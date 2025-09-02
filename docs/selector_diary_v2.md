# Selector Diary — v2 (Detailed)

_Last updated: 2025-08-25 KST_

> 목적: **구현 즉시 사용** 가능한 수준으로 선택자·행동·API·저장 규칙을 문서화.

## 업데이트 핵심 요약(반영 완료)

- **SH 탭**: 현재 선택(`a.current_selected > span:has-text("행복주택")`). 전환 필요 시 `li.snb_depth3:has(span:has-text("행복주택")) a:not(.current_selected)`.
- **youth 공고 페이징**: `onclick="cohomeList(n)"` → `page.evaluate("cohomeList(n)")` + `networkidle`.
- **LH 상세**: `POST …/selectWrtancInfo.do` (폼: `panId`, `ccrCnntSysDsCd`, `uppAisTpCd`, `aisTpCd`, `mi`, `currPage`, `panSs=공고중`, `startDt`, `endDt`, `listCo=50` 등). 응답 HTML 루트 `div.bbs_ViewA`. 첨부는 `fileDownLoad('ID')`.

---

## 공통 규칙

- **저장 경로**: `data/raw/YYYY-MM-DD/{html,attachments}`
- **메타 파일**: `manifest.csv`(상세) / `attachments.csv`(첨부)
- **파일명**: HTML→`{sha256(url)}.html`, 첨부→`{file_hash}_{originalName}.ext`
- **대기 전략**: 목록 `tbody` 등장 + `wait_for_load_state("networkidle")`
- **정규화**: 날짜 `20\d{2}[.\-/년 ]\s*\d{1,2}[.\-/월 ]\s*\d{1,2}` → `YYYY-MM-DD`

---

## A) 사회주택 — 주택찾기 (soHouse)

- **목록**: `https://soco.seoul.go.kr/soHouse/pgm/home/sohome/list.do?menuNo=300006`
- **선택자**
  - 목록: `table.boardTable` / `tbody#cohomeForm`
  - 상세: `a.no-scr[href^="javascript:modify("]`
  - 페이징: `button[onclick^="cohomeList("]`
- **필드 매핑**: 지역(3) | 주택명(4) | 유형(5) | 교통(6) | 금액(7) | 공실(8)
- **요령**
  ```python
  page.evaluate("cohomeList(2)")
  page.wait_for_load_state("networkidle")
  ```

---

## B) 공동체주택 — 주택찾기 (coHouse)

- **목록**: `https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043`
- **선택자/동작**: A와 동일 (`modify`, `cohomeList`)
- **필드(열)**: 지역(3) / 주택명(4) / 유형(5) / **테마(6)** / 교통(7) / 금액(8)
- **주의**: `전세 원` 등 비정상 금액은 결측 허용 + 원문 저장

---

## C) 청년안심주택 (youth)

### 1) 주택찾기 (삭제)

- **목록**: `https://soco.seoul.go.kr/youth/pgm/home/yohome/list.do?menuNo=400002` / `tbody#cohomeForm`
- **상세/페이징**: `modify` / `cohomeList`
- **필드**: 지역 / 주택명 / 전철역 / 공실

### 2) 모집공고（업데이트 반영）

- **목록**: `https://soco.seoul.go.kr/youth/bbs/BMSR00015/list.do?menuNo=400008`
- **컨테이너**: `tbody#boardList`
- **상세 링크**: `td.align_left a[href*="view.do?boardId="]`
- **페이징**: **버튼형 JS** → `onclick="cohomeList(n)"`
  ```python
  page.evaluate(f"cohomeList({n})")
  page.wait_for_load_state("networkidle")
  ```
- **종료 조건**: 첫 행 제목 반복 / ‘다음’ 미표시 / 행 0건

### 3) 공급현황(예정 포함)

- **URL**: `https://soco.seoul.go.kr/youth/main/contents.do?menuNo=400014`
- **표**: `table.status_apply_table.mt20` (`tr.show_20xx`)
- **정규화**: `2025.07.30.` → `2025-07-30`

---

## D) 행복주택 (haHouse)

### 1) SH 공급계획 탭

- **URL**: `https://www.i-sh.co.kr/main/lay2/S1T243C1043/contents.do#`
- **현재 상태**: `a.current_selected > span:has-text("행복주택")` (선택됨)
- **전환 셀렉터**: `li.snb_depth3:has(span:has-text("행복주택")) a:not(.current_selected)`
- **대기**: 전환 뒤 `wait_for_selector("table")`

### 2) LH 공고문 (목록→상세→첨부)

- **목록**: `https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026` → 상세 링크 `a.wrtancInfoBtn`
- **상세 API**（확정）
  - `POST /lhapply/apply/wt/wrtanc/selectWrtancInfo.do`
  - **Form Data(예)**: `panId, ccrCnntSysDsCd, srchUppAisTpCd, uppAisTpCd, aisTpCd, mi, currPage, panSs, startDt, endDt, listCo`
  - **응답**: `text/html` / 루트 `div.bbs_ViewA`
- **필드**: 제목 `div.bbs_ViewA > h3` / 정보 `ul.bbsV_data li`
- **첨부**
  - 다운로드: `a[href^="javascript:fileDownLoad"]` → `expect_download()`
  - 뷰어: `a.btn_grL.preview`(토큰) → 기록만

---

## E) 서울시 주택건축소식 (news)

- **목록**: `https://news.seoul.go.kr/citybuild/archives/category/build-news_c1/build_news-news-n1`
- **상세**: `article a[href*="/citybuild/archives/"]` / 제목 `h1.entry-title` / 날짜 `.entry-meta time` / 본문 `.entry-content`
- **페이징**: `a[rel="next"]`/“다음”

---

## 스모크 테스트(DoD)

- [ ] 목록 1페이지에서 상세 3–5건 저장
- [ ] 제목·게시/공고일 파싱 성공
- [ ] 첨부 1–2건 다운로드 성공
- [ ] JS 페이징/탭 전환 시 `networkidle` 대기 적용
- [ ] `manifest.csv` / `attachments.csv` 레코드 추가
