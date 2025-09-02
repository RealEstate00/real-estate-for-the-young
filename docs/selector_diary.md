# Selector Diary — Seoul Housing Assist (선택자 다이어리)

_Last updated: 2025-08-25 09:44 KST_

> 목적: 각 사이트의 **목록/상세/첨부** 선택자와 동작 특성을 한 곳에 기록해, 크롤러 수정·유지보수를 빠르게 한다.

---

## 공통 워크플로우

1. **목록 1페이지 고정 검사**

## 부록 — 금액/숫자 정규화 팁

- **초기 버전(간단)**: `(\d[\d,]*)\s*만원` → 정수(원)로 환산(×10,000), `(\d[\d,]*)\s*원`도 추출
- **개선 버전(한글 숫자)**: `천/백/십` 포함 케이스는 **보족숫자**(예: `1천5백0` → 1,500)로 변환하는 헬퍼를 별도 구현
  - 실패 시 **원문도 같이 저장**해 디버깅/후처리 가능하게

---

## 공통 규칙 & 정규식

- **날짜 패턴(일반)**: `20\d{2}[.\-/년 ]\s*\d{1,2}[.\-/월 ]\s*\d{1,2}`
- **금액 패턴**: `(\d[\d,]*)\s*(만원|원)` → 원 단위로 환산
- **면적 패턴**: `(\d+(?:\.\d+)?)\s*(㎡|m2|제곱미터|평)` → ㎡로 통일(평×3.3058)
- **첨부 식별**: 링크 텍스트/`href`에 `download|attach|file|.pdf|.hwp|.doc|.docx|.xls|.xlsx|.zip` 포함

---

## A) 사회주택 — 주택찾기 (soHouse)

- **목록 URL**: `https://soco.seoul.go.kr/soHouse/pgm/home/sohome/list.do?menuNo=300006`
- **목록 컨테이너**
  - `table.boardTable`
  - `tbody#cohomeForm`
- **행 예시**: 번호 | 사진 | 지역 | 주택명 | 주택유형 | 교통 | 금액 | 공실여부
- **상세 진입(링크)**
  - `<a class="no-scr" href="javascript:modify(20000569);">…</a>`
  - **선택자**: `a.no-scr[href^="javascript:modify("]`
  - **요령**: JS 함수로 이동하므로 **클릭 그대로 수행** or `page.evaluate("modify(20000569)")`
- **페이지네이션**
  - `button[onclick^="cohomeList("]` 例) `onclick="cohomeList(2)"`
  - **요령**: `page.evaluate("cohomeList(2)")` → 로딩 대기: `wait_for_load_state("networkidle")`
- **필드 매핑(정제)**
  - 지역 → `td:nth-child(3)`
  - 주택명 → `td:nth-child(4) a.no-scr`
  - 주택유형 → `td:nth-child(5)`
  - 교통 → `td:nth-child(6)`
  - 금액 → `td:nth-child(7)` (예: `보증금 1천5백0만원<br>월세 35만원`)
    - **정규화**: 보증금/월세 분리, ‘천/백/십’ 한글 숫자 처리(초기엔 숫자만 추출 후 개선)
  - 공실여부 → `td:last-child`
  - 썸네일(선택) → `td:nth-child(2) img[src*="fileDown.do"]` (루트 붙여 저장)
- **대기 조건**
  - 목록: `await page.wait_for_selector("tbody#cohomeForm tr")`
  - 상세: 클릭 후 본문 컨테이너 등장까지 대기(상세 구조 파악 필요)
- **체크박스**
  - [ ] 상세 3–5건 이동 OK
  - [ ] 보증금/월세 파싱 OK
  - [ ] 2→3페이지 이동 OK (`cohomeList(n)`)

---

## B) 공동체주택 — 주택찾기 (coHouse)

- **목록 URL**: `https://soco.seoul.go.kr/coHouse/pgm/home/cohome/list.do?menuNo=200043`
- **목록 컨테이너**
  - `table.boardTable`
  - `tbody#cohomeForm`
- **행 예시**: 번호 | 사진 | 지역 | 주택명 | 주택유형 | 테마 | 교통 | 금액
- **상세 진입**
  - `<a class="no-scr" href="javascript:modify(20000570);">…</a>`
  - **선택자**: `a.no-scr[href^="javascript:modify("]`
- **페이지네이션**
  - `button[onclick^="cohomeList("]`
- **필드 매핑(정제)**
  - 지역(3) / 주택명(4) / 주택유형(5) / **테마(6)** / 교통(7) / 금액(8)
  - 금액 표기가 `전세 원`처럼 불완전할 수 있음 → **결측 허용 + 비정상 값 로그**
- **체크박스**
  - [ ] 상세 이동 OK
  - [ ] 테마/교통 파싱 OK
  - [ ] 페이징 OK

---

## C) 청년안심주택 (youth)

### 1) 주택찾기

- **목록 URL**: `https://soco.seoul.go.kr/youth/pgm/home/yohome/list.do?menuNo=400002`
- **목록 컨테이너**
  - `table.boardTable`
  - `tbody#cohomeForm`
- **행 예시**: 번호 | 사진 | 지역 | 주택명 | 전철역 | 공실여부
- **상세 진입**
  - `<a href="javascript:modify(20000373);">…</a>` → `a[href^="javascript:modify("]`
- **페이지네이션**
  - `button[onclick^="cohomeList("]`
- **필드 매핑(정제)**
  - 지역(3) / 주택명(4) / 전철역(5) / 공실여부(6)
  - **가격 없음** → 후속(모집공고·상세) 데이터와 조합 고려
- **체크박스**
  - [ ] 상세 이동 OK
  - [ ] 전철역/공실여부 파싱 OK
  - [ ] 페이징 OK

### 2) 모집공고

- **목록 URL**: `https://soco.seoul.go.kr/youth/bbs/BMSR00015/list.do?menuNo=400008`
- **목록 컨테이너**
  - `table.boardTable`
  - `tbody#boardList`
- **행 예시**: 번호 | 구분 | 공고명 | 공고게시일 | 등록일 | 담당부서/사업자
  - 상세 링크: `td.align_left a[href*="view.do?boardId="]`
- **페이지네이션**
  - (표기상 cohomeList 사용) 실제는 `pageIndex` 파라미터일 수도 → **Network 탭으로 확인**
- **필드 매핑(정제)**
  - 공고명/링크, 공고게시일(YYYY-MM-DD), 등록일, 구분(민간/추가 등)
- **체크박스**
  - [ ] 목록→상세 5건 OK
  - [ ] 공고게시일 파싱 OK
  - [ ] 페이징 OK

### 3) 공급현황 및 계획

- **URL**: `https://soco.seoul.go.kr/youth/main/contents.do?menuNo=400014`
- **표 컨테이너**: `table.status_apply_table.mt20`
- **행 예시**(연도별 클래스): `<tr class="bg-purple2 cell_show_wrap_24 show_2025">…`
- **필드**: 공급년도 | 단지명 | 주소 | 지하철역 | 모집공고(공공) | 모집공고(민간) | 총실수 | 공공임대 | 민간임대 | 문의전화(공공/민간)
- **요령**
  - `tr[class*="show_20"]`로 연도 필터
  - 날짜 표기 `2025.07.30.` → `YYYY-MM-DD`로 정규화
- **체크박스**
  - [ ] 연도별 파싱 OK
  - [ ] 수치(총실수 등) 숫자화 OK

### 4) 금융지원(정보 페이지)

- **URL**: `https://soco.seoul.go.kr/youth/main/contents.do?menuNo=400021`
- **컨테이너**: `article.subLayout.support-intro.cont2`
- **포인트**: 목록형 정보(대출한도/지원금리), 외부 링크 존재
- **요령**: **콘텐츠 스냅만 저장**(정형표 아님) → 텍스트 추출해 참고 테이블로 유지

---

## D) 행복주택 (haHouse)

### 1) SH공사 — 공급계획

- **URL**: `https://www.i-sh.co.kr/main/lay2/S1T243C1043/contents.do#`
- **유형 토글**: 상단 탭(장기전세/국민임대/**행복주택**/…)
  - **선택자**: `a:has-text("행복주택")` 클릭 → 해당 표 로드 대기
- **표 구조**: 단지명 | 계 | 전용면적별 공급예정물량 | 소재지 | 공급예정월 | 유형 …
  - 각 `td`에 `data-fshasflag` 등 속성 존재(텍스트 추출에는 영향 없음)
- **요령**
  - 탭 클릭 후 `wait_for_selector("table")`
  - 공급예정월 `7~8` 같은 **범위 값** 처리(두 값으로 분해 or 중간값 가정)
- **체크박스**
  - [ ] 행복주택 탭 전환 OK
  - [ ] 표 파싱 OK(단지명/소재지/예정월/유형)

### 2) LH 청약플러스 — 공고문

- **목록 URL**: `https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026`
- **페이지네이션**: `<a href="javascript:" onclick="goPaging(2)" class="bbs_pge_num">…`
  - **요령**: `page.evaluate("goPaging(2)")` → `wait_for_load_state("networkidle")`
- **행 예시**: 번호 | 유형 | 공고명 | 지역 | **첨부** | 게시일 | 마감일 | 상태 | 조회수
  - 상세 링크: `a.wrtancInfoBtn` (데이터 속성: `data-id1..id5`)
  - 첨부 다운로드: `a.listFileDown.tbl_web2[data-id1..id5]`
- **상세 진입**
  - 모달/프레임/XHR 호출일 수 있음 → **클릭 후 Network 캡쳐**로 상세 API/URL 확인
- **필드 매핑(정제)**
  - 유형(행복주택), 공고명, 지역, 게시일 `YYYY.MM.DD`, 마감일 `YYYY.MM.DD`, 상태(공고중), 첨부 존재 여부
- **체크박스**
  - [ ] `goPaging(n)` 동작 OK
  - [ ] `wrtancInfoBtn` 클릭 후 상세 데이터 확보 OK
  - [ ] `listFileDown`로 첨부 1–2건 다운로드 OK

---

## E) 서울시 주택건축소식 (news)

- **목적**: 공지/보도자료 기사형 콘텐츠 수집
- **목록 URL(예상 패턴)**: `https://news.seoul.go.kr/citybuild/archives/category/build-news_c1/build_news-news-n1`
- **상세 URL(예상 패턴)**: `https://news.seoul.go.kr/citybuild/archives/\d+`

### 목록

- **상세 링크(CSS)**: `article a[href*="/citybuild/archives/"]` 또는 카드 내 첫 a
- **페이지네이션**: `a[rel="next"]`, `a:has-text("다음")`

### 상세

- **제목**: `h1.entry-title`, `h1`, `.title`
- **게시일**: `.entry-meta time`, `time[datetime]`
- **본문**: `.entry-content`, `.content`, `.post-content`
- **첨부**: 본문 내 링크 중 파일 확장자(.pdf 등) 필터링

### 스모크 테스트

- [ ] 목록에서 최근 기사 5건 수집
- [ ] 상세 3건 저장/제목·게시일 파싱
- [ ] 본문 내 파일 링크 존재 시 1건 저장

---

## 공통 Edge Cases & 운영 메모

- **동적 로딩**: 목록이 JS로 로드될 때 `wait_for_selector("table tbody")` 또는 카드 컨테이너 대기
- **세션/리퍼러 요구**: 첨부가 POST/세션 의존일 수 있으니 브라우저 컨텍스트를 동일하게 유지
- **중복 제거**: `sha256(url)` → `url_hash`로 관리
- **파일명 정책**: `{file_hash}_{originalName}.ext`
- **에러/재시도**: 60s 타임아웃, 3회 지수백오프(1s→2s→4s)

---

## 확인 로그 포맷(예시, JSONL)

```json
{"ts":"2025-08-25T10:00:00+09:00","site":"soHouse","step":"list","url":".../list.do","count":20,"elapsed_ms":420}
{"ts":"2025-08-25T10:00:02+09:00","site":"soHouse","step":"detail","url":".../view.do?id=...","status":200,"elapsed_ms":380}
{"ts":"2025-08-25T10:00:03+09:00","site":"soHouse","step":"attach","url":".../download?id=...","saved":".../attachments/<hash>_파일명.hwp","bytes":123456}
```

---

## 미확정/검증 필요 항목 To-Do

- [ ] 실제 DOM 기준으로 **제목/날짜/본문/첨부**의 **최종 선택자** 고정
- [ ] 페이징 버튼 텍스트/aria-label 확인(“다음/이전” 변형 여부)
- [ ] 뉴스 페이지의 **카테고리 변형** 여부(서브 카테고리 존재 시 링크 확장)

---

## 부록 — sites.yml 스니펫 (동기화용)

```yaml
sites:
  soco_sohouse:
    platform: "사회주택"
    list_url: "https://soco.seoul.go.kr/soHouse/bbs/BMSR00010/list.do?menuNo=300017"
    detail_selector: 'table tbody a[href*="/soHouse/bbs/"][href*="/view.do"]'
    next_selector: 'a:has-text("다음")'
    attach_hint: "첨부파일"

  soco_cohouse:
    platform: "공동체주택"
    list_url: "https://soco.seoul.go.kr/coHouse/bbs/BMSR00010/list.do?menuNo=300012"
    detail_selector: 'table tbody a[href*="/coHouse/bbs/"][href*="/view.do"]'
    next_selector: 'a:has-text("다음")'
    attach_hint: "첨부파일"

  soco_youth:
    platform: "청년안심주택"
    list_url: "https://soco.seoul.go.kr/youth/bbs/BMSR00015/list.do?menuNo=300033"
    detail_selector: 'table tbody a[href*="/youth/bbs/"][href*="/view.do"]'
    next_selector: 'a:has-text("다음")'
    attach_hint: "첨부파일"

  seoul_news:
    platform: "서울시뉴스"
    list_url: "https://news.seoul.go.kr/citybuild/archives/category/build-news_c1/build_news-news-n1"
    detail_selector: 'article a[href*="/citybuild/archives/"]'
    next_selector: 'a[rel="next"], a:has-text("다음")'
    attach_hint: "첨부"
```
