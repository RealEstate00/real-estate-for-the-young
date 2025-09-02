# real-estate-for-the-young

## 설치 항목

- playwright install chromium

## 크롤링 진행

- 1. seoul portal happy intro // 서울주거포털 행복주택 소개 스냅샷

  - python3 -m scripts.crawl_platforms_raw seoul_happy_intro
  - python -m scripts.crawl_platforms_raw seoul_happy_intro

- 2. sh happy plan // SH 공급계획(행복주택 탭) 표 스냅샷

  - python3 -m scripts.crawl_platforms_raw sh_happy
  - python -m scripts.crawl_platforms_raw sh_happy

- 3. lh announcements // LH 공고 목록(최대 80행)

  - python3 -m scripts.crawl_platforms_raw lh_ann
  - python -m scripts.crawl_platforms_raw lh_ann

- 4. sohouse // 사회주택 목록→상세/이미지

  - python3 -m scripts.crawl_platforms_raw sohouse
  - python -m scripts.crawl_platforms_raw sohouse

- 5. cohouse // 공동체주택 목록→상세/이미지

  - python3 -m scripts.crawl_platforms_raw cohouse
  - python -m scripts.crawl_platforms_raw cohouse

- 6. platform info // 소개/입주자격/청년안심 소개·금융

  - python3 -m scripts.crawl_platforms_raw platform_info
  - python -m scripts.crawl_platforms_raw platform_info

- 7. youth // 청년안심 주택찾기 + 모집공고(BBS)

  - python3 -m scripts.crawl_platforms_raw youth
  - python -m scripts.crawl_platforms_raw youth
