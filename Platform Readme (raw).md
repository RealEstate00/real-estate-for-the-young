# 서울주택·부동산 RAW 크롤링 README

이 문서는** \*\***서울주택·부동산 RAW 크롤링(완료 버전)** 의 실제 코드(`/scripts/crawl_public_raw.py`) 기준으로 작성되었습니다. 실행 방법, 산출물(폴더/파일),** \*\*`raw.csv` 스키마, 트러블슈팅, 다음 단계(Parsed 이행)를 정리합니다.

> 목표는 “ **크롤링은 넓고 안정적으로** ,\*\* \*\* **정제·표준화·병합은 Parsed에서** ”.

---

## 1) 산출물 구조 (실제 폴더명)

크롤 시점별 루트:

```
project_root/
  data/
    raw/
      <YYYY-MM-DD>/
        rtms_rent/
          raw.csv                 # RTMS 전/월세 요약 매니페스트
          html/                   # 상세/조회 HTML 스냅샷
          tables/                 # 표 구조화 결과 (JSON + CSV)
          downloads/              # (선택) 엑셀 다운로드 보관
        landprice/
          raw.csv                 # 토지가격 ZIP 다운로드 매니페스트
          downloads/              # 서울시 ZIP 원본
          extracted_csv/          # ZIP 해제된 CSV 모음 (landprice_extract)
```

---

## 2) 실행 방법 (CLI 실제 서브커맨드)

스크립트:\*\* \*\*`scripts/crawl_public_raw.py`

```bash
# 1) RTMS 전/월세 전수 크롤링 (연도/분기/전월세 탭 자동 순회)
python scripts/crawl_public_raw.py rtms_all \
  --from 2006 \
  --to 2025 \
  --throttle 150

# 2) 토지가격 ZIP 파일 일괄 수집
python scripts/crawl_public_raw.py landprice_files

# 3) 수집된 ZIP → CSV 추출 (extracted_csv/ 생성)
python scripts/crawl_public_raw.py landprice_extract
```

**옵션**

- `--from / --to` : RTMS 연도 범위(미지정 시 2006~현재 연도)
- `--throttle` : 요청 간 대기(ms). 기본 150ms

> 헤드리스/디버그 모드는 코드 내부 기본값을 따릅니다.

---

## 3)\*\* \*\*`raw.csv` 스키마 (실측)

### A)\*\* \*\*`rtms_rent/raw.csv`

`RAW_HEADER` 스키마에 따라 행이 append됩니다. 코드 상 필드 구성은 다음 정보를 포함합니다.

- 공통 메타:\*\* \*\*`record_id, title, address, list_url, detail_url, detail_descriptor, html_path, image_paths, tables_paths, extras_json, crawled_at`
- `extras_json` 예시 키:\*\* **`sigungu, dong, year, quarter, jw_gubun` (전세/월세 구분),** \*\*`tab_name`
- 표 데이터 산출물:\*\* \*\*`tables/rtms_{tab}_{sigungu}_{dong}_{year}Q{quarter}_jw{rent}.json|csv`

> HTML 스냅샷은\*\* **`html/`에 저장되며, 일부 상세 화면은** \*\*`_detail.html` 네이밍을 사용합니다.

### B)\*\* \*\*`landprice/raw.csv`

ZIP 다운로드 결과의 매니페스트이며, 코드에서 다음 컬럼으로 저장합니다:

- `file_id, title, saved_path, error, crawl_date, crawled_at`

ZIP 해제 후 CSV는\*\* \*\*`extracted_csv/` 폴더에 생성됩니다(매니페스트는 유지).

---

## 4) 트러블슈팅 (코드 동작 기준)

- **RTMS 탭 전환 실패** : 버튼 클릭 실패 시 JS 폴백(`fn_tab('rentApartment')`). 그래도 실패하면\*\* \*\*`safe_wait_any(#selectJWGubun)` 셀렉터 대기 시간을 확장하세요.
- **연도/분기 드롭다운 파싱 실패** : CLI로\*\* \*\*`--from/--to`를 지정하면 연도 리스트를 보강합니다(기본 2006~현재).
- **표 저장** : 표를 찾지 못하면 스킵 로그 출력. 표를 찾은 경우\*_ \*\*`tables/_.json|csv` 동시 저장.
- **토지가격 ZIP** :\*\* **`landprice_files`로 매니페스트(`raw.csv`)에 적재 후,** \*\*`landprice_extract`로 일괄 해제(`extracted_csv/`). 매니페스트가 없으면 추출 단계에서 “No manifest file found”.

---

## 5) 다음 단계(Parsed 가이드)

- **HTML → 필드 파싱** :\*\* \*\*`sigungu/dong/아파트명/전월세/년/분기`를 표준 스키마로 투영
- **주소 정규화·좌표화** : 법정동/행정동 코드 매핑, 좌표 캐시 적용
- **요금 단위 통일** : 보증금/월세(₩), 전용면적(㎡)
- **중복 판정** : (정규화된 제목+주소)+기간 근접, 출처별 고유 키 보조

---

## 6) 변경 이력 (요약)

- **2025-08-29** :\*_ **`rtms_all`,** **`landprice_files`,** **`landprice_extract` CLI 고정. 출력 폴더명을** **`rtms_rent/`,** **`landprice/`로 확정.** \*\*`tables/_.json|csv` 동시 산출.

---
