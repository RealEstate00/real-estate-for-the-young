"""
detail.__init__.py
- 상세 페이지에서 '탭 전환 → HTML 추출 → 각 파서(parse_*) 호출'을 한 번에
- 반환: {
    "overview": {...},        # dict (단일행)
    "floorplan": [...],       # list[dict] (다중행)
    "movein": [...],
    "location": {... or [...]},
    "amenities": {...},
    "about": {...}
  }
"""

from src.config import (
    TAB_OVERVIEW, TAB_FLOORPLAN, TAB_MOVEIN, TAB_LOCATION, TAB_AMENITIES, TAB_ABOUT
)
from src.utils import click_if_exists, page_html
from .overview import parse_overview
from .floorplan import parse_floorplan
from .movein import parse_movein
from .location import parse_location
from .amenities import parse_amenities
from .about import parse_about

def collect_details(driver, house_name: str) -> dict:
    """상세 페이지의 모든 섹션을 차례로 수집하여 dict로 묶어 반환"""
    data = {}

    # 1) 상세소개
    click_if_exists(driver, f"a[href='{TAB_OVERVIEW}']")
    data["overview"] = parse_overview(page_html(driver), house_name)

    # 2) 평면도
    click_if_exists(driver, f"a[href='{TAB_FLOORPLAN}']")
    data["floorplan"] = parse_floorplan(page_html(driver), house_name)

    # 3) 입주현황
    click_if_exists(driver, f"a[href='{TAB_MOVEIN}']")
    data["movein"] = parse_movein(page_html(driver), house_name)

    # 4) 위치
    click_if_exists(driver, f"a[href='{TAB_LOCATION}']")
    data["location"] = parse_location(page_html(driver), house_name)

    # 5) 편의시설
    click_if_exists(driver, f"a[href='{TAB_AMENITIES}']")
    data["amenities"] = parse_amenities(page_html(driver), house_name)

    # 6) 사업자소개
    click_if_exists(driver, f"a[href='{TAB_ABOUT}']")
    data["about"] = parse_about(page_html(driver), house_name)

    return data
