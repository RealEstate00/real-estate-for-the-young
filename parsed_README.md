# PARSED 작업자용 README

이 문서는** \*\***RAW 수집단계에서 저장된 것**과** \***\*PARSED 단계에서 해야 할 일**을 한눈에 정리한 안내서입니다.
목표는 “크롤링은 넓고 안전하게, 정제·중복제거·스키마화는 PARSED에서” 입니다.

---

## 1) RAW 단계에서 저장하는 것 (현 상태)

### 공통

- 출력 루트:\*\* \*\*`data/raw/<YYYY-MM-DD>/<소스코드>/`
- 레코드 요약 CSV: 각 소스 폴더의\*\* \*\*`raw.csv`
  컬럼:
  <pre class="overflow-visible!" data-start="267" data-end="452"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>record_id, platform, platform_id, crawl_date, house_name, </span><span>address</span><span>, platform_intro,
  list_url, detail_url, detail_descriptor, image_paths, html_path, extras_json, crawled_at
  </span></span></code></div></div></pre>
- 원본 HTML:\*\* **`html/<rid>.html` (또는 LH 상세의 경우** \*\*`<rid>_detail.html`)
- 이미지:\*\* \*\*`images/<rid>/...`
- 첨부파일(문서/압축):\*\* **`attachments/<rid>/...`
  (허용 확장자:** \*\*`.pdf .hwp .hwpx .doc .docx .xls .xlsx .ppt .pptx .zip`)
- (있을 때) 첫 번째 표를 CSV로 추출:\*_ \*\*`tables/<rid>\__.csv`
- `extras_json`에 소스별 힌트 저장(예: 첨부 경로, POST 폼, 원시 날짜/금액 등)

### 소스별 수집 범위

- **sohouse / cohouse**
  - 상세 HTML, 이미지, 첨부, (있으면) 입주현황 표 CSV
  - 목록 페이징 자동 탐색(쿼리 파라미터\*\* \*\*`pageIndex` + “다음” 버튼 폴백 지원)
- **youth_unified**
  - `youth_home`(주택찾기): 상세 HTML, 이미지, 첨부
  - `youth_bbs`(모집공고): 상세 HTML, 이미지, 첨부
  - `--max-youth-bbs`로 BBS 상세 수집 개수 제한 가능(기본 0=전체)
- **lh_ann** (LH 공고 목록)
  - 목록 HTML(세션 기준),** \*\***상세 POST 응답 HTML\*\* 저장(`<rid>_detail.html`)
  - 첨부파일 저장(POST 상세 본문에서 링크 스캔)
  - `extras_json`에\*\* **`detail_html_path`,** \*\*`attachments_paths`, 원시 날짜·마감일, 외부 ID 힌트 등 포함
- **sh_plan_happy** (SH 공급계획의 “행복주택” 탭)
  - 표 데이터를\*\* \*\*`raw.csv`에 적재(상세 첨부 없음)
- **platform_info** ,** \*\***seoul_portal_happy_intro\*\*
- 소개/정책/자격 페이지의 원본 HTML 및 페이지 레벨 이미지(가볍게)
- **sh_ann** ✅ (추가)
  - **SH 공고 전체** : 모든 페이지를 돌며 상세 HTML, 이미지, 첨부 수집
  - (있을 때) 첫 표 CSV 추출

> **중복 허용 정책**
> LH·SH는 “행복주택”에 한정하지 않고** \*\***현재 노출된 전체 공고**를 수집하도록 확장했습니다.
> 타 플랫폼과 동일 공고가** \***\*중복**될 수 있으며,** \*\***중복 제거는 PARSED 단계에서 처리\*\*합니다.

---

## 2) PARSED 단계에서 해야 할 일

### A. 필드 정규화 & 스키마 추출

- 각\*\* **`html_path`(또는** \*\*`detail_html_path`)를 파싱하여 공통 스키마로 변환:
  - 예시 필드:
    `title, project_name, provider, address_raw, district, deposit, monthly_rent, supply_count, area_m2, application_start, application_end, category, contact, url_source, platform, record_id, crawled_at, attachments_paths …`
- 금액/단위 통일:
  - **보증금/월세** : “만원/천원” 등 표기를** \*\***KRW 정수(원)\*\* 로 통일
  - **면적** : 평→㎡ 변환(1평=3.3058㎡) 후 **㎡**로 보관
- 날짜 통일:
  - `YYYY-MM-DD` ISO 형식. 기간(`~`) 표기는 시작/종료로 분리

### B. 주소 정리 & 좌표(위·경도)

- `address_raw` 정제 → 표준화된\*\* \*\*`addr_std`
- 지오코딩: Kakao/Naver/Google 중 1개 선택,** \*\***캐시\*\*를 두어 중복 호출 방지
- 결과 필드:\*\* \*\*`lat, lng, geocode_status, geocode_source`

### C. 중복 처리(디듀플리케이션) / 레코드 병합

- 가능한 경우** \*\***플랫폼 고유 ID\*\*를 우선 키로 사용
  - LH:\*\* \*\*`detail_descriptor.form.panId` (POST 폼에서 추출)
- 플랫폼 간 중복 탐지:
  - `(정규화된 제목, 정규화된 주소)` + 날짜 근접도 + 첨부/HTML 유사도
- 병합 시** \*\***출처(provenance)\*\* 유지:
  - 병합된 원본\*\* \*\*`record_id` 목록, 원 플랫폼 목록을 함께 보관

### D. 첨부 텍스트 추출

- **PDF** :\*\* **`pdfminer.six`(텍스트), 스캔일 경우** \*\*`ocrmypdf`(Tesseract)로 OCR
- **HWP/HWPX** :
- `hwp5txt` 또는 LibreOffice 변환 → PDF → OCR 폴백
- **DOC/DOCX/XLS/XLSX/PPT/PPTX** :
- DOCX:\*\* **`mammoth` / XLSX:** **`openpyxl` / PPTX:** \*\*`python-pptx`
- 변환 어려우면 LibreOffice headless(`soffice --headless --convert-to …`) 경유
- 첨부 텍스트에서** \*\***날짜/금액/연락처\*\* 같은 힌트를 추가 추출해 HTML 파싱 보완

### E. (선택) 이미지 처리

- 공고 이미지에 간단 OCR 적용(배너형 공고에서 제목·기간 회수)
- 썸네일 생성(목록 UI용)

### F. 최종 산출물

- `data/parsed/<YYYY-MM-DD>/items.parquet` (또는\*\* **`.csv`) —** \***\*정제된 단일 스키마**
- `data/parsed/<YYYY-MM-DD>/attachments_text/` — 첨부 텍스트 결과물
- **검증 리포트** (필드 결측·변환 오류 등)
- **ID 매핑표** : 논리 ID ↔ RAW\*\* \*\*`record_id` 목록(출처 추적)

### G. 품질 점검 지표(권장)

- 필드 커버리지(플랫폼별 채움률)
- 금액/날짜 파서 오류율
- 지오코딩 성공률
- 중복 병합률

---

## 3) 폴더 구조(요약)

<pre class="overflow-visible!" data-start="3350" data-end="4025"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>data/
  raw/
    </span><span>2025</span><span>-</span><span>08</span><span>-</span><span>28</span><span>/
      sohouse/
        </span><span>html</span><span>/, images/, attachments/, tables/, raw</span><span>.csv</span><span>
      cohouse/
      youth_unified/
        </span><span>html</span><span>/, images/, attachments/, raw</span><span>.csv</span><span>
      lh_ann/
        </span><span>html</span><span>/           # 목록/상세(POST 응답) </span><span>HTML</span><span>
        attachments/
        raw</span><span>.csv</span><span>
      sh_plan_happy/
        </span><span>html</span><span>/, raw</span><span>.csv</span><span>
      sh_ann/
        </span><span>html</span><span>/, images/, attachments/, tables/, raw</span><span>.csv</span><span>
      platform_info/
        </span><span>html</span><span>/, images/, raw</span><span>.csv</span><span>
      seoul_portal_happy_intro/
        </span><span>html</span><span>/, images/, raw</span><span>.csv</span><span>
  parsed/
    </span><span>2025</span><span>-</span><span>08</span><span>-</span><span>28</span><span>/
      items</span><span>.parquet</span><span>  # 또는 items</span><span>.csv</span><span>
      attachments_text/
      report</span><span>.json</span><span>     # (선택) 품질/에러 리포트
      id_map</span><span>.csv</span><span>      # (선택) 병합 매핑
</span></span></code></div></div></pre>

---

## 4) 실행 예시(크롤러)

> **초기화 옵션** :\*\* **`--fresh` 는** \***\*오늘 날짜의 해당 소스 폴더를 삭제** 후 재수집합니다.
> **유스 BBS 제한** :\*\* \*\*`--max-youth-bbs N` (기본 0=전체)

<pre class="overflow-visible!" data-start="4160" data-end="4792"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span># 사회주택 전체(페이지네이션 자동)</span><span>
python3 -m scripts.crawl_platforms_raw sohouse --fresh

</span><span># 공동체주택 전체</span><span>
python3 -m scripts.crawl_platforms_raw cohouse --fresh

</span><span># 청년(주택찾기 + BBS 공고)</span><span>
python3 -m scripts.crawl_platforms_raw youth --fresh --max-youth-bbs 0

</span><span># LH 공고 목록 + 상세 POST + 첨부</span><span>
python3 -m scripts.crawl_platforms_raw lh_ann --fresh

</span><span># SH 공급계획(행복주택 탭)</span><span>
python3 -m scripts.crawl_platforms_raw sh_happy --fresh

</span><span># SH 전체 공고(신규) — 실제 목록 URL 설정 필요</span><span>
python3 -m scripts.crawl_platforms_raw sh_ann --fresh

</span><span># 소개/정책/자격 페이지</span><span>
python3 -m scripts.crawl_platforms_raw platform_info --fresh
python3 -m scripts.crawl_platforms_raw seoul_happy_intro --fresh
</span></span></code></div></div></pre>

---

## 5) 참고/주의

- **RAW는 넓게, 중복 허용**이 원칙입니다. 삭제·필터링은 하지 않습니다.
  (실제 서비스에서 쓰는 정제/필터링은** \*\***PARSED\*\*에서 수행)
- 셀렉터나 페이징 동작은 사이트 개편 시 변경될 수 있으니,
  **실패 사례를 로깅**하고** \*\***셀렉터 후보\*\*를 확장해 주세요.
- `extras_json` 안의 값(예: LH\*\* **`detail_descriptor.form.panId`, 첨부 경로 등)은
  PARSED에서** \***\*매우 유용한 힌트**이므로 적극 활용하세요.
- 첨부 텍스트 추출은** \*\***시간이 오래 걸릴 수** 있으니** \***\*캐시**를 권장합니다.

---

# PARSED 작업자용: DB 모델 가이드(필수)

## TL;DR

- **DB는 하나** ,\*\* \*\* **테이블은 여러 개** .
- 중심 테이블은\*\* \*\* **items(=공고/단지/매물 레벨)** .
- 이미지/첨부/유닛(타입·평면도 등)처럼\*\* \*\* **여러 개가 달리는 건 전부 1:N 보조 테이블** .
- **중복 병합**은 items에서 하고, 병합 전 원본들은** \*\***source_map\*\*으로 추적.

## 1) 핵심 ERD (요약)

items (1)
├─< units
│ ├─< images (unit별 이미지가 있을 때 unit_id로도 연결)
│ └─< attachments (unit별 첨부가 있을 때 unit_id로도 연결)
├─< images (공고 라벨 이미지/조감도 이미지)
├─< attachments (공고 라벨 첨부)
├─< tables_raw (입주현황 등 CSV 추출본)
└─< source_map (RAW record_id 매핑/출처)

## 2) 최소 스키마 (PostgreSQL 예시 · SQLite도 타입만 살짝 바꾸면 동일)

-- 1) 공고/프로젝트(상위 엔티티)
CREATE TABLE items (
item_id BIGSERIAL PRIMARY KEY,
platform TEXT NOT NULL, -- 'sohouse','cohouse','ha_lh','sh_ann',...
item_bk TEXT UNIQUE, -- 자연키/논리키(LH panId 등). 없으면 NULL
title TEXT,
addr_std TEXT,
lat DOUBLE PRECISION,
lng DOUBLE PRECISION,
category TEXT, -- 사회/공동체/행복주택 등
crawled_at TIMESTAMPTZ,
source_hint JSONB -- 필요시 요약 메타
);

-- 2) 유닛(평형/타입/가격 등 세부)
CREATE TABLE units (
unit_id BIGSERIAL PRIMARY KEY,
item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
unit_plan TEXT, -- 59A, 84B ...
area_m2 NUMERIC,
deposit_krw BIGINT,
monthly_rent_krw BIGINT,
supply_count INT,
application_start DATE,
application_end DATE,
UNIQUE (item_id, unit_plan) -- 필요시 중복 방지(스냅샷이면 날짜 포함)
);

-- 3) 이미지(공고 레벨 & 선택적으로 유닛 레벨)
CREATE TABLE images (
image_id BIGSERIAL PRIMARY KEY,
item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
unit_id BIGINT REFERENCES units(unit_id) ON DELETE CASCADE, -- NULL 허용
file_path TEXT NOT NULL,
role TEXT, -- 'floorplan','banner','photo',...
UNIQUE (file_path) -- 파일 경로 기준 중복 방지(선택)
);

-- 4) 첨부(공고/유닛 공통)
CREATE TABLE attachments (
attachment_id BIGSERIAL PRIMARY KEY,
item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
unit_id BIGINT REFERENCES units(unit_id) ON DELETE CASCADE, -- NULL 허용
file_path TEXT NOT NULL,
filename TEXT,
ext TEXT,
text_path TEXT, -- 텍스트 추출 결과 저장 경로(선택)
is_ocr BOOLEAN DEFAULT FALSE
);

-- 5) 표 원본 CSV(입주현황 등)
CREATE TABLE tables_raw (
table_id BIGSERIAL PRIMARY KEY,
item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
unit_id BIGINT REFERENCES units(unit_id) ON DELETE CASCADE, -- 필요시
kind TEXT, -- 'occupancy','fees',...
csv_path TEXT NOT NULL
);

-- 6) 원본 매핑(프로비넌스: RAW record_id 연결)
CREATE TABLE source_map (
item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
record_id TEXT NOT NULL, -- RAW의 record_id
platform TEXT NOT NULL,
html_path TEXT,
extras_json JSONB,
PRIMARY KEY (item_id, record_id)
);

-- (권장 인덱스)
CREATE INDEX idx_items_platform ON items(platform);
CREATE INDEX idx_units_item_id ON units(item_id);
CREATE INDEX idx_images_item_id ON images(item_id);
CREATE INDEX idx_attachments_item_id ON attachments(item_id);

### “평면도가 여러 장인데요?”

- **images** 테이블에** \*\***행을 여러 개\*\* 넣으면 됩니다(1:N).
- 평면도만 따로 보고 싶다면\*\* \*\*`role='floorplan'` 같은 라벨을 써서 구분하세요.
- 타입별(59A/84B…) 보증금·월세가 다르면** \*\***units\*\* 테이블에 행을 나눠 기록.

## 3) 논리 ID(=item_id) 만들기 규칙

1. **가급적 플랫폼 고유 키 우선**

- LH:\*\* **`detail_descriptor.form.panId`(RAW** \*\*`extras_json`에서 꺼냄)
- SH/서울포털: 공고번호가 있으면 사용

2. 없다면** \*\***결합키 해시\*\*

<pre class="overflow-visible!" data-start="4255" data-end="4389"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>norm_title</span><span> = 한글/공백 정규화한 제목
</span><span>key_src</span><span> = f</span><span>"{platform}|{addr_std}|{norm_title}|{application_start or ''}"</span><span>
</span><span>item_id</span><span> = sha256(key_src)
</span></span></code></div></div></pre>

> **중요** : 중복 병합 시, 채택된 item_id가 바뀌지 않도록** \*\***항상 같은 규칙\*\*으로 생성.

## 4) PARSED 파이프라인 체크리스트

1. **RAW 적재 (staging)**
   - 각\*\* \*\*`data/raw/<date>/<source>/raw.csv`를 읽어 메모리/스테이징에 로드
   - `html_path` 또는 LH의\*\* \*\*`extras_json.detail_html_path` 기준으로 HTML 파싱
2. **HTML 파싱 → 공통 필드 추출**
   - 제목/주소/기간/공급호수/보증금/월세/면적 등
   - 단위 변환: 평→㎡, 만원→원(정수)
   - 날짜 포맷:\*\* \*\*`YYYY-MM-DD`
3. **주소 표준화 + 지오코딩(캐시)**
   - 결과:\*\* \*\*`addr_std, lat, lng, geocode_status`
4. **논리 ID 생성 → 중복 병합**
   - 플랫폼 고유 ID 있으면 우선
   - 없으면 결합키 해시
   - 병합된 원본은** \*\***source_map\*\*에 모두 기록
5. **1:N 테이블 채우기**
   - 첨부: RAW\*\* **`attachments/<rid>/…` →** \***\*attachments**
   - 이미지: RAW\*\* **`images/<rid>/…` →** \***\*images** (`role` 라벨 달기)
   - 입주현황 CSV 등:** \*\***tables_raw\*\*
6. **업서트(재실행 안전)**
   - `INSERT … ON CONFLICT(item_id) DO UPDATE` 패턴
   - 원본 매핑은\*\* **`(item_id, record_id)`를** \***\*복합 PK**로 중복 방지
7. **품질 리포트**
   - 누락률, 파싱 실패, 지오코딩 실패, 금액/날짜 변환 실패 등을 요약

## 5) 담당자용 Q&A 바로 답

- **“왜 DB를 하나만 써요?”**
  분석·조인·집계를 위해** \*\***단일 DB**가 유리합니다. 플랫폼은** \***\*컬럼 값**으로 구분하고, 스키마(테이블)는** \*\***데이터 형태(본체/첨부/이미지/유닛)\*\* 기준으로 나눕니다.
- **“평면도/이미지가 여러 장이면?”**
  **images** 테이블에\*\* \*\* **여러 행** . 필요하면\*\* \*\*`role='floorplan'`로 라벨링.
- **“공급 타입별 보증금/월세가 달라요.”**
  **units** 테이블로\*\* \*\* **행 분리** .\*\* \*\*`area_m2, deposit, monthly_rent, supply_count`를 타입별로 저장.
- **“RAW 중복이 있는데요?”**
  **의도된 설계**입니다. PARSED에서\*\* \*\* **논리 ID 생성→병합** , 그리고** \*\***source_map\*\*으로 출처 추적.
- **“extras_json은 언제 써요?”**
  당장 정규화 못한 값(예: LH POST 폼, 원시 문자열)을 넣고, 파서 개선 시 점진 정규화.
