#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Pagination utilities

import json
import re
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

from .base import Progress, robust_goto

def _with_page_index(url: str, page_idx: int) -> str:
    """Return URL with pageIndex=<page_idx> added or replaced."""
    u = urlparse(url)
    qs = dict(parse_qsl(u.query, keep_blank_values=True))
    qs["pageIndex"] = str(page_idx)
    new_q = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))

def _has_js_function(page, name: str) -> bool:
    try:
        return bool(page.evaluate(f"typeof {name} === 'function'"))
    except Exception:
        return False

def crawl_list_detail_blocks_paginated(
    page,
    list_url: str,
    row_selector: str,
    link_selector: str,
    progress: Progress,
    max_pages: int = 0,
    start_page: int = 1,
) -> list[tuple[str, dict]]:
    """Robust paginator for collecting detail descriptors."""
    details: list[tuple[str, dict]] = []
    seen: set[str] = set()

    # 페이지네이션 최대 횟수 (0 → 합리적 상한)
    max_attempts = max_pages if (max_pages and max_pages > 0) else 50
    page_idx = start_page

    while page_idx <= max_attempts:
        # --- 페이지 전환 ---
        try:
            if "soco.seoul.go.kr/youth" in list_url:
                # 청년주택: 쿼리 파라미터로 페이징
                page_url = _with_page_index(list_url, page_idx)
                page.goto(page_url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=10000)
                progress.update(f"[NAV] Page {page_idx}")
            else:
                # 공동체/사회주택: cohomeList 가 있으면 사용, 없으면 URL 폴백
                if _has_js_function(page, "cohomeList"):
                    page.evaluate(f"cohomeList({page_idx})")
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=10000)  # 네트워크 안정화 대기
                    page.wait_for_timeout(1500)  # 추가 대기 시간
                    progress.update(f"[NAV] Page {page_idx}")
                else:
                    # JS 함수 미로딩/미존재 → URL 페이징
                    page_url = _with_page_index(list_url, page_idx)
                    page.goto(page_url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    progress.update(f"[NAV] Page {page_idx}")
        except Exception as e:
            progress.update(f"[NAV] Error on page {page_idx}: {e}")
            break

        # --- 로우 존재 확인 ---
        try:
            page.wait_for_selector(row_selector, timeout=10000)
            # 테이블이 완전히 로드될 때까지 추가 대기
            page.wait_for_timeout(500)
        except Exception:
            # 첫 페이지에서 선택자 안 보이면 다른 후보 셀렉터로 시도하도록 호출부에 맡김
            break

        rows = page.locator(row_selector)
        nrows = rows.count()
        
        # 테이블이 비어있으면 잠시 더 기다림
        if nrows == 0:
            page.wait_for_timeout(1000)
            nrows = rows.count()
        added_here = 0

        for i in range(nrows):
            a = rows.nth(i).locator(link_selector)
            if not a.count():
                continue

            href = (a.first.get_attribute("href") or "").strip()
            title = (a.first.inner_text() or "").strip()
            if not href:
                continue

            # 리스트 컬럼에서 힌트 보강
            subway_station = ""
            unit_type = ""
            theme = ""
            try:
                tds = rows.nth(i).locator("td")
                c = tds.count()
                if "soco.seoul.go.kr/coHouse" in list_url:
                    if c > 4: unit_type = (tds.nth(4).inner_text() or "").strip()
                    if c > 5: theme = (tds.nth(5).inner_text() or "").strip()
                    if c > 6: subway_station = (tds.nth(6).inner_text() or "").strip()
                elif "soco.seoul.go.kr/soHouse" in list_url:
                    if c > 4: unit_type = (tds.nth(4).inner_text() or "").strip()
                    if c > 5: subway_station = (tds.nth(5).inner_text() or "").strip()
                elif "soco.seoul.go.kr/youth" in list_url:
                    if c > 4: subway_station = (tds.nth(4).inner_text() or "").strip()
            except Exception:
                pass

            # href 해석
            if href.startswith("javascript:"):
                m = re.search(r"javascript:(\w+)\(([^)]*)\)", href)
                if not m:
                    continue
                fn, arg_str = m.group(1), m.group(2).strip()

                if "soco.seoul.go.kr/coHouse" in list_url and fn == "modify":
                    # coHouse: uses homeCode parameter
                    board_id = arg_str
                    url = ("https://soco.seoul.go.kr/coHouse/pgm/home/cohome/view.do"
                           "?menuNo=200043&homeCode={}&searchKeyword=&pageNum=1&presale=&theme=&movinHoman=&houseType=&houseForm=&adresGu=").format(board_id)
                    desc = {"kind": "get", "url": url, "subway_station": subway_station, "unit_type": unit_type, "theme": theme}
                elif "soco.seoul.go.kr/soHouse" in list_url and fn == "modify":
                    # soHouse: uses homeCode parameter (not boardId)
                    board_id = arg_str
                    url = f"https://soco.seoul.go.kr/soHouse/pgm/home/sohome/view.do?menuNo=300006&homeCode={board_id}"
                    desc = {"kind": "get", "url": url, "subway_station": subway_station, "unit_type": unit_type, "theme": theme}
                elif "soco.seoul.go.kr/youth" in list_url and fn == "modify":
                    # youth: uses boardId parameter - 모집공고 섹션 사용
                    board_id = arg_str
                    if "BMSR00015/list.do" in list_url:
                        url = f"https://soco.seoul.go.kr/youth/bbs/BMSR00015/view.do?boardId={board_id}&menuNo=400008&pageIndex=1&searchCondition=&searchKeyword="
                    elif "yohome/list.do" in list_url:
                        url = f"https://soco.seoul.go.kr/youth/pgm/home/yohome/view.do?boardId={board_id}&menuNo=400002"
                    else:
                        url = f"https://soco.seoul.go.kr/youth/bbs/BMSR00015/view.do?boardId={board_id}&menuNo=400008"
                    desc = {"kind": "get", "url": url, "subway_station": subway_station}
                else:
                    desc = {"kind": "js_function", "name": fn, "args": [arg_str], "subway_station": subway_station, "unit_type": unit_type, "theme": theme}
            else:
                desc = {"kind": "get", "url": urljoin(list_url, href), "subway_station": subway_station}

            key = json.dumps(desc, ensure_ascii=False, sort_keys=True) + "|" + (title or "")
            if key in seen:
                continue
            seen.add(key)
            details.append((title, desc))
            added_here += 1

        # 종료 조건
        if nrows == 0:
            progress.update(f"[NAV] No rows on page {page_idx}, stopping")
            break
        # 충분히 탐색했고 신규 추가가 없으면 종료
        min_pages = 10 if "soco.seoul.go.kr/youth" in list_url else 5
        if added_here == 0 and page_idx >= min_pages:
            progress.update(f"[NAV] No new items on page {page_idx}, stopping")
            break

        page_idx += 1

    progress.update(f"[NAV] Collected {len(details)} items from {page_idx-1} page(s)")
    return details

def collect_details_with_fallbacks(
    page,
    list_url: str,
    progress: Progress,
    max_pages: int = 0,
    *,
    assume_on_list: bool = False,
    log_nav: bool = True,
) -> list[tuple[str, dict]]:
    """Try multiple (row, link) selector pairs until one yields details.

    여기서 단 한 번만 LIST 네비게이션을 수행해 로그 중복을 방지한다.
    """
    # 리스트 페이지 진입 (한 번만)
    robust_goto(page, list_url, progress, label="LIST")

    # 일부 페이지는 '검색' 버튼을 눌러야 테이블이 나타남
    if any(k in list_url for k in ("coHouse", "cohouse", "soHouse", "sohouse", "youth")):
        try:
            btn = page.locator('input[type="submit"], button[type="submit"], input[value*="검색"], button:has-text("검색")')
            if btn.count():
                btn.first.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                page.wait_for_timeout(500)
                progress.update("[SEARCH] 검색 완료")
        except Exception:
            pass

    # 후보 선택자
    if "soco.seoul.go.kr" in list_url:
        candidates: list[tuple[str, str]] = [
            ("tbody#cohomeForm tr", "td a[href^='javascript:modify'], td a[href]"),  # 공동체주택
            ("tbody#boardList tr", "td a[href^='javascript:'], td a[href]"),        # 사회/청년
            (".tbl_list tbody tr", "td a[href^='javascript:'], td a[href]"),
            ("table.boardTable tbody tr", "td a[href^='javascript:'], td a[href]"),
        ]
    else:
        candidates = [
            ("table.boardTable tbody tr", "a.no-scr, td a[href^='javascript:modify']"),
            (".tbl_list tbody tr", "td a[href^='javascript:modify'], td a.no-scr, td a[href]"),
            ("tbody#boardList tr", "td a[href^='javascript:modify'], td a[href]"),
        ]

    for row_sel, link_sel in candidates:
        try:
            res = crawl_list_detail_blocks_paginated(
                page=page,
                list_url=list_url,
                row_selector=row_sel,
                link_selector=link_sel,
                progress=progress,
                max_pages=max_pages,
            ) or []
            if res:
                return res
        except Exception:
            continue

    return []
