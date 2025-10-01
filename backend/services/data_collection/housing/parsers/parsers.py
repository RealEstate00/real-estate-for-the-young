import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from html import unescape
from urllib.parse import urlparse, parse_qs, urljoin  # ★ sohouse 상세 진입 보정용
from pathlib import Path

# ----------------------------
# 0) sohouse 상세페이지 진입 보정
# ----------------------------

def _is_sohouse_detail_page(page) -> bool:
    """
    sohouse '진짜' 상세페이지 판별:
      - URL이 view.do 이면서 homeCode 파라미터가 존재해야 함
      - (보조) 상세 컨테이너가 보이는지 점검
    리스트 페이지의 .boardTable / #cohomeForm 는 상세가 아님!
    """
    try:
        u = page.url
    except Exception:
        u = ""

    if not ("soco.seoul.go.kr" in u and "/soHouse/" in u and "view.do" in u):
        return False

    try:
        q = parse_qs(urlparse(u).query)
        code = (q.get("homeCode") or [None])[0]
    except Exception:
        code = None

    if not code:
        return False

    # 상세 페이지에서 흔히 보이는 컨테이너(보조 체크)
    try:
        if page.locator(".viewTable").count() > 0:
            return True
        if page.locator(".bbsV_wrap").count() > 0:
            return True
        if page.locator(".detail-info").count() > 0:
            return True
        if page.locator(".info-box").count() > 0:
            return True
    except Exception:
        pass

    # homeCode가 있고 view.do이면 상세로 간주
    return True

def _ensure_sohouse_detail_page(page) -> bool:
    """리스트/게시판으로 열려도 실제 상세(view.do?homeCode=)로 보정."""
    # 0) ★ cohouse 무영향 가드: 도메인/경로로 sohouse가 아니면 바로 탈출
    try:
        cur = page.url or ""
    except Exception:
        cur = ""
    low = cur.lower()
    if ("soco.seoul.go.kr" not in low) or ("/sohouse/" not in low):
        return False

    # 이미 '진짜' 상세면 끝
    if _is_sohouse_detail_page(page):
        return True

    # 1) 페이지 내 상세 링크로 진입 시도
    try:
        link = page.locator("a[href*='/soHouse/'][href*='view.do']").first
        if link.count():
            href = (link.get_attribute("href") or "").strip()
            if href:
                if not href.startswith("http"):
                    href = urljoin("https://soco.seoul.go.kr", href)
                # ★ 중복 네비게이션 방지
                if href != cur:
                    page.goto(href, wait_until="domcontentloaded")
                return _is_sohouse_detail_page(page)
    except Exception:
        pass

    # 2) URL 쿼리/hidden/modify()에서 code 캐치 (homeCode 우선, 없으면 boardId 허용)
    code = None
    try:
        q = parse_qs(urlparse(cur).query)
        code = (q.get("homeCode") or q.get("boardId") or [None])[0]
    except Exception:
        pass

    if not code:
        try:
            hidden = page.locator("input[name='homeCode'], input[name='boardId']").first
            if hidden.count():
                code = (hidden.input_value() or "").strip() or None
        except Exception:
            pass

    if not code:
        try:
            # 리스트의 javascript:modify(20000569) 형태에서 추출
            a = page.locator("a[href^='javascript:modify(']").first
            if a.count():
                m = re.search(r"modify\((\d+)\)", a.get_attribute("href") or "")
                if m: code = m.group(1)
            if not code:
                m = re.search(r"modify\((\d+)\)", page.content())
                if m: code = m.group(1)
        except Exception:
            pass

    if code:
        target = f"https://soco.seoul.go.kr/soHouse/pgm/home/sohome/view.do?menuNo=300006&homeCode={code}"
        # ★ 현재가 이미 target이면 이동 안 함 → cohouse에도 영향 X, 중복 네비게이션 X
        if (page.url or "") != target:
            try:
                page.goto(
                    target,
                    referer="https://soco.seoul.go.kr/soHouse/pgm/home/sohome/list.do?menuNo=300006",
                    wait_until="domcontentloaded",
                )
            except Exception:
                page.goto(target, wait_until="domcontentloaded")
        return _is_sohouse_detail_page(page)

    return False

# ----------------------------
# 1) Subway parsing (robust)
# ----------------------------

_STATION_NAME_CLEAN = re.compile(r"\s+")
_NUM = r"(?:\d{1,3}(?:,\d{3})*|\d+)"
# Capture things like:
#  - "2호선 홍대입구역 도보 7분"
#  - "지하철 3호선 압구정역 버스 5분"
#  - "신정네거리역(도보10분)"
#  - "회기역 500m"
#  - "수유역 도보 2분 / 쌍문역 버스 6분"
_SUBWAY_TOKEN = re.compile(
    r"""
    (?:
        (?:(?:지하철)?\s*(?P<line>\d+)\s*호선)\s*   # optional explicit line
    )?
    (?P<name>[가-힣A-Za-z0-9·\-\s]+?)\s*역          # station name + 역
    (?:[^\S\r\n]*[\(\[]?)?
    (?:
        (?P<walk>도보)\s*(?P<walk_min>\d+)\s*분   |
        (?P<walk_sec>\d+)\s*초                    |
        (?P<bus>버스)\s*(?P<bus_min>\d+)\s*분     |
        (?P<dist_m>\d+)\s*m
    )?
    """,
    re.VERBOSE,
)

# ----------------------------
# 2) Helper functions for parsing
# ----------------------------

def _clean_title(t: str) -> str:
    """Clean title by removing bracket prefixes and category words."""
    t = re.sub(r"^\s*\[[^\]]+\]\s*", "", t or "").strip()
    # "사회적주택"을 "사회주택"으로 변경
    t = t.replace("사회적주택", "사회주택")
    if t in {"사회주택", "공동체주택", "청년", "청년안심주택"}:
        return ""
    return t

def parse_by_label(page, labels: list[str]) -> str:
    """Parse text by table label."""
    for key in labels:
        try:
            th = page.locator(f"table th:has-text('{key}')").first
            if th.count():
                td = th.locator("xpath=following-sibling::td[1]").first
                if td.count():
                    t = td.inner_text().strip()
                    if t:
                        return t
        except Exception:
            continue
    return ""

def parse_address_strict(page) -> str:
    """주소 추출 로직 - 사회주택 상세 페이지 구조 기반 간단한 추출 (게시판 뷰 보강)"""
    try:
        address_elements = page.locator("li.dashline p:has-text('주소')")
        for i in range(address_elements.count()):
            try:
                element = address_elements.nth(i)
                text = element.inner_text().strip()
                if "주소" in text:
                    addr_part = text.split("주소")[-1].strip()
                    if addr_part.startswith(":"):
                        addr_part = addr_part[1:].strip()
                    elif addr_part.startswith("："):
                        addr_part = addr_part[1:].strip()
                    if addr_part and len(addr_part) > 5:
                        return addr_part[:200]
            except Exception:
                continue
    except Exception:
        pass

    try:
        strong_elements = page.locator("strong:has-text('주소')")
        for i in range(strong_elements.count()):
            try:
                strong = strong_elements.nth(i)
                parent = strong.locator("xpath=parent::*").first
                if parent.count():
                    text = parent.inner_text().strip()
                    if "주소" in text:
                        addr_part = text.split("주소")[-1].strip()
                        if addr_part.startswith(":"):
                            addr_part = addr_part[1:].strip()
                        elif addr_part.startswith("："):
                            addr_part = addr_part[1:].strip()
                        if addr_part and len(addr_part) > 5:
                            return addr_part[:200]
            except Exception:
                continue
    except Exception:
        pass

    try:
        tables = page.locator("table")
        for i in range(tables.count()):
            table = tables.nth(i)
            ths = table.locator("th")
            for j in range(ths.count()):
                th_text = ths.nth(j).inner_text().strip()
                if any(addr_key in th_text for addr_key in ["주소", "소재지", "위치", "현장주소"]):
                    td = ths.nth(j).locator("xpath=following-sibling::td[1]").first
                    if td.count():
                        addr_text = td.inner_text().strip()
                        if addr_text and len(addr_text) > 5:
                            return addr_text[:200]
    except Exception:
        pass

    t = parse_by_label(page, ["주소", "소재지", "위치", "현장주소"])
    if t and len(t) > 5:
        return t[:200]

    # ★ (추가) dl/dt+dd 구조 지원
    try:
        dts = page.locator("dl dt")
        for i in range(dts.count()):
            dt = dts.nth(i)
            label = dt.inner_text().strip()
            if any(k in label for k in ["주소", "소재지", "위치", "현장주소", "도로명주소"]):
                dd = dt.locator("xpath=following-sibling::dd[1]").first
                if dd.count():
                    val = dd.inner_text().strip()
                    if val and len(val) > 5:
                        return val[:200]
    except Exception:
        pass

    # ★ (추가) 게시판/상세 컨테이너 내부의 '주소: ...' 한 줄 패턴 스캔
    try:
        containers = [
            "tbody#cohomeForm", ".detail-info", ".info-box",
            ".bbsV_wrap", ".bbsV_cont", ".viewTable", ".boardTable",
            "div.detail-box", ".view-content", "article",
            # 청년주택 특화 컨테이너 추가
            ".youth-detail", ".youth-info", ".youth-content",
            "div[class*='youth']", "div[class*='detail']", "div[class*='info']",
        ]
        for sel in containers:
            loc = page.locator(sel)
            if loc.count():
                txt = loc.inner_text()
                m = re.search(r"(?:주소|소재지|위치|현장주소|도로명주소)\s*[：:]\s*([^\n]+)", txt)
                if m:
                    addr_part = m.group(1).strip()
                    if len(addr_part) > 5:
                        return addr_part[:200]
    except Exception:
        pass

    try:
        body_text = page.locator("body").inner_text()
        seoul_patterns = [
            r"서울[시특]?\s*[가-힣]+구\s*[가-힣]+동\s*[가-힣]+로\s*\d+",
            r"서울[시특]?\s*[가-힣]+구\s*[가-힣]+동\s*[가-힣]+길\s*\d+",
            r"서울[시특]?\s*[가-힣]+구\s*[가-힣]+동\s*\d+-\d+",
            r"[가-힣]+구\s*[가-힣]+동\s*[가-힣]+로\s*\d+",
            r"[가-힣]+구\s*[가-힣]+동\s*[가-힣]+길\s*\d+",
            r"[가-힣]+구\s*[가-힣]+동\s*\d+-\d+",
        ]
        for pattern in seoul_patterns:
            match = re.search(pattern, body_text)
            if match:
                addr_text = match.group().strip()
                if len(addr_text) > 5:
                    return addr_text[:200]
    except Exception:
        pass

    return ""

def parse_building_type(page) -> str:
    """주거형태 정보 추출 (도시형생활주택, 아파트 등) - p.subcont_txt3에서 추출"""
    try:
        subcont_elements = page.locator("p.subcont_txt3")
        for i in range(subcont_elements.count()):
            text = subcont_elements.nth(i).inner_text().strip()
            if text and len(text) > 1 and text not in ["", " ", "\n"]:
                housing_forms = ["연립주택", "다세대주택", "도시형생활주택", "아파트", "단독주택", "빌라", "오피스텔"]
                for housing_form in housing_forms:
                    if housing_form in text:
                        return housing_form
                return text[:50]
    except Exception:
        pass

    try:
        occupancy_elements = page.locator("li.dashline p:has-text('주거형태')")
        for i in range(occupancy_elements.count()):
            try:
                element = occupancy_elements.nth(i)
                text = element.inner_text().strip()
                if "주거형태" in text:
                    occ_part = text.split("주거형태")[-1].strip()
                    if occ_part.startswith(":"):
                        occ_part = occ_part[1:].strip()
                    elif occ_part.startswith("："):
                        occ_part = occ_part[1:].strip()
                    if occ_part and len(occ_part) > 1:
                        return occ_part[:100]
            except Exception:
                continue
    except Exception:
        pass

    try:
        strong_elements = page.locator("strong:has-text('주거형태')")
        for i in range(strong_elements.count()):
            try:
                strong = strong_elements.nth(i)
                parent = strong.locator("xpath=parent::*").first
                if parent.count():
                    text = parent.inner_text().strip()
                    if "주거형태" in text:
                        occ_part = text.split("주거형태")[-1].strip()
                        if occ_part.startswith(":"):
                            occ_part = occ_part[1:].strip()
                        elif occ_part.startswith("："):
                            occ_part = occ_part[1:].strip()
                        if occ_part and len(occ_part) > 1:
                            return occ_part[:100]
            except Exception:
                continue
    except Exception:
        pass

    occupancy_labels = ["입주타입", "주택유형", "세대유형", "세대구성", "세대형태", "집구조", "주택구조", "세대형"]
    for label in occupancy_labels:
        try:
            th = page.locator(f"table th:has-text('{label}')").first
            if th.count():
                td = th.locator("xpath=following-sibling::td[1]").first
                if td.count():
                    text = td.inner_text().strip()
                    if text and text != "면적" and len(text) > 1:
                        return text[:100]
        except Exception:
            continue

    try:
        body_text = page.locator("body").inner_text()
        specific_patterns = [r"1인1실", r"2인1실", r"3인1실", r"4인1실", r"1인실", r"2인실", r"3인실", r"4인실"]
        for pattern in specific_patterns:
            match = re.search(pattern, body_text)
            if match:
                return match.group().strip()

        detailed_patterns = [
            r"원룸\s*\(오픈형\)", r"원룸\s*\(분리형\)", r"원룸\s*\(복층형\)", r"원룸\s*\(셰어형\)",
            r"원룸\s*\(오픈\)", r"원룸\s*\(분리\)", r"원룸\s*\(복층\)", r"원룸\s*\(셰어\)",
        ]
        for pattern in detailed_patterns:
            match = re.search(pattern, body_text)
            if match:
                return match.group().strip()

        general_patterns = [
            r"원룸\s*형", r"투룸\s*형", r"쓰리룸\s*형", r"포룸\s*형",
            r"원룸", r"투룸", r"쓰리룸", r"포룸",
            r"1룸", r"2룸", r"3룸", r"4룸",
        ]
        for pattern in general_patterns:
            match = re.search(pattern, body_text)
            if match:
                return match.group().strip()
    except Exception:
        pass

    return ""

def parse_last_modified_date(page) -> str:
    """최종수정일 추출"""
    try:
        # HTML에서 최종수정일 패턴 찾기
        patterns = [
            r'최종수정일\s*:\s*(\d{4}-\d{2}-\d{2})',
            r'최종수정일\s*:\s*(\d{4}\.\d{2}\.\d{2})',
            r'최종수정일\s*:\s*(\d{4}/\d{2}/\d{2})',
        ]
        
        page_text = page.content()
        for pattern in patterns:
            match = re.search(pattern, page_text)
            if match:
                date_str = match.group(1)
                # 날짜 형식 통일 (YYYY-MM-DD)
                date_str = date_str.replace('.', '-').replace('/', '-')
                return date_str
    except Exception:
        pass
    return ""

def extract_facility_info(page) -> dict:
    """편의시설 정보 추출"""
    facilities = {}
    
    try:
        # 지하철 정보
        subway_elements = page.locator("li.subway p, .subway p")
        for i in range(subway_elements.count()):
            subway_text = subway_elements.nth(i).inner_text().strip()
            if subway_text and subway_text != "지하철 정보":
                facilities["subway"] = subway_text
                break
        
        # 버스 정보
        bus_elements = page.locator("li.bus p, .bus p")
        for i in range(bus_elements.count()):
            bus_text = bus_elements.nth(i).inner_text().strip()
            if bus_text and bus_text != "버스 정보":
                facilities["bus"] = bus_text
                break
        
        # 주변 시설들
        facility_types = ["마트", "병원", "학교", "시설", "카페"]
        for facility_type in facility_types:
            try:
                elements = page.locator(f"li:has-text('주변 {facility_type} 정보')")
                for i in range(elements.count()):
                    element = elements.nth(i)
                    text = element.inner_text().strip()
                    if text and f"주변 {facility_type} 정보" in text:
                        # "주변 마트 정보" 부분을 제거하고 실제 정보만 추출
                        info = text.replace(f"주변 {facility_type} 정보", "").strip()
                        if info:
                            facilities[f"nearby_{facility_type}"] = info
                        break
            except Exception:
                continue
                
    except Exception:
        pass
    
    return facilities

def extract_related_housing_info(page) -> dict:
    """주변 지역 주택 및 같은 사업자 주택 정보 추출"""
    related_info = {}
    
    try:
        # 주변 지역 사회주택 링크 추출
        area_elements = page.locator("a[href*='cohomeOfTheAreaList'], a[href*='sohomeOfTheAreaList']")
        if area_elements.count() > 0:
            area_links = []
            for i in range(area_elements.count()):
                element = area_elements.nth(i)
                href = element.get_attribute("href")
                text = element.inner_text().strip()
                if href and text:
                    area_links.append({
                        "title": text,
                        "url": href,
                        "type": "주변 지역 사회주택",
                        "index": i
                    })
            related_info["nearby_housing"] = {
                "description": "주변 지역 사회주택",
                "count": area_elements.count(),
                "links": area_links
            }
        
        # 같은 사업자의 사회주택 링크 추출
        biz_elements = page.locator("a[href*='cohomeOfTheBizList'], a[href*='sohomeOfTheBizList']")
        if biz_elements.count() > 0:
            biz_links = []
            for i in range(biz_elements.count()):
                element = biz_elements.nth(i)
                href = element.get_attribute("href")
                text = element.inner_text().strip()
                if href and text:
                    biz_links.append({
                        "title": text,
                        "url": href,
                        "type": "같은 사업자의 사회주택",
                        "index": i
                    })
            related_info["same_business_housing"] = {
                "description": "같은 사업자의 사회주택",
                "count": biz_elements.count(),
                "links": biz_links
            }
        
        # 실제 주택 목록이 있다면 추출 (JavaScript로 로드되는 경우가 많음)
        housing_list = page.locator("#cohomeForm li, .imgTable_sty2 li, .housing-list li")
        housing_items = []
        for i in range(min(housing_list.count(), 10)):  # 최대 10개만
            try:
                item = housing_list.nth(i)
                text = item.inner_text().strip()
                if text and len(text) > 5:
                    # 링크가 있다면 URL도 추출
                    link_element = item.locator("a").first
                    href = ""
                    if link_element.count() > 0:
                        href = link_element.get_attribute("href") or ""
                    
                    housing_items.append({
                        "title": text,
                        "url": href if href else None,
                        "index": i
                    })
            except Exception:
                continue
        
        if housing_items:
            related_info["housing_list"] = {
                "count": len(housing_items),
                "items": housing_items
            }
            
    except Exception as e:
        print(f"Error extracting related housing info: {e}")
    
    return related_info

def parse_eligibility_from_text(text: str) -> str:
    """텍스트에서 입주자격 정보 추출"""
    import re
    
    if not text:
        return ""
    
    # 1. 상세 조건 패턴들 (여러 줄) - 최고 우선순위
    detailed_patterns = [
        r'입주\s*조건\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
        r'입주\s*자격\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
        r'신청\s*자격\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
        r'☆\s*입주자격\s*☆\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
        r'입주\s*조건\s*\n([^▷]+?)(?=\n[▷]|\n상세소개|\n평면도|\n입주현황)',
        r'신청\s*자격\s*\n([^▷]+?)(?=\n[▷]|\n상세소개|\n평면도|\n입주현황)',
        r'입주\s*조건\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금)',
        r'신청\s*자격\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금)',
        r'입주\s*조건\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
        r'신청\s*자격\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
        r'☆\s*입주자격\s*☆\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
        r'입주\s*조건\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
        r'신청\s*자격\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
        r'☆\s*입주자격\s*☆\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
    ]
    
    for pattern in detailed_patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            conditions_text = match.group(1).strip()
            # 불필요한 공백 정리
            conditions_text = re.sub(r'\s+', ' ', conditions_text).strip()
            if conditions_text and len(conditions_text) > 10:
                print(f"[DEBUG] 텍스트에서 상세 입주조건 발견: {conditions_text[:100]}...")
                return conditions_text
    
    # 2. 상세한 패턴들 (괄호 포함) - 두 번째 우선순위
    # 먼저 괄호가 포함된 상세한 패턴을 찾음 (한 줄 내에서)
    detailed_patterns_with_parens = [
        r'입주\s*대상\s*:\s*([^\(]+\([^)]+\))',
        r'공급\s*대상\s*:\s*([^\(]+\([^)]+\))',
        r'입주\s*조건\s*:\s*([^\(]+\([^)]+\))',
        r'입주\s*자격\s*:\s*([^\(]+\([^)]+\))',
        r'신청\s*자격\s*:\s*([^\(]+\([^)]+\))',
    ]
    
    for pattern in detailed_patterns_with_parens:
        # 한 줄씩 검사하여 정확한 매칭 찾기
        lines = text.split('\n')
        for line in lines:
            match = re.search(pattern, line)
            if match:
                elig_text = match.group(1).strip()
                # 괄호가 포함되고 줄바꿈이 없는 경우만 유효
                if elig_text and '(' in elig_text and ')' in elig_text and '\n' not in elig_text and len(elig_text) > 5:
                    print(f"[DEBUG] 상세 입주대상 발견: {elig_text}")
                    return elig_text
    
    # 3. 간단한 패턴들 (한 줄) - 세 번째 우선순위
    simple_patterns = [
        r'입주\s*대상\s*:\s*([^\n]+)',
        r'공급\s*대상\s*:\s*([^\n]+)',
        r'입주\s*조건\s*:\s*([^\n]+)',
        r'입주\s*자격\s*:\s*([^\n]+)',
        r'신청\s*자격\s*:\s*([^\n]+)',
    ]
    
    for pattern in simple_patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            elig_text = match.group(1).strip()
            if elig_text and len(elig_text) > 2:
                print(f"[DEBUG] 간단 입주대상 발견: {elig_text}")
                return elig_text
    
    return ""

def parse_eligibility(page) -> str:
    """입주자격 정보 추출 - 상세 조건과 간단 대상 모두 처리"""
    t = parse_by_label(page, ["입주대상", "공급대상", "대상", "신청자격", "입주자격"])
    simple_target = t if t else ""

    table_eligibility = ""
    try:
        tables = page.locator("table")
        for i in range(tables.count()):
            table = tables.nth(i)
            ths = table.locator("th")
            for j in range(ths.count()):
                th_text = ths.nth(j).inner_text().strip()
                if any(elig_key in th_text for elig_key in ["입주대상", "공급대상", "대상", "자격", "신청자격", "입주자격"]):
                    td = ths.nth(j).locator("xpath=following-sibling::td[1]").first
                    if td.count():
                        elig_text = td.inner_text().strip()
                        if elig_text:
                            table_eligibility = elig_text
                            break
    except Exception:
        pass

    detailed_conditions = ""
    try:
        page_text = page.content()
        detailed_patterns = [
            r'입주\s*조건\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
            r'입주\s*자격\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
            r'신청\s*자격\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
            r'☆\s*입주자격\s*☆\s*\n((?:[0-9]+\.\s*[^\n]+\n?)+)',
            r'입주\s*조건\s*\n([^▷]+?)(?=\n[▷]|\n상세소개|\n평면도|\n입주현황)',
            r'신청\s*자격\s*\n([^▷]+?)(?=\n[▷]|\n상세소개|\n평면도|\n입주현황)',
            r'입주\s*조건\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금)',
            r'신청\s*자격\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금)',
            r'입주\s*조건\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
            r'신청\s*자격\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
            r'☆\s*입주자격\s*☆\s*\n([^상세소개]+?)(?=\n상세소개|\n평면도|\n입주현황|\n보증금|\n현재)',
            r'입주\s*조건\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
            r'신청\s*자격\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
            r'☆\s*입주자격\s*☆\s*\n([^상세소개]+?)(?=\n보증금|\n현재|\n사회주택)',
        ]
        for pattern in detailed_patterns:
            match = re.search(pattern, page_text, re.MULTILINE | re.DOTALL)
            if match:
                conditions_text = match.group(1).strip()
                conditions_text = re.sub(r'<[^>]+>', '', conditions_text)
                conditions_text = re.sub(r'\s+', ' ', conditions_text).strip()
                if conditions_text and len(conditions_text) > 10:
                    detailed_conditions = conditions_text
                    break
    except Exception:
        pass

    simple_patterns = [
        r'입주\s*조건\s*:\s*([^\n]+)',
        r'입주\s*자격\s*:\s*([^\n]+)',
        r'신청\s*자격\s*:\s*([^\n]+)',
        r'입주\s*대상\s*:\s*([^\n]+)',
        r'공급\s*대상\s*:\s*([^\n]+)',
    ]

    simple_eligibility = ""
    try:
        page_text = page.content()
        for pattern in simple_patterns:
            match = re.search(pattern, page_text, re.MULTILINE | re.DOTALL)
            if match:
                elig_text = match.group(1).strip()
                elig_text = re.sub(r'<[^>]+>', '', elig_text)
                elig_text = re.sub(r'\s+', ' ', elig_text).strip()
                if elig_text and len(elig_text) > 5:
                    simple_eligibility = elig_text
                    break
    except Exception:
        pass

    if detailed_conditions:
        return detailed_conditions
    elif table_eligibility:
        return table_eligibility
    elif simple_eligibility:
        return simple_eligibility
    elif simple_target:
        return simple_target
    return ""

def _normalize_station_name(raw: str) -> str:
    """Normalize station names to a consistent '...역' form."""
    name = raw.strip()
    name = re.sub(r"[\(\)\[\]<>]", " ", name)
    name = _STATION_NAME_CLEAN.sub(" ", name)
    name = name.replace("  ", " ").strip()
    if not name.endswith("역"):
        name = name + "역"
    return name

def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            out.append(it)
            seen.add(it)
    return out

def _extract_subway_from_text(text: str) -> List[Dict[str, Optional[str]]]:
    """Return a list of stations with optional line and access info."""
    results: List[Dict[str, Optional[str]]] = []
    for m in _SUBWAY_TOKEN.finditer(text):
        raw_name = m.group("name") or ""
        name = _normalize_station_name(raw_name)
        line = m.group("line")
        walk_min = m.group("walk_min")
        walk_sec = m.group("walk_sec")
        bus_min = m.group("bus_min")
        dist_m = m.group("dist_m")

        results.append({
            "line": f"{line}호선" if line else None,
            "station": name,
            "access": (
                f"도보 {walk_min}분" if walk_min else
                f"도보 {walk_sec}초" if walk_sec else
                f"버스 {bus_min}분" if bus_min else
                f"{dist_m}m" if dist_m else None
            )
        })
    return results

def _stations_to_string(stations: List[Dict[str, Optional[str]]]) -> str:
    """Collapse station dicts into a readable, deduped CSV string."""
    labels = []
    for s in stations:
        label = s["station"]
        if s.get("line"):
            label = f"{s['line']} {label}"
        if s.get("access"):
            label = f"{label} {s['access']}"
        labels.append(label.strip())
    return ", ".join(_dedupe_preserve_order(labels))

def parse_subway_station(page) -> str:
    """지하철역 정보 추출"""
    try:
        # sohouse 전용: ul.flexbox.trans 구조에서 추출
        subway_selector = "ul.flexbox.trans li.subway p"
        subway_elements = page.locator(subway_selector)
        if subway_elements.count() > 0:
            subway_text = subway_elements.first.inner_text().strip()
            if subway_text and "역" in subway_text:
                station_patterns = [
                    r"(\w+역)",
                    r"(\w+역\s*도보\s*\d+분)",
                    r"(\w+역\s*도보\s*\d+초)",
                    r"(\w+역\s*버스\s*\d+분)",
                ]
                for pattern in station_patterns:
                    match = re.search(pattern, subway_text)
                    if match:
                        return match.group(1).strip()
        
        # 기존 테이블 구조도 시도
        table_rows = page.locator("table tr")
        for i in range(table_rows.count()):
            row = table_rows.nth(i)
            cells = row.locator("td")
            if cells.count() >= 6:
                try:
                    subway_cell = cells.nth(5)
                    subway_text = subway_cell.inner_text().strip()
                    if subway_text and subway_text != "" and "역" in subway_text:
                        station_patterns = [
                            r"(\w+역)",
                            r"(\w+역\s*도보\s*\d+분)",
                            r"(\w+역\s*도보\s*\d+초)",
                            r"(\w+역\s*버스\s*\d+분)",
                        ]
                        for pattern in station_patterns:
                            match = re.search(pattern, subway_text)
                            if match:
                                return match.group(1).strip()
                except Exception:
                    continue
    except Exception:
        pass

    try:
        transport = parse_by_label(page, ["교통", "교통편", "접근성", "대중교통", "지하철"])
        if transport:
            subway_patterns = [
                r"(\d+호선\s*[가-힣]+역)",
                r"지하철\s*(\d+호선\s*[가-힣]+역)",
                r"([가-힣]+역)",
                r"(\d+호선\s*[가-힣]+)",
            ]
            for pattern in subway_patterns:
                matches = re.findall(pattern, transport)
                if matches:
                    return ", ".join(matches)

        address = parse_address_strict(page)
        if address:
            subway_in_address = re.search(r"([가-힣]+역)", address)
            if subway_in_address:
                return subway_in_address.group(1)
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------
# 2) JSON field filtering for sohouse (normalization-first)
# ---------------------------------------------------------

_PHONE_CLEAN = re.compile(r"[^\d]")
_URL_PREFIX = re.compile(r"^(?!https?://)")
_TAG = re.compile(r"<[^>]+>")
_WS  = re.compile(r"\s+")

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = _PHONE_CLEAN.sub("", phone)
    if len(digits) < 7:
        return None
    if digits.startswith("02") and len(digits) in (9, 10):
        if len(digits) == 9:
            return f"02-{digits[2:5]}-{digits[5:]}"
        return f"02-{digits[2:6]}-{digits[6:]}"
    if len(digits) in (10, 11):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return digits

def _normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if " " in u and not u.startswith("http"):
        return None
    if _URL_PREFIX.match(u):
        u = "https://" + u
    return u

def _is_meaningful(val: Optional[str]) -> bool:
    if val is None:
        return False
    s = str(val).strip()
    if len(s) <= 2:
        return False
    if s.isdigit():
        return False
    return True

def _strip_tags(s: str) -> str:
    s = unescape(s or "")
    s = _TAG.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s

def _clean_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        return _strip_tags(v)
    return v

def _money_tuple(text: str) -> tuple[str, str] | None:
    nums = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text or "")
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    lo, hi = nums[0], nums[1]
    if int(lo.replace(",", "")) > int(hi.replace(",", "")):
        lo, hi = hi, lo
    return lo, hi

def filter_json_fields_for_sohouse(kv_pairs: dict, platform_specific_fields: dict) -> dict:
    """Build stable, clean JSON for sohouse (schema-aligned with cohouse sample)."""
    import re

    def _strip_tags_local(s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _nz(v):
        return isinstance(v, str) and v.strip() and v.strip() != "-"

    def pick(*keys):
        for k in keys:
            v = platform_specific_fields.get(k)
            if _nz(v):
                return _strip_tags_local(v)
        for k in keys:
            v = kv_pairs.get(k)
            if _nz(v):
                return _strip_tags_local(v)
        return ""

    cleaned_text = platform_specific_fields.pop("text_content", "") or ""
    result: dict = {}

    # 1) facilities
    facilities = {}
    subway = pick("subway_station")
    if _nz(subway):
        facilities["subway_station"] = subway
    
    # facility_info에서 편의시설 정보 추가 (subway 중복 제거)
    if "facility_info" in platform_specific_fields:
        facility_info = platform_specific_fields["facility_info"]
        if isinstance(facility_info, dict):
            # subway는 이미 subway_station으로 추가되었으므로 제외
            filtered_facility_info = {k: v for k, v in facility_info.items() if k != "subway"}
            facilities.update(filtered_facility_info)
    
    if facilities:
        result["facilities"] = facilities

    # 2) company_info
    company_info = {}
    cn = pick("company_name")
    if _nz(cn):
        company_info["company_name"] = cn
    rep = pick("representative")
    if _nz(rep):
        company_info["representative"] = rep
    hp = pick("contact_phone", "phone", "문의전화")
    hp = _normalize_phone(hp) if hp else None
    if hp:
        company_info["contact_phone"] = hp
    home = pick("homepage", "홈페이지")
    home = _normalize_url(home) if home else None
    if home:
        company_info["homepage"] = home
    if company_info:
        result["company_info"] = company_info

    # 3) housing_specific
    housing_specific = {}
    deposit = pick("deposit", "보증금")
    if _nz(deposit):
        housing_specific["deposit_range"] = deposit
    monthly = pick("monthly_rent", "월세", "월임대료")
    if _nz(monthly):
        housing_specific["monthly_rent_range"] = monthly
    mgmt = pick("management_fee", "관리비", "월관리비")
    if _nz(mgmt):
        housing_specific["management_fee"] = mgmt
    elig = pick("target_occupancy", "입주대상", "입주자격", "공급대상")
    if _nz(elig):
        housing_specific["target_occupancy_detail"] = elig
    if housing_specific:
        result["housing_specific"] = housing_specific

    # 4) building_details
    building_details = {}
    district = pick("district_type", "지역/지구")
    if _nz(district):
        building_details["district_type"] = district
    bscale = pick("building_scale", "규모", "규 모")
    if _nz(bscale):
        building_details["building_scale"] = bscale
    bstruct = pick("building_structure", "구조", "구 조")
    if _nz(bstruct):
        building_details["building_structure"] = bstruct
    site_area = pick("site_area", "대지면적")
    if _nz(site_area):
        building_details["site_area"] = site_area
    tfa = pick("total_floor_area", "연면적", "연 면 적")
    if _nz(tfa):
        building_details["total_floor_area"] = tfa
    appr = pick("approval_date", "사용승인")
    if _nz(appr):
        building_details["approval_date"] = appr
    park = pick("parking", "주차")
    if _nz(park):
        building_details["parking"] = park
    tunits = pick("total_units", "총세대", "총 세대")
    if _nz(tunits):
        building_details["total_units"] = tunits
    tpeople = pick("total_people", "총주거인원", "총 주거인원")
    if _nz(tpeople):
        building_details["total_people"] = tpeople
    trooms = pick("total_rooms", "총실", "총 실")
    if _nz(trooms):
        building_details["total_rooms"] = trooms
    # address를 building_details에 추가
    addr = pick("address", "주소")
    if _nz(addr):
        building_details["address"] = addr
    
    if building_details:
        result["building_details"] = building_details

    # 5) sohouse_text_extracted_info
    soi = {}

    hform = pick("building_type", "주거형태", "주택구조")
    if _nz(hform):
        soi["building_type"] = hform
    htype = pick("unit_type", "세대형태", "세대유형", "집구조", "세대형")
    if _nz(htype):
        soi["unit_type"] = htype
    if _nz(elig):
        soi["target_occupancy"] = elig

    extracted_patterns = {}
    if cleaned_text:
        text = re.sub(r"<[^>]+>", " ", cleaned_text)
        text = re.sub(r"\s+", " ", text).strip()

        areas = re.findall(r"(\d+(?:\.\d+)?)\s*(?:㎡|m²|m2)", text)
        if areas:
            seen = set(); a_out = []
            for a in areas:
                if a not in seen:
                    seen.add(a); a_out.append(a)
            extracted_patterns["areas"] = a_out

        prices = []
        for m in re.finditer(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{2,})\s*원", text):
            prices.append(m.group(1))
        if prices:
            prices = [p for p in prices if not re.fullmatch(r"0+", p)]
            seen = set(); p_out = []
            for p in prices:
                if p not in seen:
                    seen.add(p); p_out.append(p)
            if p_out:
                extracted_patterns["prices"] = p_out

        dates = []
        for m in re.finditer(r"(\d{4}[.\-\/]\d{1,2}[.\-\/]\d{1,2})", text):
            dates.append(m.group(1))
        if dates:
            seen = set(); d_out = []
            for d in dates:
                if d not in seen:
                    seen.add(d); d_out.append(d)
            extracted_patterns["dates"] = d_out

    if extracted_patterns:
        soi["extracted_patterns"] = extracted_patterns

    if soi:
        result["sohouse_text_extracted_info"] = soi

    # 6) eligibility_raw
    elig_raw = pick("eligibility", "eligibility_raw")
    if _nz(elig_raw):
        result["eligibility_raw"] = elig_raw


    result["_meta"] = {
        "source": "sohouse",
        "schema": "v1",
        "fetched_at": datetime.now().isoformat(),
    }
    return result


# -----------------------------------------
# 3) Text mining: extract structured info
# -----------------------------------------

_AMENITY_FLAGS = {
    "elevator": re.compile(r"엘리베이터"),
    "cctv": re.compile(r"CCTV", re.IGNORECASE),
    "parcel_box": re.compile(r"(무인|택배)\s*함"),
    "rooftop": re.compile(r"(옥상|루프탑)"),
    "parking": re.compile(r"(주차|파킹)"),
    "coworking": re.compile(r"(코워킹|공유\s*오피스|작업실|스터디\s*룸)"),
    "lounge": re.compile(r"(라운지|공용\s*거실|커뮤니티\s*공간)"),
    "common_kitchen": re.compile(r"(공용\s*주방|셰어\s*키친|공동\s*취사)"),
    "garden": re.compile(r"(마당|정원)"),
    "balcony": re.compile(r"(발코니|테라스)"),
    "security": re.compile(r"(경비|보안)"),
    "laundry": re.compile(r"(세탁실|세탁기|건조기)"),
}

_POLICY_FLAGS = {
    "pet_allowed": re.compile(r"(반려동물|애완동물).*(가능|허용)"),
    "pet_not_allowed": re.compile(r"(반려동물|애완동물).*(불가|금지)"),
    "smoking_not_allowed": re.compile(r"(금연|흡연\s*불가)"),
    "move_in": re.compile(r"(입주\s*(가능|예정)\s*일?\s*[:：]?\s*)(?P<date>[\d\.\-/년월일\s]+)"),
}

_BUS_LINES = re.compile(r"(버스)\s*[:：]?\s*(?P<lines>(?:\d{1,3}[A-Za-z]?[\s,／/·\-]?)+)")
_DISTANCE_MIN = re.compile(r"(도보)\s*(?P<min>\d+)\s*분")
_DISTANCE_SEC = re.compile(r"(도보)\s*(?P<sec>\d+)\s*초")
_DISTANCE_M = re.compile(r"(?P<m>\d+)\s*m\b")

_MONEY = re.compile(rf"(?:보증금|월세|월임대료|임대료)\s*[:：]?\s*({_NUM})\s*(?:원|만원|억)?")
_AREA = re.compile(rf"({_NUM}(?:\.\d+)?)\s*(?:㎡|m2|m²)")

def _safe_join_csv(parts: List[str]) -> Optional[str]:
    parts = [p.strip() for p in parts if p and str(p).strip()]
    return ", ".join(_dedupe_preserve_order(parts)) if parts else None

def _extract_text_info(text_content: str) -> dict:
    """Mine semi-structured details from free text into stable keys."""
    text = (text_content or "").strip()
    if not text:
        return {}

    info: Dict[str, object] = {}
    amenities = {}
    for key, rx in _AMENITY_FLAGS.items():
        if rx.search(text):
            amenities[key] = True
    if amenities:
        info["amenities"] = amenities

    policies = {}
    if _POLICY_FLAGS["pet_allowed"].search(text):
        policies["pet"] = "allowed"
    elif _POLICY_FLAGS["pet_not_allowed"].search(text):
        policies["pet"] = "not_allowed"
    if _POLICY_FLAGS["smoking_not_allowed"].search(text):
        policies["smoking"] = "not_allowed"
    m_move = _POLICY_FLAGS["move_in"].search(text)
    if m_move and m_move.group("date"):
        policies["move_in_detail"] = m_move.group("date").strip()
    if policies:
        info["policies"] = policies

    buses = []
    for m in _BUS_LINES.finditer(text):
        raw = m.group("lines") or ""
        tokens = re.split(r"[^0-9A-Za-z]+", raw)
        buses.extend([t for t in tokens if t.strip()])
    buses = _dedupe_preserve_order(buses)
    if buses:
        info["bus_lines"] = buses

    dist_hints = []
    for rx in (_DISTANCE_MIN, _DISTANCE_SEC, _DISTANCE_M):
        for m in rx.finditer(text):
            dist_hints.append(m.group(0))
    if dist_hints:
        info["distance_hints"] = _dedupe_preserve_order(dist_hints)

    money_vals = [m.group(1) for m in _MONEY.finditer(text)]
    if money_vals:
        info["money_mentions"] = _dedupe_preserve_order(money_vals)

    area_vals = [m.group(1) for m in _AREA.finditer(text)]
    if area_vals:
        info["area_mentions_sqm"] = _dedupe_preserve_order(area_vals)

    subways = _extract_subway_from_text(text)
    if subways:
        info["subway"] = subways
    return info


# ----------------------------
# 4) Platform-specific field extractors
# ----------------------------

def extract_sohouse_specific_fields(page, detail_text: str = "") -> dict:
    """사회주택 특화 필드 추출 - cohouse와 동일한 수준으로 풍부하게"""
    # ★ sohouse 상세 진입 보정
    try:
        _ensure_sohouse_detail_page(page)
    except Exception:
        pass

    fields = {}
    try:
        page_text = detail_text if detail_text else page.content()

        # 기본 정보
        try:
            address = parse_address_strict(page)
            if address:
                fields["address"] = address

            building_type = parse_building_type(page)
            if building_type:
                fields["building_type"] = building_type
                fields["building_type"] = building_type

            eligibility = parse_eligibility(page)
            if eligibility:
                fields["target_occupancy"] = eligibility
                fields["eligibility"] = eligibility

            subway_station = parse_subway_station(page)
            if subway_station:
                fields["subway_station"] = subway_station
        except Exception as e:
            print(f"Error in basic field extraction: {e}")

        # 텍스트 기반 보강
        if page_text:
            unit_type_patterns = [
                r'주택유형\s*:\s*([^\n]+)',
                r'집구조\s*:\s*([^\n]+)',
                r'(\w+룸)',
                r'(\w+형)',
            ]
            for pattern in unit_type_patterns:
                match = re.search(pattern, page_text)
                if match:
                    unit_text = match.group(1).strip()
                    if unit_text and unit_text not in ['', '주택유형', '집구조']:
                        fields["unit_type"] = unit_text
                        break

            company_patterns = {
                "company_name": r'상호\s*:\s*([^\n]+)',
                "representative": r'대표자\s*:\s*([^\n]+)',
                "contact_phone": r'문의전화\s*:\s*([^\n]+)',
                "homepage": r'홈페이지\s*:\s*([^\n]+)',
            }
            for key, pattern in company_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            price_patterns = {
                "deposit": r'보증금\s*:\s*([^\n]+)',
                "monthly_rent": r'월세\s*:\s*([^\n]+)',
                "management_fee": r'관리비\s*:\s*([^\n]+)',
            }
            for key, pattern in price_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            housing_detail_patterns = {
                "district_type": r'지역/지구:\s*([^\n]+)',
                "building_scale": r'규\s*모:\s*([^\n]+)',
                "building_structure": r'구\s*조:\s*([^\n]+)',
                "site_area": r'대지면적\s*:\s*([^\n]+)',
                "total_floor_area": r'연\s*면\s*적\s*:\s*([^\n]+)',
                "approval_date": r'사용승인\s*:\s*([^\n]+)',
                "parking": r'주\s*차\s*:\s*([^\n]+)',
                "total_units": r'총\s*세대\s*:\s*([^\n]+)',
                "total_people": r'총\s*주거인원\s*:\s*([^\n]+)',
                "total_rooms": r'총\s*실\s*:\s*([^\n]+)',
            }
            for key, pattern in housing_detail_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            facility_patterns = {
                "subway_station": r'지하철역\s*:\s*([^\n]+)',
                "bus_info": r'버스\s*정보\s*:\s*([^\n]+)',
                "nearby_mart": r'주변\s*마트\s*정보\s*:\s*([^\n]+)',
                "nearby_hospital": r'주변\s*병원\s*정보\s*:\s*([^\n]+)',
                "nearby_school": r'주변\s*학교\s*정보\s*:\s*([^\n]+)',
                "nearby_facilities": r'주변\s*시설\s*정보\s*:\s*([^\n]+)',
                "nearby_cafe": r'주변\s*카페\s*정보\s*:\s*([^\n]+)',
            }
            for key, pattern in facility_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            occupancy_patterns = {
                "target_occupancy": r'입주대상\s*:\s*([^\n]+)',
                "building_type": r'주거형태\s*:\s*([^\n]+)',
                "unit_type": r'주택유형\s*:\s*([^\n]+)',
                "move_in_date": r'입주가능일\s*:\s*([^\n]+)',
                "availability": r'입주가능\s*:\s*([^\n]+)',
            }
            for key, pattern in occupancy_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            other_patterns = {
                "house_name": r'주택명\s*:\s*([^\n]+)',
                "address": r'주소\s*:\s*([^\n]+)',
                "theme": r'테마\s*:\s*([^\n]+)',
                "features": r'특징\s*:\s*([^\n]+)',
                "description": r'설명\s*:\s*([^\n]+)',
            }
            for key, pattern in other_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

        # 편의시설 정보 추가
        try:
            facility_info = extract_facility_info(page)
            if facility_info:
                fields["facility_info"] = facility_info
        except Exception as e:
            print(f"Error extracting facility info: {e}")

        # 관련 주택 정보 추가
        try:
            related_housing_info = extract_related_housing_info(page)
            if related_housing_info:
                fields["related_housing_info"] = related_housing_info
        except Exception as e:
            print(f"Error extracting related housing info: {e}")

    except Exception as e:
        print(f"Error in extract_sohouse_specific_fields: {e}")

    return fields

def extract_cohouse_specific_fields(page, detail_text: str = "") -> dict:
    """공동체주택 특화 필드 추출 - cohouse 전용 로직"""
    fields = {}
    try:
        page_text = detail_text if detail_text else page.content()

        # 기본 정보
        try:
            address = parse_address_strict(page)
            if address:
                fields["address"] = address

            building_type = parse_building_type(page)
            if building_type:
                fields["building_type"] = building_type
                fields["building_type"] = building_type

            eligibility = parse_eligibility(page)
            if eligibility:
                fields["target_occupancy"] = eligibility
                fields["eligibility"] = eligibility

            subway_station = parse_subway_station(page)
            if subway_station:
                fields["subway_station"] = subway_station
        except Exception as e:
            print(f"Error in cohouse basic field extraction: {e}")

        # 텍스트 기반 보강
        if page_text:
            unit_type_patterns = [
                r'주택유형\s*:\s*([^\n]+)',
                r'집구조\s*:\s*([^\n]+)',
                r'(\w+룸)',
                r'(\w+형)',
            ]
            for pattern in unit_type_patterns:
                match = re.search(pattern, page_text)
                if match:
                    unit_text = match.group(1).strip()
                    if unit_text and unit_text not in ['', '주택유형', '집구조']:
                        fields["unit_type"] = unit_text
                        break

            company_patterns = {
                "company_name": r'상호\s*:\s*([^\n]+)',
                "representative": r'대표자\s*:\s*([^\n]+)',
                "contact_phone": r'문의전화\s*:\s*([^\n]+)',
                "homepage": r'홈페이지\s*:\s*([^\n]+)',
            }
            for key, pattern in company_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            price_patterns = {
                "deposit": r'보증금\s*:\s*([^\n]+)',
                "monthly_rent": r'월세\s*:\s*([^\n]+)',
                "management_fee": r'관리비\s*:\s*([^\n]+)',
            }
            for key, pattern in price_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            housing_detail_patterns = {
                "district_type": r'지역/지구:\s*([^\n]+)',
                "building_scale": r'규\s*모:\s*([^\n]+)',
                "building_structure": r'구\s*조:\s*([^\n]+)',
                "site_area": r'대지면적\s*:\s*([^\n]+)',
                "total_floor_area": r'연\s*면\s*적\s*:\s*([^\n]+)',
                "approval_date": r'사용승인\s*:\s*([^\n]+)',
                "parking": r'주\s*차\s*:\s*([^\n]+)',
                "total_units": r'총\s*세대\s*:\s*([^\n]+)',
                "total_people": r'총\s*주거인원\s*:\s*([^\n]+)',
                "total_rooms": r'총\s*실\s*:\s*([^\n]+)',
            }
            for key, pattern in housing_detail_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            facility_patterns = {
                "subway_station": r'지하철역\s*:\s*([^\n]+)',
                "bus_info": r'버스\s*정보\s*:\s*([^\n]+)',
                "nearby_mart": r'주변\s*마트\s*정보\s*:\s*([^\n]+)',
                "nearby_hospital": r'주변\s*병원\s*정보\s*:\s*([^\n]+)',
                "nearby_school": r'주변\s*학교\s*정보\s*:\s*([^\n]+)',
                "nearby_facilities": r'주변\s*시설\s*정보\s*:\s*([^\n]+)',
                "nearby_cafe": r'주변\s*카페\s*정보\s*:\s*([^\n]+)',
            }
            for key, pattern in facility_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            occupancy_patterns = {
                "target_occupancy": r'입주대상\s*:\s*([^\n]+)',
                "building_type": r'주거형태\s*:\s*([^\n]+)',
                "unit_type": r'주택유형\s*:\s*([^\n]+)',
                "move_in_date": r'입주가능일\s*:\s*([^\n]+)',
                "availability": r'입주가능\s*:\s*([^\n]+)',
            }
            for key, pattern in occupancy_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

            other_patterns = {
                "house_name": r'주택명\s*:\s*([^\n]+)',
                "address": r'주소\s*:\s*([^\n]+)',
                "theme": r'테마\s*:\s*([^\n]+)',
                "features": r'특징\s*:\s*([^\n]+)',
                "description": r'설명\s*:\s*([^\n]+)',
            }
            for key, pattern in other_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()

        # 편의시설 정보 추가
        try:
            facility_info = extract_facility_info(page)
            if facility_info:
                fields["facility_info"] = facility_info
        except Exception as e:
            print(f"Error extracting facility info: {e}")

        # 관련 주택 정보 추가
        try:
            related_housing_info = extract_related_housing_info(page)
            if related_housing_info:
                fields["related_housing_info"] = related_housing_info
        except Exception as e:
            print(f"Error extracting related housing info: {e}")

        # additional_info 추출 (기존 JSON에서 가져온 정보)
        additional_info = {}
        
        # 입주타입, 면적, 입주가능일 등 추가 정보
        occupancy_type = fields.get("unit_type", "")
        if occupancy_type:
            # HTML 태그 제거
            occupancy_type = re.sub(r'<[^>]+>', '', occupancy_type).strip()
            if occupancy_type:
                additional_info["입주타입"] = occupancy_type
        
        # 면적 정보 (텍스트에서 추출)
        area_match = re.search(r'전용\s*([0-9.,]+)\s*m²\s*/\s*공용\s*([0-9.,]+)\s*m²', page_text)
        if area_match:
            private_area = area_match.group(1)
            common_area = area_match.group(2)
            additional_info["면적"] = f"전용 {private_area}m² / 공용 {common_area}m²"
        
        # 입주가능일
        move_in_date = fields.get("move_in_date", "")
        if move_in_date:
            additional_info["입주가능일"] = move_in_date
        
        # 주소 (더 정확한 주소가 있다면)
        address = fields.get("address", "")
        if address:
            # HTML 태그 제거
            address = re.sub(r'<[^>]+>', '', address).strip()
            if address:
                additional_info["주소"] = address
        
        # facility_info 구성
        facility_info = {}
        if fields.get("subway_station"):
            facility_info["subway"] = fields["subway_station"]
        if fields.get("bus_info"):
            facility_info["bus"] = fields["bus_info"]
        if fields.get("nearby_mart"):
            facility_info["nearby_마트"] = fields["nearby_mart"]
        if fields.get("nearby_hospital"):
            facility_info["nearby_병원"] = fields["nearby_hospital"]
        if fields.get("nearby_school"):
            facility_info["nearby_학교"] = fields["nearby_school"]
        if fields.get("nearby_facilities"):
            facility_info["nearby_시설"] = fields["nearby_facilities"]
        if fields.get("nearby_cafe"):
            facility_info["nearby_카페"] = fields["nearby_cafe"]
        
        if facility_info:
            additional_info["facility_info"] = facility_info
        
        if additional_info:
            fields["additional_info"] = additional_info

        # cohouse_text_extracted_info 생성
        cohouse_text_info = {}
        
        # 기본 정보 (HTML 태그 제거)
        if fields.get("building_type"):
            building_type = re.sub(r'<[^>]+>', '', fields["building_type"]).strip()
            if building_type:
                cohouse_text_info["building_type"] = building_type
                # raw.csv를 위해 최상위 레벨에도 저장
                fields["building_type"] = building_type
        if fields.get("unit_type"):
            unit_type = re.sub(r'<[^>]+>', '', fields["unit_type"]).strip()
            if unit_type:
                cohouse_text_info["unit_type"] = unit_type
                # raw.csv를 위해 최상위 레벨에도 저장
                fields["unit_type"] = unit_type
        if fields.get("target_occupancy"):
            target_occupancy = re.sub(r'<[^>]+>', '', fields["target_occupancy"]).strip()
            if target_occupancy:
                cohouse_text_info["target_occupancy"] = target_occupancy
        
        # 텍스트에서 패턴 추출
        extracted_patterns = {}
        if page_text:
            text = re.sub(r"<[^>]+>", " ", page_text)
            text = re.sub(r"\s+", " ", text).strip()

            areas = re.findall(r"(\d+(?:\.\d+)?)\s*(?:㎡|m²|m2)", text)
            if areas:
                seen = set()
                a_out = []
                for a in areas:
                    if a not in seen:
                        seen.add(a)
                        a_out.append(a)
                extracted_patterns["areas"] = a_out

            prices = []
            for m in re.finditer(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{2,})\s*원", text):
                prices.append(m.group(1))
            if prices:
                prices = [p for p in prices if not re.fullmatch(r"0+", p)]
                seen = set()
                p_out = []
                for p in prices:
                    if p not in seen:
                        seen.add(p)
                        p_out.append(p)
                if p_out:
                    extracted_patterns["prices"] = p_out

            dates = []
            for m in re.finditer(r"(\d{4}[.\-\/]\d{1,2}[.\-\/]\d{1,2})", text):
                dates.append(m.group(1))
            if dates:
                seen = set()
                d_out = []
                for d in dates:
                    if d not in seen:
                        seen.add(d)
                        d_out.append(d)
                extracted_patterns["dates"] = d_out

        if extracted_patterns:
            cohouse_text_info["extracted_patterns"] = extracted_patterns

        if cohouse_text_info:
            fields["cohouse_text_extracted_info"] = cohouse_text_info

    except Exception as e:
        print(f"Error in extract_cohouse_specific_fields: {e}")

    return fields

def parse_house_name(page, list_title_fallback: str = "") -> str:
    """Prefer detail-specific fields; avoid global page headings like '사회주택'."""
    candidates = [".detail-box h3", ".detail-tit", ".bbsV_title", ".view_tit", "article h3"]
    for sel in candidates:
        try:
            el = page.locator(sel).first
            if el.count():
                t = _clean_title(el.inner_text().strip())
                if t:
                    return t
        except Exception:
            pass

    label_keys = ["주택명", "공고명", "시설명", "단지명", "프로젝트명"]
    for key in label_keys:
        try:
            th = page.locator(f"table th:has-text('{key}')").first
            if th.count():
                td = th.locator("xpath=following-sibling::td[1]").first
                if td.count():
                    t = _clean_title(td.inner_text().strip())
                    if t:
                        return t
        except Exception:
            pass

    return _clean_title(list_title_fallback)

def extract_platform_intro_text(page, container_selectors: list[str]) -> str:
    """Extract main body text from intro/policy pages."""
    for sel in container_selectors:
        try:
            if page.locator(sel).count():
                txt = page.locator(sel).inner_text().strip()
                if txt:
                    return re.sub(r"\s+\n", "\n", txt)
        except Exception:
            continue
    return page.locator("body").inner_text().strip()[:4000]

def extract_detail_text(page) -> str:
    """상세 페이지의 전체 본문 텍스트 추출 - sohouse와 cohouse 모두 지원"""
    # ★ sohouse일 경우 상세 진입 보정
    try:
        u = page.url
    except Exception:
        u = ""
    if "soco.seoul.go.kr" in u and "/soHouse/" in u:
        try:
            _ensure_sohouse_detail_page(page)
        except Exception:
            pass

    try:
        # URL에 따라 다른 선택자 사용
        if "coHouse" in u or "cohouse" in u:
            # cohouse 전용 선택자 (더 구체적이고 포괄적)
            cohouse_selectors = [
                ".subpage_content",  # 메인 콘텐츠 영역
                ".detail-box",       # 상세 정보 박스
                ".viewTable",        # 뷰 테이블
                ".detail-info",      # 상세 정보
                ".info-box",         # 정보 박스
                ".bbsV_wrap",        # 게시판 래퍼
                ".bbsV_cont",        # 게시판 콘텐츠
                ".view-content",     # 뷰 콘텐츠
                ".detail-content",   # 상세 콘텐츠
                ".board-view",       # 게시판 뷰
                ".view-wrap",        # 뷰 래퍼
                ".detail-wrap",      # 상세 래퍼
                "article.detail",    # 아티클 상세
                ".detail-list",      # 상세 리스트
                ".flexbox-detail",   # 플렉스박스 상세
                "#content",          # 콘텐츠 영역
                ".content",          # 콘텐츠 클래스
                "main",              # 메인 요소
                ".main-content",     # 메인 콘텐츠
            ]
            
            for sel in cohouse_selectors:
                try:
                    if page.locator(sel).count():
                        txt = page.locator(sel).inner_text().strip()
                        if txt and len(txt) > 200:  # 더 긴 텍스트 요구
                            return re.sub(r"\s+\n", "\n", txt)
                except Exception:
                    continue
                    
        elif "soHouse" in u or "sohouse" in u:
            # sohouse 전용 선택자
            sohouse_selectors = [
            ".subpage_content", ".homeSearch", ".schTitle",
            "tbody#cohomeForm", ".tbl_list", ".boardTable",
            ".detail-info", ".info-box", ".bbsV_wrap", ".bbsV_cont",
            "div.detail-box", ".view-content",
                "#content", ".content", "main",
        ]

            for sel in sohouse_selectors:
                try:
                    if page.locator(sel).count():
                        txt = page.locator(sel).inner_text().strip()
                        if txt and len(txt) > 100:
                            return re.sub(r"\s+\n", "\n", txt)
                except Exception:
                    continue
        else:
            # 기본 선택자 (기존 로직)
            default_selectors = [
                "article.detail", ".detail-list", ".flexbox-detail",
                ".detail-box", ".bbsV_wrap", "article", ".viewTable",
                "#content", ".content", ".detail-content", ".view-content",
                ".board-view", ".view-wrap", ".detail-wrap",
            ]
            
            for sel in default_selectors:
                try:
                    if page.locator(sel).count():
                        txt = page.locator(sel).inner_text().strip()
                        if txt and len(txt) > 100:
                            return re.sub(r"\s+\n", "\n", txt)
                except Exception:
                    continue

        # 최종 폴백: body 전체 텍스트
        text = page.locator("body").inner_text().strip()
        
        # 최종수정일 정보 추가
        last_modified = parse_last_modified_date(page)
        if last_modified:
            text = f"최종수정일: {last_modified}\n\n" + text
        
        return text
    except Exception:
        return ""

def extract_key_value_pairs(page) -> dict:
    """상세 페이지에서 라벨-값 쌍 추출"""
    kv_pairs = {}

    try:
        tables = page.locator("table")
        for i in range(tables.count()):
            table = tables.nth(i)
            ths = table.locator("th")
            tds = table.locator("td")
            for j in range(min(ths.count(), tds.count())):
                try:
                    label = ths.nth(j).inner_text().strip()
                    value = tds.nth(j).inner_text().strip()
                    if label and value and len(label) < 50:
                        clean_label = re.sub(r"[:：]\s*$", "", label)
                        clean_label = re.sub(r"\s*\([^)]*\)\s*$", "", clean_label)
                        clean_label = clean_label.strip()
                        if clean_label and len(clean_label) > 0:
                            kv_pairs[clean_label] = value
                except Exception:
                    continue
    except Exception:
        pass

    try:
        dashlines = page.locator("li.dashline")
        for i in range(dashlines.count()):
            try:
                text = dashlines.nth(i).inner_text().strip()
                if ":" in text or "：" in text:
                    parts = re.split(r"[:：]", text, 1)
                    if len(parts) == 2:
                        label = parts[0].strip()
                        value = parts[1].strip()
                        if label and value and len(label) < 50:
                            kv_pairs[label] = value
            except Exception:
                continue
    except Exception:
        pass

    try:
        strongs = page.locator("strong")
        for i in range(strongs.count()):
            try:
                strong = strongs.nth(i)
                label = strong.inner_text().strip()
                if label and len(label) < 50:
                    parent = strong.locator("xpath=parent::*").first
                    if parent.count():
                        parent_text = parent.inner_text().strip()
                        if ":" in parent_text or "：" in parent_text:
                            parts = re.split(r"[:：]", parent_text, 1)
                            if len(parts) == 2 and parts[0].strip() == label:
                                value = parts[1].strip()
                                if value:
                                    kv_pairs[label] = value
            except Exception:
                continue
    except Exception:
        pass

    return kv_pairs

def filter_sh_announcement_title(title: str) -> bool:
    """SH 공고 제목 필터링 - '모집공고' 또는 '모집 공고' 포함"""
    if not title:
        return False
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in ["모집공고", "모집 공고", "입주자모집", "입주자 모집"])

def filter_lh_announcement_title(title: str) -> bool:
    """LH 공고 제목 필터링 - 서울 관련 및 2024년 이후"""
    if not title:
        return False
    title_lower = title.lower()
    seoul_keywords = ["서울", "seoul", "수도권"]
    has_seoul = any(keyword in title_lower for keyword in seoul_keywords)

    import re
    year_match = re.search(r"20(\d{2})", title)
    if year_match:
        year = int(year_match.group(1))
        if year >= 24:
            return has_seoul
    return has_seoul

def parse_youth_address(page) -> str:
    """청년주택 특화 주소 추출 - youth 페이지 구조에 최적화"""
    try:
        # 청년주택 특화 선택자들
        youth_selectors = [
            "li.dashline p:has-text('주소')",
            "strong:has-text('주소')",
            ".youth-detail p:has-text('주소')",
            ".youth-info p:has-text('주소')",
            "div[class*='youth'] p:has-text('주소')",
            "div[class*='detail'] p:has-text('주소')",
            "div[class*='info'] p:has-text('주소')",
        ]
        
        for selector in youth_selectors:
            try:
                elements = page.locator(selector)
                for i in range(elements.count()):
                    element = elements.nth(i)
                    text = element.inner_text().strip()
                    if "주소" in text:
                        addr_part = text.split("주소")[-1].strip()
                        if addr_part.startswith(":"):
                            addr_part = addr_part[1:].strip()
                        elif addr_part.startswith("："):
                            addr_part = addr_part[1:].strip()
                        if addr_part and len(addr_part) > 5:
                            return addr_part[:200]
            except Exception:
                continue
    except Exception:
        pass
    
    # 기본 주소 파싱으로 폴백
    return parse_address_strict(page)

def extract_youth_specific_fields(page, detail_text: str = "", detail_desc: dict = None) -> dict:
    """청년주택 특화 필드 추출 - co/so와 동일한 구조로 통일 + 홈페이지 데이터 통합"""
    fields = {}
    try:
        page_text = detail_text if detail_text else page.content()

        # co/so와 동일한 기본 필드 추출
        try:
            # 주소는 기본 parse_address_strict 사용 (youth 특화는 parse_youth_address에서 처리)
            address = parse_address_strict(page)
            if address:
                fields["address"] = address

            building_type = parse_building_type(page)
            if building_type:
                fields["building_type"] = building_type
                fields["building_type"] = building_type

            eligibility = parse_eligibility(page)
            if eligibility:
                fields["target_occupancy"] = eligibility
                fields["eligibility"] = eligibility

            subway_station = parse_subway_station(page)
            if subway_station:
                fields["subway_station"] = subway_station
        except Exception as e:
            print(f"Error in youth basic field extraction: {e}")

        # co/so와 동일한 패턴으로 텍스트 기반 보강
        if page_text:
            # co/so와 동일한 필드명 사용
            common_patterns = {
                "house_name": r'주택명\s*:\s*([^\n]+)',
                "address": r'주소\s*:\s*([^\n]+)',
                "building_type": r'주택유형\s*:\s*([^\n]+)',
                "building_type": r'주거형태\s*:\s*([^\n]+)',
                "unit_type": r'세대유형\s*:\s*([^\n]+)',
                "target_occupancy": r'입주대상\s*:\s*([^\n]+)',
                "theme": r'테마\s*:\s*([^\n]+)',
                "subway_station": r'지하철역\s*:\s*([^\n]+)',
            }
            
            # 모집공고 페이지 특화 패턴 추가
            announcement_patterns = {
                "house_name": r'■단지명\s*:\s*([^\n]+)',
                "address": r'■주택위치\s*:\s*([^\n]+)',
                "building_type": r'■공급호수\s*:\s*([^\n]+)',
                "company_name": r'■사업주체\s*:\s*([^\n]+)',
                "construction_company": r'■시공사\s*:\s*([^\n]+)',
            }
            
            # 먼저 모집공고 패턴 시도
            for key, pattern in announcement_patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    fields[key] = match.group(1).strip()
            
            # 그 다음 일반 패턴 시도 (기존 값이 없을 때만)
            for key, pattern in common_patterns.items():
                if key not in fields:  # 이미 모집공고 패턴에서 추출된 경우 스킵
                    match = re.search(pattern, page_text)
                    if match:
                        fields[key] = match.group(1).strip()
        
        # 홈페이지 데이터 통합
        if detail_desc and detail_desc.get("homepage_data"):
            homepage_data_list = detail_desc["homepage_data"]
            fields["homepage_data"] = homepage_data_list
            
            # 홈페이지에서 추출한 정보를 우선적으로 사용
            for homepage_data in homepage_data_list:
                # 주소 정보 (홈페이지가 더 정확할 수 있음)
                if homepage_data.get("location_info", {}).get("addresses"):
                    addresses = homepage_data["location_info"]["addresses"]
                    if addresses and not fields.get("address"):
                        fields["address"] = addresses[0]
                
                # 연락처 정보
                if homepage_data.get("contact_info"):
                    contact_info = homepage_data["contact_info"]
                    if contact_info.get("phones"):
                        fields["contact_phones"] = contact_info["phones"]
                    if contact_info.get("emails"):
                        fields["contact_emails"] = contact_info["emails"]
                
                # 가격 정보
                if homepage_data.get("pricing_info", {}).get("prices"):
                    fields["pricing_info"] = homepage_data["pricing_info"]
                
                # 편의시설 정보
                if homepage_data.get("facilities"):
                    fields["homepage_facilities"] = homepage_data["facilities"]
                
                # 상세 정보
                if homepage_data.get("detailed_info"):
                    fields["homepage_detailed_info"] = homepage_data["detailed_info"]
                
                # 이미지 정보
                if homepage_data.get("images"):
                    fields["homepage_images"] = homepage_data["images"]
                if homepage_data.get("floor_plans"):
                    fields["homepage_floor_plans"] = homepage_data["floor_plans"]

        # 편의시설 정보 추가
        try:
            facility_info = extract_facility_info(page)
            if facility_info:
                fields["facility_info"] = facility_info
        except Exception as e:
            print(f"Error extracting facility info: {e}")

        # 관련 주택 정보 추가
        try:
            related_housing_info = extract_related_housing_info(page)
            if related_housing_info:
                fields["related_housing_info"] = related_housing_info
        except Exception as e:
            print(f"Error extracting related housing info: {e}")

        # 청년주택 특화 추가 필드들
        try:
            main_images = page.locator("img[src*='main'], img[src*='represent'], .main-image img, .represent-image img")
            if main_images.count() > 0:
                fields["main_image"] = main_images.first.get_attribute("src") or ""
        except Exception:
            pass

        try:
            floor_plan_images = page.locator("img[src*='floor'], img[src*='plan'], img[src*='평면']")
            if floor_plan_images.count() > 0:
                fields["floor_plan_images"] = [floor_plan_images.nth(i).get_attribute("src") for i in range(floor_plan_images.count())]
        except Exception:
            pass

    except Exception as e:
        print(f"Error in extract_youth_specific_fields: {e}")

    return fields

def _clean_youth_text_content(text: str) -> str:
    """텍스트 정리 - 상단 불필요한 부분 제거"""
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = []
    skip_keywords = [
        "입주현황", "입주자격", "입주조건", "입주절차", "입주안내",
        "모집공고", "공고", "공지사항", "공지", "안내사항",
        "홈", "메인", "메뉴", "네비게이션", "탐색", "검색",
        "로그인", "회원가입", "로그아웃", "마이페이지",
        "이전", "다음", "목록", "뒤로", "돌아가기",
        "서울특별시", "서울시", "청년안심주택", "청년주택",
        "주택찾기", "주택정보", "주택상세", "주택소개",
        "상세정보", "기본정보", "입주정보", "입주현황",
        "단지정보", "단지소개", "단지안내", "단지현황",
        "위치정보", "교통정보", "주변시설", "주변환경",
        "문의", "연락처", "담당자", "관리사무소",
        "copyright", "저작권", "개인정보처리방침", "이용약관",
        "사이트맵", "관련사이트", "바로가기", "링크",
        "팝업", "새창", "새창열림", "새창닫기",
        "페이지", "페이지네이션", "페이징", "페이지 번호",
        "총", "건", "개", "항목", "목록", "리스트",
        "정렬", "필터", "검색어", "검색결과",
        "선택", "체크", "라디오", "체크박스", "버튼",
        "입력", "텍스트", "폼", "양식", "제출",
        "확인", "취소", "저장", "삭제", "수정",
        "등록", "신청", "접수", "완료", "처리",
        "오류", "에러", "경고", "알림", "메시지",
        "로딩", "처리중", "대기", "진행중", "완료",
        "날짜", "시간", "작성일", "수정일", "등록일",
        "조회수", "추천수", "댓글수", "좋아요",
        "공유", "인쇄", "다운로드", "업로드", "첨부",
        "파일", "이미지", "사진", "그림", "도표",
        "표", "테이블", "목록", "리스트", "항목",
        "번호", "순번", "인덱스", "ID", "코드",
        "이름", "제목", "내용", "설명", "요약",
        "상세", "자세히", "더보기", "펼치기", "접기",
        "전체", "일부", "부분", "선택", "모두",
        "없음", "비어있음", "데이터없음", "정보없음",
        "준비중", "개발중", "서비스중", "점검중",
        "임시", "테스트", "샘플", "예시", "데모",
    ]
    start_found = False
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if any(keyword in line for keyword in skip_keywords):
            continue
        if any(keyword in line for keyword in ["주택명", "단지명", "주소", "위치", "면적", "입주", "모집", "공급"]):
            start_found = True
            cleaned_lines.append(line)
        elif start_found:
            cleaned_lines.append(line)
    if not start_found:
        for line in lines:
            line = line.strip()
            if line and not any(keyword in line for keyword in skip_keywords):
                cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def extract_units_from_notice(page, detail_text: str = "", json_data: dict = None, occupancy_table_path: str = None) -> List[Dict]:
    """
    하나의 공고에서 여러 units를 추출하는 함수
    우선순위: occupancy 테이블 > JSON 데이터 > 텍스트 추출
    """
    units = []
    
    # 기본 unit 정보 추출
    unit_type = parse_building_type(page)
    building_type = parse_building_type(page)
    
    # 1. occupancy 테이블에서 units 추출 (가장 정확)
    if occupancy_table_path and Path(occupancy_table_path).exists():
        units = _extract_units_from_occupancy_table(occupancy_table_path, unit_type, building_type)
        if units:
            return units
    
    # 2. JSON 데이터에서 extracted_patterns 추출
    areas = []
    prices = []
    
    if json_data and 'cohouse_text_extracted_info' in json_data:
        extracted = json_data['cohouse_text_extracted_info'].get('extracted_patterns', {})
        areas = [float(area) for area in extracted.get('areas', [])]
        prices = [int(price.replace(',', '')) for price in extracted.get('prices', [])]
    
    # 3. JSON에서 추출하지 못한 경우 텍스트에서 추출
    if not areas and detail_text:
        area_patterns = [
            r'(\d+(?:\.\d+)?)\s*㎡',
            r'(\d+(?:\.\d+)?)\s*평',
            r'(\d+(?:\.\d+)?)\s*제곱미터'
        ]
        for pattern in area_patterns:
            matches = re.findall(pattern, detail_text)
            areas.extend([float(m) for m in matches])
    
    if not prices and detail_text:
        price_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*만원',
            r'(\d{1,3}(?:,\d{3})*)\s*원',
            r'(\d{1,3}(?:,\d{3})*)\s*만'
        ]
        for pattern in price_patterns:
            matches = re.findall(pattern, detail_text)
            for match in matches:
                # 콤마 제거하고 숫자로 변환
                price = int(match.replace(',', ''))
                prices.append(price)
    
    # 4. 면적과 가격이 여러 개인 경우, 각각을 별도 unit으로 생성
    if len(areas) > 1 or len(prices) > 1:
        # 면적과 가격의 개수를 맞춰서 units 생성
        max_units = max(len(areas), len(prices), 1)
        
        for i in range(max_units):
            # 가격 매핑 개선: 보증금은 첫 번째 가격, 월임대료는 두 번째 가격 등
            deposit = None
            rent = None
            maintenance_fee = None
            
            if len(prices) > 0:
                # 보증금 (일반적으로 가장 큰 금액)
                deposit_candidates = [p for p in prices if p >= 1000000]  # 100만원 이상
                deposit = deposit_candidates[0] if deposit_candidates else prices[0]
                
                # 월임대료 (보증금보다 작은 금액들 중에서)
                rent_candidates = [p for p in prices if p < deposit and p >= 100000]  # 10만원 이상, 보증금보다 작음
                rent = rent_candidates[0] if rent_candidates else (prices[1] if len(prices) > 1 else None)
                
                # 관리비 (가장 작은 금액)
                maintenance_candidates = [p for p in prices if p < 100000]  # 10만원 미만
                maintenance_fee = maintenance_candidates[0] if maintenance_candidates else None
            
            unit = {
                'unit_type': unit_type,
                'building_type': building_type,
                'area_m2': areas[i] if i < len(areas) else areas[0] if areas else None,
                'deposit': deposit,
                'rent': rent,
                'maintenance_fee': maintenance_fee,
                'floor': None,
                'room_number': f"{i+1}호" if i > 0 else None,
                'occupancy_available_at': None,
                'unit_extra': {
                    'unit_index': i,
                    'is_multiple_units': True,
                    'data_source': 'json_patterns'
                }
            }
            units.append(unit)
    else:
        # 기본 unit 생성 (하나만)
        unit = {
            'unit_type': unit_type,
            'building_type': building_type,
            'area_m2': areas[0] if areas else None,
            'deposit': prices[0] if len(prices) > 0 else None,
            'rent': prices[1] if len(prices) > 1 else None,
            'maintenance_fee': prices[2] if len(prices) > 2 else None,
            'floor': None,
            'room_number': None,
            'occupancy_available_at': None,
            'unit_extra': {
                'unit_index': 0,
                'is_multiple_units': False,
                'data_source': 'json_patterns'
            }
        }
        units.append(unit)
    
    return units

def _extract_units_from_occupancy_table(table_path: str, unit_type: str, building_type: str) -> List[Dict]:
    """
    occupancy 테이블에서 units 추출 (새로운 ID 컬럼 지원)
    """
    import pandas as pd
    from pathlib import Path
    
    units = []
    
    try:
        # CSV 파일 읽기
        df = pd.read_csv(table_path)
        
        # 헤더 행 제외하고 각 행을 unit으로 처리
        for i, row in df.iterrows():
            if i == 0:  # 헤더 행 스킵
                continue
                
            # 방이름에서 호수 추출
            room_name = str(row.get('방이름', '')).strip()
            if not room_name or room_name == 'nan':
                continue
                
            # 면적 추출 (m² 제거)
            area_str = str(row.get('면적', '')).strip()
            area_m2 = None
            if area_str and area_str != 'nan':
                area_match = re.search(r'(\d+(?:\.\d+)?)', area_str)
                if area_match:
                    area_m2 = float(area_match.group(1))
            
            # 가격 추출 (콤마와 "원" 제거)
            deposit_str = str(row.get('보증금', '')).strip()
            rent_str = str(row.get('월임대료', '')).strip()
            maintenance_str = str(row.get('관리비', '')).strip()
            
            deposit = _parse_price(deposit_str)
            rent = _parse_price(rent_str)
            maintenance_fee = _parse_price(maintenance_str)
            
            # 층과 호수 추출
            floor = _parse_int(row.get('층'))
            room_number = str(row.get('호', '')).strip()
            if room_number == 'nan':
                room_number = None
                
            # 인원수 추출
            occupancy = _parse_int(row.get('인원'))
            
            # 새로운 ID 필드들 추출 (하위 호환성 지원)
            crawler_id = str(row.get('crawler_id', '')).strip() if 'crawler_id' in row else None
            space_id = str(row.get('space_id', '')).strip() if 'space_id' in row else None
            
            # 기존 필드들 (하위 호환성)
            record_id = str(row.get('record_id', '')).strip() if 'record_id' in row else None
            occupancy_id = str(row.get('occupancy_id', '')).strip() if 'occupancy_id' in row else None
            notice_id = str(row.get('notice_id', '')).strip() if 'notice_id' in row else None
            
            unit = {
                'unit_type': unit_type,
                'building_type': building_type,
                'area_m2': area_m2,
                'deposit': deposit,
                'rent': rent,
                'maintenance_fee': maintenance_fee,
                'floor': floor,
                'room_number': room_number,
                'occupancy': occupancy,
                'occupancy_available_at': None,
                'unit_extra': {
                    'unit_index': i - 1,  # 헤더 제외한 인덱스
                    'is_multiple_units': True,
                    'data_source': 'occupancy_table',
                    'room_name': room_name,
                    'crawler_id': crawler_id,
                    'space_id': space_id,
                    # 하위 호환성을 위한 기존 필드들
                    'record_id': record_id,
                    'occupancy_id': occupancy_id,
                    'notice_id': notice_id
                }
            }
            units.append(unit)
            
    except Exception as e:
        print(f"Error parsing occupancy table {table_path}: {e}")
    
    return units

def _parse_price(price_str: str) -> int:
    """가격 문자열을 정수로 변환"""
    if not price_str or price_str == 'nan' or price_str == '0원':
        return None
        
    # "연락 후 확인", "문의" 등의 경우 None 반환
    if any(keyword in price_str for keyword in ['연락', '문의', '확인', '상담']):
        return None
        
    # 숫자만 추출
    price_match = re.search(r'(\d{1,3}(?:,\d{3})*)', price_str)
    if price_match:
        return int(price_match.group(1).replace(',', ''))
    
    return None

def _parse_int(value) -> int:
    """값을 정수로 변환"""
    if pd.isna(value) or value == '' or str(value).strip() == 'nan':
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

def filter_json_fields_for_cohouse(kv_pairs: dict, platform_fields: dict) -> dict:
    """공동체주택 JSON 필드 필터링 - sohouse와 동일한 구조"""
    import re
    from datetime import datetime

    def _strip_tags_local(s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _nz(v):
        return isinstance(v, str) and v.strip() and v.strip() != "-"

    def pick(*keys):
        for k in keys:
            v = platform_fields.get(k)
            if _nz(v):
                return _strip_tags_local(v)
        for k in keys:
            v = kv_pairs.get(k)
            if _nz(v):
                return _strip_tags_local(v)
        return ""

    cleaned_text = platform_fields.pop("text_content", "") or ""
    result = {}

    # 1) facilities
    facilities = {}
    subway = pick("subway_station")
    if _nz(subway):
        facilities["subway_station"] = subway
    
    # facility_info에서 편의시설 정보 추가 (subway 중복 제거)
    if "facility_info" in platform_fields:
        facility_info = platform_fields["facility_info"]
        if isinstance(facility_info, dict):
            # subway는 이미 subway_station으로 추가되었으므로 제외
            filtered_facility_info = {k: v for k, v in facility_info.items() if k != "subway"}
            facilities.update(filtered_facility_info)
    
    # additional_info에서 facility_info 추출
    if "additional_info" in platform_fields:
        additional_info = platform_fields["additional_info"]
        if isinstance(additional_info, dict) and "facility_info" in additional_info:
            additional_facility_info = additional_info["facility_info"]
            if isinstance(additional_facility_info, dict):
                # subway는 이미 subway_station으로 추가되었으므로 제외
                filtered_additional_facility = {k: v for k, v in additional_facility_info.items() if k != "subway"}
                facilities.update(filtered_additional_facility)
    
    if facilities:
        result["facilities"] = facilities

    # 2) company_info
    company_info = {}
    cn = pick("company_name")
    if _nz(cn):
        company_info["company_name"] = cn
    rep = pick("representative")
    if _nz(rep):
        company_info["representative"] = rep
    hp = pick("contact_phone", "phone", "문의전화")
    if _nz(hp):
        company_info["contact_phone"] = hp
    home = pick("homepage", "홈페이지")
    if _nz(home):
        company_info["homepage"] = home
    if company_info:
        result["company_info"] = company_info

    # 3) housing_specific
    housing_specific = {}
    deposit = pick("deposit", "보증금")
    if _nz(deposit):
        housing_specific["deposit_range"] = deposit
    monthly_rent = pick("monthly_rent", "월세")
    if _nz(monthly_rent):
        housing_specific["monthly_rent_range"] = monthly_rent
    management_fee = pick("management_fee", "관리비")
    if _nz(management_fee):
        housing_specific["management_fee"] = management_fee
    elig = pick("target_occupancy", "입주대상")
    if _nz(elig):
        housing_specific["target_occupancy_detail"] = elig
    
    # extracted_patterns에서 가격 정보 추출
    if "cohouse_text_extracted_info" in platform_fields:
        cohouse_info = platform_fields["cohouse_text_extracted_info"]
        if isinstance(cohouse_info, dict) and "extracted_patterns" in cohouse_info:
            patterns = cohouse_info["extracted_patterns"]
            if isinstance(patterns, dict):
                # 가격 패턴에서 보증금과 월세 추출
                prices = patterns.get("prices", [])
                if prices:
                    # 숫자만 추출하여 정렬
                    numeric_prices = []
                    for price in prices:
                        # 쉼표 제거하고 숫자만 추출
                        clean_price = re.sub(r'[^\d]', '', price)
                        if clean_price and len(clean_price) >= 4:  # 최소 4자리 이상
                            numeric_prices.append(int(clean_price))
                    
                    if numeric_prices:
                        numeric_prices.sort()
                        min_price = numeric_prices[0]
                        max_price = numeric_prices[-1]
                        
                        # 보증금 범위 (큰 금액들)
                        large_amounts = [p for p in numeric_prices if p >= 10000000]  # 1천만원 이상
                        if large_amounts:
                            large_amounts.sort()
                            min_deposit = large_amounts[0]
                            max_deposit = large_amounts[-1]
                            housing_specific["deposit_range"] = f"{min_deposit:,}원 ~ {max_deposit:,}원"
                        
                        # 월세 범위 (작은 금액들)
                        small_amounts = [p for p in numeric_prices if p < 10000000]  # 1천만원 미만
                        if small_amounts:
                            small_amounts.sort()
                            min_rent = small_amounts[0]
                            max_rent = small_amounts[-1]
                            housing_specific["monthly_rent_range"] = f"{min_rent:,}원 ~ {max_rent:,}원"
    
    # additional_info에서 housing_specific 정보 추출
    if "additional_info" in platform_fields:
        additional_info = platform_fields["additional_info"]
        if isinstance(additional_info, dict):
            # 입주타입
            occupancy_type = additional_info.get("입주타입")
            if _nz(occupancy_type):
                housing_specific["occupancy_type"] = occupancy_type
            
            # 면적 정보
            area_info = additional_info.get("면적")
            if _nz(area_info):
                housing_specific["area_info"] = area_info
                
                # 면적에서 전용/공용 면적 추출
                area_match = re.search(r'전용\s*([0-9.,]+)\s*m²', area_info)
                if area_match:
                    housing_specific["private_area"] = area_match.group(1) + "m²"
                
                area_match = re.search(r'공용\s*([0-9.,]+)\s*m²', area_info)
                if area_match:
                    housing_specific["common_area"] = area_match.group(1) + "m²"
            
            # 입주가능일
            move_in_date = additional_info.get("입주가능일")
            if _nz(move_in_date):
                housing_specific["move_in_date"] = move_in_date
    
    # extracted_patterns에서 면적 정보 추출
    if "cohouse_text_extracted_info" in platform_fields:
        cohouse_info = platform_fields["cohouse_text_extracted_info"]
        if isinstance(cohouse_info, dict) and "extracted_patterns" in cohouse_info:
            patterns = cohouse_info["extracted_patterns"]
            if isinstance(patterns, dict):
                # 면적 패턴에서 가장 큰 면적을 총 면적으로 사용
                areas = patterns.get("areas", [])
                if areas:
                    # 숫자로 변환하여 정렬
                    numeric_areas = []
                    for area in areas:
                        try:
                            numeric_areas.append(float(area))
                        except ValueError:
                            continue
                    
                    if numeric_areas:
                        numeric_areas.sort()
                        # 가장 큰 면적을 총 면적으로 사용
                        total_area = numeric_areas[-1]
                        housing_specific["total_area"] = f"{total_area}m²"
                        
                        # 면적 범위도 제공
                        if len(numeric_areas) > 1:
                            min_area = numeric_areas[0]
                            max_area = numeric_areas[-1]
                            housing_specific["area_range"] = f"{min_area}m² ~ {max_area}m²"
    
    if housing_specific:
        result["housing_specific"] = housing_specific

    # 4) building_details
    building_details = {}
    district = pick("district_type", "지역/지구")
    if _nz(district):
        building_details["district_type"] = district
    bscale = pick("building_scale", "규모", "규 모")
    if _nz(bscale):
        building_details["building_scale"] = bscale
    bstruct = pick("building_structure", "구조", "구 조")
    if _nz(bstruct):
        building_details["building_structure"] = bstruct
    site_area = pick("site_area", "대지면적")
    if _nz(site_area):
        building_details["site_area"] = site_area
    tfa = pick("total_floor_area", "연면적", "연 면 적")
    if _nz(tfa):
        building_details["total_floor_area"] = tfa
    appr = pick("approval_date", "사용승인")
    if _nz(appr):
        building_details["approval_date"] = appr
    park = pick("parking", "주차")
    if _nz(park):
        building_details["parking"] = park
    tunits = pick("total_units", "총세대", "총 세대")
    if _nz(tunits):
        building_details["total_units"] = tunits
    tpeople = pick("total_people", "총주거인원", "총 주거인원")
    if _nz(tpeople):
        building_details["total_people"] = tpeople
    trooms = pick("total_rooms", "총실", "총 실")
    if _nz(trooms):
        building_details["total_rooms"] = trooms
    
    # address를 building_details에 추가
    addr = pick("address", "주소")
    if _nz(addr):
        building_details["address"] = addr
    
    # additional_info에서 building_details 정보 추출
    if "additional_info" in platform_fields:
        additional_info = platform_fields["additional_info"]
        if isinstance(additional_info, dict):
            # 주소 (additional_info의 주소가 더 정확할 수 있음)
            additional_addr = additional_info.get("주소")
            if _nz(additional_addr):
                building_details["address"] = additional_addr
    
    if building_details:
        result["building_details"] = building_details

    # 5) cohouse_text_extracted_info
    cohouse_info = {}
    hform = pick("building_type", "주거형태", "주택구조")
    if _nz(hform):
        cohouse_info["building_type"] = hform
    htype = pick("unit_type", "세대형태", "세대유형", "집구조", "세대형")
    if _nz(htype):
        cohouse_info["unit_type"] = htype
    if _nz(elig):
        cohouse_info["target_occupancy"] = elig
    
    # platform_fields에서 cohouse_text_extracted_info 가져오기
    if "cohouse_text_extracted_info" in platform_fields:
        existing_cohouse_info = platform_fields["cohouse_text_extracted_info"]
        if isinstance(existing_cohouse_info, dict):
            cohouse_info.update(existing_cohouse_info)

    # 텍스트에서 패턴 추출
    extracted_patterns = {}
    if cleaned_text:
        text = re.sub(r"<[^>]+>", " ", cleaned_text)
        text = re.sub(r"\s+", " ", text).strip()

        areas = re.findall(r"(\d+(?:\.\d+)?)\s*(?:㎡|m²|m2)", text)
        if areas:
            seen = set(); a_out = []
            for a in areas:
                if a not in seen:
                    seen.add(a); a_out.append(a)
            extracted_patterns["areas"] = a_out

        prices = []
        for m in re.finditer(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{2,})\s*원", text):
            prices.append(m.group(1))
        if prices:
            prices = [p for p in prices if not re.fullmatch(r"0+", p)]
            seen = set(); p_out = []
            for p in prices:
                if p not in seen:
                    seen.add(p); p_out.append(p)
            if p_out:
                extracted_patterns["prices"] = p_out

        dates = []
        for m in re.finditer(r"(\d{4}[.\-\/]\d{1,2}[.\-\/]\d{1,2})", text):
            dates.append(m.group(1))
        if dates:
            seen = set(); d_out = []
            for d in dates:
                if d not in seen:
                    seen.add(d); d_out.append(d)
            extracted_patterns["dates"] = d_out

    if extracted_patterns:
        cohouse_info["extracted_patterns"] = extracted_patterns

    if cohouse_info:
        result["cohouse_text_extracted_info"] = cohouse_info

    # 6) eligibility_raw
    elig_raw = pick("eligibility", "eligibility_raw")
    if _nz(elig_raw):
        result["eligibility_raw"] = elig_raw

    result["_meta"] = {
        "source": "cohouse",
        "schema": "v1",
        "fetched_at": datetime.now().isoformat(),
    }
    return result
