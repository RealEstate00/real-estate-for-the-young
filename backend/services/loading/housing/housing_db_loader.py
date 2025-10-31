# -*- coding: utf-8 -*-
"""
Natural-key first loader for housing schema.

Tables (PK):
- housing.code_master(cd)
- housing.platforms(code)
- housing.addresses(address_ext_id PK)  # 정규화 JSON의 id -> address_ext_id 로 매핑
- housing.notices(notice_id)
- housing.units(unit_id)
- housing.unit_features(unit_id UNIQUE FK -> units.unit_id)
- housing.notice_tags (notice_id, tag_type, tag_value) UNIQUE

Usage:
  data-load housing
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ------------------------------
# Config
# ------------------------------
@dataclass
class LoaderConfig:
    root_dir: Path
    db_url: str
    only_latest_date: bool = True

# ------------------------------
# Loader
# ------------------------------
class HousingLoader:
    """
    정규화된 JSON 데이터를 PostgreSQL(housing 스키마)에 적재
    """

    def __init__(self, cfg: LoaderConfig):
        self.cfg = cfg
        self.engine: Engine = create_engine(self.cfg.db_url, future=True)
        self.conn: Optional[Connection] = None
        
        # 로거 설정
        import logging
        self.logger = logging.getLogger(__name__)

        self._code_set: set[str] = set()
        self._platform_set: set[str] = set()
        self._notice_set: set[str] = set()
        self._unit_set: set[str] = set()

        self._current_platform: Optional[str] = None
        self._notices_has_address_id: bool = False

    # ---------------- helpers ----------------
    @staticmethod
    def _none_if_blank(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    def _valid_code(self, cd: Optional[str]) -> Optional[str]:
        cd = self._none_if_blank(cd)
        if cd and cd in self._code_set:
            return cd
        return None

    def _read_platform_payload(self, plat_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
        """플랫폼 폴더 내 표준 파일만 읽음"""
        out: Dict[str, List[Dict[str, Any]]] = {}
        for fname in ("platforms.json", "addresses.json", "notices.json",
                      "units.json", "unit_features.json", "notice_tags.json"):
            p = plat_dir / fname
            key = p.stem
            if p.exists():
                try:
                    out[key] = json.loads(p.read_text(encoding="utf-8"))
                    log.info("  - %s: %d개 레코드 로드", fname, len(out[key]))
                except Exception as e:
                    log.error("  - %s 읽기 실패: %s (빈 배열로 대체)", fname, e)
                    out[key] = []
            else:
                out[key] = []
        return out
    
    def _detect_schema_flags(self) -> None:
        assert self.conn is not None
        q = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='housing' AND table_name='notices' AND column_name='address_id'
        LIMIT 1
        """)
        self._notices_has_address_id = self.conn.execute(q).first() is not None
        log.debug("notices.address_id exists? %s", self._notices_has_address_id)


    # ---------------- public ----------------
    def run(self) -> None:
        root = self.cfg.root_dir
        if not root.exists():
            raise FileNotFoundError(f"normalized root not found: {root}")

       # 0) codes.json
        global_codes = root / "codes.json"
        if global_codes.exists():
            with self.engine.begin() as conn:
                self.conn = conn
                codes = json.loads(global_codes.read_text(encoding="utf-8"))
                self._load_codes(codes)
                self.conn = None

        # 1) 날짜 폴더 선택
        all_dirs = [p for p in root.iterdir() if p.is_dir()]
        date_dirs = [p for p in all_dirs if DATE_DIR_RE.match(p.name)]
        if not date_dirs:
            log.warning("날짜 폴더(YYYY-MM-DD) 없음: %s", [p.name for p in all_dirs])
            return

        date_dirs.sort(key=lambda p: datetime.strptime(p.name, "%Y-%m-%d"))
        targets = date_dirs
        if self.cfg.only_latest_date:
            # 가장 최근 날짜 중 실제 플랫폼 폴더가 존재하는 것만 선택
            selected = None
            for d in reversed(date_dirs):
                if any(p.is_dir() for p in d.iterdir()):
                    selected = d
                    break
            if not selected:
                log.warning("플랫폼 폴더가 있는 날짜 폴더를 찾지 못함.")
                return
            targets = [selected]

        # 2) 날짜/플랫폼 단위 처리
        for d in targets:
            plat_dirs = [p for p in d.iterdir() if p.is_dir()]
            if not plat_dirs:
                log.info("Skip %s (플랫폼 폴더 없음)", d.name)
                continue

            for plat_dir in plat_dirs:
                self._current_platform = plat_dir.name
                log.info("Processing %s/%s", d.name, plat_dir.name)
                payload = self._read_platform_payload(plat_dir)

                # 여기서 매 배치마다 트랜잭션/커넥션을 새로 열고 닫음
                with self.engine.begin() as conn:
                    self.conn = conn
                    self._detect_schema_flags()  # ✅ 여기서 1회 감지

                    # FK 비의존 → 의존 순서로 적재
                    self._load_platforms(payload.get("platforms", []))
                    self._load_addresses(payload.get("addresses", []))
                    self._load_notices(payload.get("notices", []))
                    self._load_units(payload.get("units", []))
                    self._load_unit_features(payload.get("unit_features", []))
                    self._load_notice_tags(payload.get("notice_tags", []))

                    self.conn = None

        log.info("All done.")

    # ---------------- caches ----------------
    def _refresh_code_cache_from_db(self) -> None:
        rows = self.conn.execute(text("SELECT cd FROM housing.code_master")).fetchall()
        self._code_set = {r[0] for r in rows}

    def _refresh_platform_cache_from_db(self) -> None:
        rows = self.conn.execute(text("SELECT code FROM housing.platforms")).fetchall()
        self._platform_set = {r[0] for r in rows}

    def _refresh_notice_cache_from_db(self) -> None:
        rows = self.conn.execute(text("SELECT notice_id FROM housing.notices")).fetchall()
        self._notice_set = {r[0] for r in rows}

    def _refresh_unit_cache_from_db(self) -> None:
        rows = self.conn.execute(text("SELECT unit_id FROM housing.units")).fetchall()
        self._unit_set = {r[0] for r in rows}

    # ---------------- loaders ----------------
    def _load_codes(self, codes: List[Dict[str, Any]]) -> None:
        if not codes:
            self._refresh_code_cache_from_db()
            return

        sql = """
        INSERT INTO housing.code_master (cd, name, description, upper_cd)
        VALUES (:cd, :name, :description, :upper_cd)
        ON CONFLICT (cd) DO UPDATE
          SET name = EXCLUDED.name,
              description = EXCLUDED.description,
              upper_cd = EXCLUDED.upper_cd
        """
        for c in codes:
            params = {
                "cd": c.get("cd"),
                "name": c.get("name") or "",
                "description": self._none_if_blank(c.get("description")),
                "upper_cd": self._none_if_blank(c.get("upper_cd")),
            }
            self.conn.execute(text(sql), params)

        self._refresh_code_cache_from_db()

    def _load_platforms(self, items: List[Dict[str, Any]]) -> None:
        # 플랫폼 폴더명이 실제 코드일 수도 있으니, 최소 한 줄은 보장 차원에서 upsert
        if not items and self._current_platform:
            items = [{"code": self._current_platform, "name": self._current_platform, "url": None}]

        if not items:
            self._refresh_platform_cache_from_db()
            return

        log.info("플랫폼 데이터 저장: %d개", len(items))
        sql = """
        INSERT INTO housing.platforms
          (code, name, url, platform_code, is_active, created_at, updated_at)
        VALUES
          (:code, :name, :url, :platform_code, COALESCE(:is_active, TRUE), now(), now())
        ON CONFLICT (code) DO UPDATE
          SET name = EXCLUDED.name,
              url = EXCLUDED.url,
              platform_code = EXCLUDED.platform_code,
              is_active = EXCLUDED.is_active,
              updated_at = now()
        """
        for p in items:
            code = p.get("code") or self._current_platform
            params = {
                "code": code,
                "name": p.get("name") or code or "",
                "url": self._none_if_blank(p.get("url") or p.get("base_url")),
                "platform_code": self._valid_code(p.get("platform_code")),
                "is_active": p.get("is_active"),
            }
            self.conn.execute(text(sql), params)

        self._refresh_platform_cache_from_db()

    def _load_addresses(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        log.info("주소 데이터 저장: %d개", len(items))

        # 정규화 JSON 키 보정: id -> address_ext_id, lat/lon -> latitude/longitude
        sql = """
        INSERT INTO housing.addresses (
            address_ext_id, address_raw, ctpv_nm, sgg_nm, emd_nm, emd_cd,
            building_main_no, building_sub_no, building_name,
            road_name_full, jibun_name_full, latitude, longitude,
            created_at, updated_at
        ) VALUES (
            :address_ext_id, :address_raw, :ctpv_nm, :sgg_nm, :emd_nm, NULLIF(:emd_cd, ''),
            :building_main_no, :building_sub_no, :building_name,
            :road_name_full, :jibun_name_full, :latitude, :longitude,
            now(), now()
        )
        ON CONFLICT (address_ext_id) DO UPDATE
          SET address_raw = EXCLUDED.address_raw,
              ctpv_nm = EXCLUDED.ctpv_nm,
              sgg_nm = EXCLUDED.sgg_nm,
              emd_nm = EXCLUDED.emd_nm,
              emd_cd = NULLIF(EXCLUDED.emd_cd, ''),
              building_main_no = EXCLUDED.building_main_no,
              building_sub_no = EXCLUDED.building_sub_no,
              building_name = EXCLUDED.building_name,
              road_name_full = EXCLUDED.road_name_full,
              jibun_name_full = EXCLUDED.jibun_name_full,
              latitude = EXCLUDED.latitude,
              longitude = EXCLUDED.longitude,
              updated_at = now()
        """
        for a in items:
            addr_id = a.get("address_ext_id") or a.get("id")  # ✅ 키 보정
            emd_cd = self._valid_code(a.get("emd_cd"))
            params = {
                "address_ext_id": addr_id,
                "address_raw": a.get("address_raw") or a.get("address") or "",
                "ctpv_nm": self._none_if_blank(a.get("ctpv_nm")),
                "sgg_nm": self._none_if_blank(a.get("sgg_nm")),
                "emd_nm": self._none_if_blank(a.get("emd_nm")),
                "emd_cd": emd_cd or "",
                "building_main_no": self._none_if_blank(a.get("building_main_no")),
                "building_sub_no": self._none_if_blank(a.get("building_sub_no")),
                "building_name": self._none_if_blank(a.get("building_name")),
                "road_name_full": self._none_if_blank(a.get("road_name_full")),
                "jibun_name_full": self._none_if_blank(a.get("jibun_name_full")),
                "latitude": self._none_if_blank(a.get("latitude") if "latitude" in a else a.get("lat")),
                "longitude": self._none_if_blank(a.get("longitude") if "longitude" in a else a.get("lon")),
            }
            if not params["address_ext_id"]:
                log.warning("주소 레코드에 ID가 없습니다. 건너뜀: %s", a)
                continue
            self.conn.execute(text(sql), params)

    def _load_notices(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            self._refresh_notice_cache_from_db()
            return

        log.info("공고 데이터 저장: %d개", len(items))

        if getattr(self, "_notices_has_address_id", False):
            sql = """
            INSERT INTO housing.notices (
                notice_id, platform_code, title, status, address_raw, address_id,
                building_type, notice_extra, has_images, has_floorplan, has_documents,
                list_url, detail_url, posted_at, last_modified, apply_start_at, apply_end_at,
                created_at, updated_at
            ) VALUES (
                :notice_id, :platform_code, :title, COALESCE(:status, 'open'),
                :address_raw, :address_id, :building_type, :notice_extra,
                COALESCE(:has_images, FALSE), COALESCE(:has_floorplan, FALSE), COALESCE(:has_documents, FALSE),
                :list_url, :detail_url, :posted_at, :last_modified, :apply_start_at, :apply_end_at,
                now(), now()
            )
            ON CONFLICT (notice_id) DO UPDATE SET
                platform_code = EXCLUDED.platform_code,
                title = EXCLUDED.title,
                status = EXCLUDED.status,
                address_raw = EXCLUDED.address_raw,
                address_id = EXCLUDED.address_id,
                building_type = EXCLUDED.building_type,
                notice_extra = EXCLUDED.notice_extra,
                has_images = EXCLUDED.has_images,
                has_floorplan = EXCLUDED.has_floorplan,
                has_documents = EXCLUDED.has_documents,
                list_url = EXCLUDED.list_url,
                detail_url = EXCLUDED.detail_url,
                posted_at = EXCLUDED.posted_at,
                last_modified = EXCLUDED.last_modified,
                apply_start_at = EXCLUDED.apply_start_at,
                apply_end_at = EXCLUDED.apply_end_at,
                updated_at = now()
            """
        else:
            # address_id 없는 스키마용
            sql = """
            INSERT INTO housing.notices (
                notice_id, platform_code, title, status, address_raw,
                building_type, notice_extra, has_images, has_floorplan, has_documents,
                list_url, detail_url, posted_at, last_modified, apply_start_at, apply_end_at,
                created_at, updated_at
            ) VALUES (
                :notice_id, :platform_code, :title, COALESCE(:status, 'open'),
                :address_raw, :building_type, :notice_extra,
                COALESCE(:has_images, FALSE), COALESCE(:has_floorplan, FALSE), COALESCE(:has_documents, FALSE),
                :list_url, :detail_url, :posted_at, :last_modified, :apply_start_at, :apply_end_at,
                now(), now()
            )
            ON CONFLICT (notice_id) DO UPDATE SET
                platform_code = EXCLUDED.platform_code,
                title = EXCLUDED.title,
                status = EXCLUDED.status,
                address_raw = EXCLUDED.address_raw,
                building_type = EXCLUDED.building_type,
                notice_extra = EXCLUDED.notice_extra,
                has_images = EXCLUDED.has_images,
                has_floorplan = EXCLUDED.has_floorplan,
                has_documents = EXCLUDED.has_documents,
                list_url = EXCLUDED.list_url,
                detail_url = EXCLUDED.detail_url,
                posted_at = EXCLUDED.posted_at,
                last_modified = EXCLUDED.last_modified,
                apply_start_at = EXCLUDED.apply_start_at,
                apply_end_at = EXCLUDED.apply_end_at,
                updated_at = now()
            """

        for n in items:
            raw_platform = n.get("platform_code") or n.get("platform_id") or n.get("source")
            platform_code = self._none_if_blank(raw_platform)
            if not platform_code or (self._platform_set and platform_code not in self._platform_set):
                platform_code = self._current_platform

            building_type = self._valid_code(n.get("building_type"))

            # notice_extra 는 dict 또는 str 모두 허용
            ne = n.get("notice_extra")
            if isinstance(ne, str):
                ne_str = ne
            else:
                try:
                    ne_str = json.dumps(ne or {}, ensure_ascii=False)
                except Exception:
                    ne_str = "{}"

            base_params = {
                "notice_id": n.get("notice_id") or n.get("source_key"),
                "platform_code": platform_code,
                "title": n.get("title") or "",
                "status": self._none_if_blank(n.get("status")),
                "address_raw": self._none_if_blank(n.get("address_raw")),
                "building_type": building_type,
                "notice_extra": ne_str,
                "has_images": n.get("has_images"),
                "has_floorplan": n.get("has_floorplan"),
                "has_documents": n.get("has_documents"),
                "list_url": self._none_if_blank(n.get("list_url")),
                "detail_url": self._none_if_blank(n.get("detail_url")),
                "posted_at": self._none_if_blank(n.get("posted_at")),
                "last_modified": self._none_if_blank(n.get("last_modified")),
                "apply_start_at": self._none_if_blank(n.get("apply_start_at")),
                "apply_end_at": self._none_if_blank(n.get("apply_end_at")),
            }

            if getattr(self, "_notices_has_address_id", False):
                # address_id는 address_ext_id를 사용해서 실제 addresses.id를 찾아서 매핑
                addr_ext_id = n.get("address_id")
                if addr_ext_id:
                    # address_ext_id로 실제 데이터베이스의 addresses.id를 조회
                    sql_addr = "SELECT id FROM housing.addresses WHERE address_ext_id = :address_ext_id LIMIT 1"
                    result = self.conn.execute(text(sql_addr), {"address_ext_id": addr_ext_id}).first()
                    base_params["address_id"] = result[0] if result else None
                else:
                    base_params["address_id"] = None

            self.conn.execute(text(sql), base_params)

        self._refresh_notice_cache_from_db()


    def _load_units(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            self._refresh_unit_cache_from_db()
            return

        log.info("유닛 데이터 저장: %d개", len(items))
        sql = """
        INSERT INTO housing.units (
            unit_id, notice_id, unit_type, deposit, rent, maintenance_fee,
            area_m2, floor, room_number, occupancy_available, occupancy_available_at,
            capacity, created_at, updated_at
        ) VALUES (
            :unit_id, :notice_id, :unit_type, :deposit, :rent, :maintenance_fee,
            :area_m2, :floor, :room_number, :occupancy_available, :occupancy_available_at,
            :capacity, now(), now()
        )
        ON CONFLICT (unit_id) DO UPDATE SET
            notice_id = EXCLUDED.notice_id,
            unit_type = EXCLUDED.unit_type,
            deposit = EXCLUDED.deposit,
            rent = EXCLUDED.rent,
            maintenance_fee = EXCLUDED.maintenance_fee,
            area_m2 = EXCLUDED.area_m2,
            floor = EXCLUDED.floor,
            room_number = EXCLUDED.room_number,
            occupancy_available = EXCLUDED.occupancy_available,
            occupancy_available_at = EXCLUDED.occupancy_available_at,
            capacity = EXCLUDED.capacity,
            updated_at = now()
        """
        for u in items:
            params = {
                "unit_id": u.get("unit_id") or u.get("space_id"),
                "notice_id": u.get("notice_id") or u.get("source_key"),
                "unit_type": self._none_if_blank(u.get("unit_type")),
                "deposit": self._none_if_blank(u.get("deposit")),
                "rent": self._none_if_blank(u.get("rent")),
                "maintenance_fee": self._none_if_blank(u.get("maintenance_fee") or u.get("management_fee")),
                "area_m2": self._none_if_blank(u.get("area_m2")),
                "floor": self._none_if_blank(u.get("floor")),
                "room_number": self._none_if_blank(u.get("room_number") or u.get("room_no")),
                "occupancy_available": u.get("occupancy_available") if "occupancy_available" in u else u.get("is_available"),
                "occupancy_available_at": self._none_if_blank(u.get("occupancy_available_at") or u.get("available_at")),
                "capacity": self._none_if_blank(u.get("capacity") or u.get("max_occupancy")),
            }
            self.conn.execute(text(sql), params)

        self._refresh_unit_cache_from_db()

    def _load_unit_features(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return

        log.info("유닛 특징 데이터 저장: %d개", len(items))
        
        # _unit_set이 비어있으면 현재 트랜잭션에서 units를 다시 조회
        if not self._unit_set:
            rows = self.conn.execute(text("SELECT unit_id FROM housing.units")).fetchall()
            self._unit_set = {r[0] for r in rows}

        sql = """
        INSERT INTO housing.unit_features (
            unit_id, room_count, bathroom_count, direction, created_at, updated_at
        ) VALUES (
            :unit_id, :room_count, :bathroom_count, :direction, now(), now()
        )
        ON CONFLICT (unit_id) DO UPDATE SET
            room_count = EXCLUDED.room_count,
            bathroom_count = EXCLUDED.bathroom_count,
            direction = EXCLUDED.direction,
            updated_at = now()
        """
        skipped = 0
        for f in items:
            uid = f.get("unit_id")
            if not uid or uid not in self._unit_set:
                skipped += 1
                continue
            params = {
                "unit_id": uid,
                "room_count": self._none_if_blank(f.get("room_count")),
                "bathroom_count": self._none_if_blank(f.get("bathroom_count")),
                "direction": self._none_if_blank(f.get("direction")),
            }
            self.conn.execute(text(sql), params)
        if skipped:
            log.info("unit_features skipped (units missing): %d", skipped)

    def _load_notice_tags(self, items: list[dict]):
        sql = """
            INSERT INTO housing.notice_tags (notice_id, tag_type, tag_value, created_at, updated_at)
            VALUES (:notice_id, :tag_type, :tag_value, now(), now())
            ON CONFLICT (notice_id, tag_type, tag_value) DO NOTHING
        """
        params = []
        skipped_null_type = 0
        skipped_empty_value = 0
        for it in items:
            # 정규화된 데이터 구조에 맞게 수정
            # tag_type은 정규화 과정에서 추가된 필드, 없으면 misc로 설정
            t = it.get("tag_type", "misc")
            # tag_value는 description 필드 사용
            v = (it.get("description") or it.get("tag_value") or it.get("value") or "").strip()
            nid = it.get("notice_id")
            
            if not v:
                skipped_empty_value += 1
                continue
            if not t:
                t = "misc"
                skipped_null_type += 1
                
            t = t.strip().lower()
            params.append({"notice_id": nid, "tag_type": t, "tag_value": v})
        if params:
            self.conn.execute(text(sql), params)
        self.logger.info("notice_tags saved: %d, skipped(empty_value): %d, skipped(null_type): %d", 
                        len(params), skipped_empty_value, skipped_null_type)

# ---------------- tiny runner ----------------
def _env(name: str, default: str) -> str:
    import os
    return os.environ.get(name, default)

def build_db_url() -> str:
    user = _env("PG_USER", "postgres")
    pwd  = _env("PG_PASSWORD", "post1234")
    host = _env("PG_HOST", "localhost")
    port = _env("PG_PORT", "55432")
    db   = _env("PG_DB", "rey")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
