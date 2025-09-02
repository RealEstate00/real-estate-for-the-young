# Selector Diary — v1 (Clean)

_Last updated: 2025-08-25 KST_

> 목적: 각 사이트의 **목록/상세/첨부/페이징** 동작을 한눈에 정리해 크롤러 개발·운영을 빠르게 한다.

## 🔔 업데이트 핵심 요약

- **SH 공급계획 탭**: DOM에 `a.current_selected > span:has-text("행복주택")` → 이미 선택(클릭 불필요). 미선택 전환: `li.snb_depth3:has(span:has-text("행복주택")) a:not(.current_selected)`.
- **청년안심주택(모집공고) 페이징**: 버튼형 JS → `onclick="cohomeList(n)"` (evaluate로 호출 + networkidle 대기).
- **LH 상세 진입(API)**: `POST /lhapply/apply/wt/wrtanc/selectWrtancInfo.do` (form-urlencoded). 응답은 **HTML**, 루트 `div.bbs_ViewA`. 첨부는 `javascript:fileDownLoad('ID')`.

---

## A) 사회주택 — 주택찾기 (soHouse)

- **목록**: https://soco.seoul.go.kr/soHouse/pgm/home/sohome/list.do?menuNo=300006
- **컨테이너**: `table.boardTable` / `tbody#cohomeForm`
- **상세 링크**: `a.no-scr[href^="javascript:modify("]`
- **페이징**: `button[onclick^="cohomeList("]`
- **필드(열)**: 지역(3) / 주택명(4) / 유형(5) / 교통(6) / 금액(7) / 공실(8)

## B) 공동체주택 — 주택찾기 (coHouse)

- **목록**: https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043
- **컨테이너/상세/페이징**: A와 동일 패턴 (`modify` / `cohomeList`)
- **필드(열)**: 지역(3) / 주택명(4) / 유형(5) / **테마(6)** / 교통(7) / 금액(8)

## C) 청년안심주택 (youth)

- **주택찾기**: `…/yohome/list.do?menuNo=400002` / `tbody#cohomeForm` / `modify` / `cohomeList`
- **모집공고**: `…/bbs/BMSR00015/list.do?menuNo=400008` / `tbody#boardList` / **페이징: `cohomeList(n)`**
  - 상세 링크: `td.align_left a[href*="view.do?boardId="]`
- **공급현황**: `…/contents.do?menuNo=400014` / `table.status_apply_table.mt20`

## D) 행복주택 (haHouse)

- **SH 공급계획**: https://www.i-sh.co.kr/main/lay2/S1T243C1043/contents.do#
  - **탭 전환**: (기본) 이미 선택. 전환 시 `li.snb_depth3:has(span:has-text("행복주택")) a:not(.current_selected)`
- **LH 공고문(목록→상세)**: https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026
  - 상세 **API**: `POST /lhapply/apply/wt/wrtanc/selectWrtancInfo.do` (form)
  - 상세 **루트**: `div.bbs_ViewA` / 제목 `h3` / 정보 `ul.bbsV_data li`
  - **첨부 다운로드**: `a[href^="javascript:fileDownLoad"]` (다운로드), `a.btn_grL.preview`(뷰어)

## E) 서울시 주택건축소식 (news)

- **목록**: `/citybuild/archives/category/build-news_c1/build_news-news-n1`
- **상세 링크**: `article a[href*="/citybuild/archives/"]`
- **페이징**: `a[rel="next"]` 또는 “다음”

---

## 공통 대기/스모크

- **대기**: `wait_for_selector(목록 tbody)` + `wait_for_load_state("networkidle")`
- **스모크 테스트**: (i) 목록 5건 추출 (ii) 상세 3건 저장 (iii) 첨부 1건 저장
