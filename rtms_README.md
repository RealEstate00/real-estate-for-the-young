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

RTMS 전·월세 요약 테이블 기반으로, 다음 필드를 저장합니다(첨부/이미지 없음).

- **필수 키/식별** :\*\* **`sigungu`,** **`dong`,** **`apt_name`,** **`year`,** **`quarter`,** \*\*`jw_gubun`(전세/월세)
- **기타 메타** :\*\* **`record_id`,** **`list_url`,** **`detail_url`,** **`detail_descriptor`,** **`html_path`,** **`tables_paths`,** **`extras_json`,** \*\*`crawled_at`
- **테이블 산출물** :\*\* \*\*`tables/rtms_{sigungu}_{dong}_{apt_name}_{year}Q{quarter}_{jw}.json|csv`

> 주의:** \*\***제목(title) 컬럼은 존재하지 않습니다.** UI 기준 명칭은** \*\*`apt_name`으로 취급합니다.

### B)\*\* \*\*`landprice/raw.csv`

토지가격(개별공시지가 등) ZIP 다운로드 매니페스트입니다(첨부/이미지 없음).

- `file_id`,\*\* **`title`(다운로드 항목명),** **`saved_path`,** **`error`,** **`crawl_date`,** \*\*`crawled_at`
- ZIP 해제 후 CSV는\*\* \*\*`extracted_csv/`에 생성됩니다.

---

## 4) 트러블슈팅 (코드 동작 기준)

- **RTMS 탭 전환 실패** : 버튼 클릭 실패 시 JS 폴백(`fn_tab('rentApartment')`). 그래도 실패하면\*\* \*\*`safe_wait_any(#selectJWGubun)` 셀렉터 대기 시간을 확장하세요.
- **연도/분기 드롭다운 파싱 실패** : CLI로\*\* \*\*`--from/--to`를 지정하면 연도 리스트를 보강합니다(기본 2006~현재).
- **표 저장** : 표를 찾지 못하면 스킵 로그 출력. 표를 찾은 경우\*_ \*\*`tables/_.json|csv` 동시 저장.
- **토지가격 ZIP** :\*\* **`landprice_files`로 매니페스트(`raw.csv`)에 적재 후,** \*\*`landprice_extract`로 일괄 해제(`extracted_csv/`). 매니페스트가 없으면 추출 단계에서 “No manifest file found”.

---

## 5) 다음 단계(Parsed 가이드)

- **RTMS 표준화 스키마 제안** :\*\* \*\*`sigungu, dong, apt_name, trade_type(jw_gubun), year, quarter, deposit_krw, monthly_rent_krw, area_m2(전용/공급), floors, built_year, data_source, record_id, crawled_at`
- **Landprice 표준화 스키마 제안** :\*\* \*\*`year, dong_code, dong_name, lot_no, land_price, category(개별/표준), data_source, file_id, crawled_at`
- **주소·좌표 보강** : 법정동/행정동 코드 매핑 후 지오코딩(캐시 적용)
- **요금/면적 단위 통일** : 금액(₩), 면적(㎡)
- **중복 판정(데이터셋별)**RTMS:\*\* **`(sigungu, dong, apt_name, year, quarter, jw_gubun, 주요수치해시)`를** \***\*주 키**로 사용. 동일 조합 + 값 동일 시 중복 처리

  Landprice:\*\* **`(year, dong_code, lot_no, category)` 조합을** \***\*주 키**로 사용

---

## 6) 변경 이력 (요약)

- **2025-08-29** :\*_ **`rtms_all`,** **`landprice_files`,** **`landprice_extract` CLI 고정. 출력 폴더명을** **`rtms_rent/`,** **`landprice/`로 확정.** \*\*`tables/_.json|csv` 동시 산출.

---

## 7) 유지보수 포인트

- [ ] 경로 유틸:\*\* **`run_dir("rtms_rent")`,** \*\*`run_dir("landprice")`
- [ ] 표 스냅샷:\*\* \*\*`save_csv(...)`, JSON은 동일 베이스네임으로 저장
- [ ] 매니페스트:\*\* \*\*`append_csv(base_dir/"raw.csv", ...)` 사용
- [ ] 안정화:\*\* **`robust_goto`,** **`safe_wait_any`,** \*\*`Progress.update` 로그 확인
