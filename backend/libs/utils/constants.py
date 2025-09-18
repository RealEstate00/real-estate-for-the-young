#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constants and configuration for Seoul Housing Assist Bot
"""

from datetime import timezone, timedelta

# Timezone
KST = timezone(timedelta(hours=9))

# Allowed file extensions for downloads
ALLOWED_EXTS = {".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}

# Platform ID mapping
PLATFORM_ID_MAP = {
    "sohouse": 1, "cohouse": 2,
    "youth_home": 3, "youth_bbs": 3,
    "sh_ann": 4, "sh_plan_happy": 4, "ha_sh": 4, "ha_lh": 4,
    "lh_ann": 4, "seoul_portal_happy_intro": 4,
    "sh_happy_eligibility": 4, "sh_main_page": 4, "sh_search": 4, "sh_happy_intro": 4,
    "sohouse_intro": 1, "cohouse_intro": 2, "youth_intro": 3, "youth_finance": 3,
}

# Platform URLs
SO_BASE = "https://soco.seoul.go.kr"
SO_SOCIAL_LIST = f"{SO_BASE}/soHouse/pgm/home/sohome/list.do?menuNo=300006"
SO_COMM_LIST = f"{SO_BASE}/coHouse/pgm/home/cohome/list.do?menuNo=200043"
SH_PLAN = "https://www.i-sh.co.kr/main/lay2/S1T243C1043/contents.do"
LH_LIST = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"

# Intro/policy pages
SOCIAL_INTRO_URL = f"{SO_BASE}/soHouse/main/contents.do?menuNo=300007"
SOCIAL_ELIG_URL = f"{SO_BASE}/soHouse/main/contents.do?menuNo=300037"
CO_INTRO_URL = f"{SO_BASE}/coHouse/main/contents.do?menuNo=200027"
YOUTH_INTRO_URL = f"{SO_BASE}/youth/main/contents.do?menuNo=400012"
YOUTH_FINANCE_URL = f"{SO_BASE}/youth/main/contents.do?menuNo=400021"
SEOUL_PORTAL_HAPPY_INTRO_URL = "https://housing.seoul.go.kr/site/main/content/sh01_060503"

# SH announcement list
SH_ANN_LIST = "https://www.i-sh.co.kr/main/lay2/S1T294C297/www/brd/m_247/list.do?multi_itm_seq=2"

# New website URLs
SH_HAPPY_ELIGIBILITY_URL = "https://www.i-sh.co.kr/app/lay2/S48T1603C3572/contents.do"
SH_MAIN_PAGE_URL = "https://www.i-sh.co.kr/houseinfo/main/mainPage.do"
SH_SEARCH_URL = "https://www.i-sh.co.kr/search/view/search.jsp"
SH_HAPPY_INTRO_URL = "https://www.i-sh.co.kr/app/lay2/S48T1594C3552/contents.do"
