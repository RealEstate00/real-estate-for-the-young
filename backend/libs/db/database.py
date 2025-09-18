#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database service for housing data with JSONB support
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

from ..models.jsonb_models import ExtraAttrsBuilder, RawPayloadBuilder, JSONBValidator


class DatabaseService:
    """Database service for housing data operations"""
    
    def __init__(self, host: str = "localhost", port: int = 3306, 
                 user: str = "root", password: str = "", database: str = "SHA_bot"):
        self.connection_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": DictCursor
        }
    
    def get_connection(self):
        """Get database connection"""
        return pymysql.connect(**self.connection_params)
    
    def store_html(self, html_content: str, content_type: str = "text/html") -> str:
        """Store HTML content and return SHA256 hash"""
        html_bytes = html_content.encode('utf-8')
        html_sha256 = hashlib.sha256(html_bytes).hexdigest()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if already exists
                cursor.execute(
                    "SELECT html_sha256 FROM listing_html WHERE html_sha256 = %s",
                    (html_sha256,)
                )
                if cursor.fetchone():
                    return html_sha256
                
                # Insert new HTML
                cursor.execute("""
                    INSERT INTO listing_html (html_sha256, bytes, content_type, fetched_at)
                    VALUES (%s, %s, %s, %s)
                """, (html_sha256, html_bytes, content_type, datetime.now()))
                
                conn.commit()
                return html_sha256
    
    def store_listing(self, listing_data: Dict[str, Any], 
                     raw_payload: Dict[str, Any], 
                     extra_attrs: Dict[str, Any],
                     html_sha256: str = None) -> str:
        """Store listing with JSONB data"""
        
        # Validate JSONB data
        validator = JSONBValidator()
        extra_errors = validator.validate_extra_attrs(extra_attrs)
        raw_errors = validator.validate_raw_payload(raw_payload)
        
        if extra_errors:
            raise ValueError(f"extra_attrs validation errors: {extra_errors}")
        if raw_errors:
            raise ValueError(f"raw_payload validation errors: {raw_errors}")
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Generate listing_id if not provided
                listing_id = listing_data.get('listing_id')
                if not listing_id:
                    listing_id = hashlib.sha256(
                        f"{listing_data['platform']}|{listing_data.get('title', '')}|{datetime.now().isoformat()}"
                    ).hexdigest()
                
                # Insert listing
                cursor.execute("""
                    INSERT INTO listings (
                        listing_id, platform, category, title, status, housing_type,
                        project_name, address_full, city, district, subway_lines,
                        deposit_won, rent_won, supply_total_units, public_units, private_units,
                        area_m2_min, area_m2_max, announce_date, deadline_date,
                        detail_url, list_url, raw_payload, extra_attrs, html_sha256,
                        source_id, region_id, location, crawled_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        title = VALUES(title),
                        status = VALUES(status),
                        housing_type = VALUES(housing_type),
                        project_name = VALUES(project_name),
                        address_full = VALUES(address_full),
                        city = VALUES(city),
                        district = VALUES(district),
                        subway_lines = VALUES(subway_lines),
                        deposit_won = VALUES(deposit_won),
                        rent_won = VALUES(rent_won),
                        supply_total_units = VALUES(supply_total_units),
                        public_units = VALUES(public_units),
                        private_units = VALUES(private_units),
                        area_m2_min = VALUES(area_m2_min),
                        area_m2_max = VALUES(area_m2_max),
                        announce_date = VALUES(announce_date),
                        deadline_date = VALUES(deadline_date),
                        detail_url = VALUES(detail_url),
                        list_url = VALUES(list_url),
                        raw_payload = VALUES(raw_payload),
                        extra_attrs = VALUES(extra_attrs),
                        html_sha256 = VALUES(html_sha256),
                        crawled_at = VALUES(crawled_at)
                """, (
                    listing_id,
                    listing_data.get('platform'),
                    listing_data.get('category'),
                    listing_data.get('title'),
                    listing_data.get('status'),
                    listing_data.get('housing_type'),
                    listing_data.get('project_name'),
                    listing_data.get('address_full'),
                    listing_data.get('city'),
                    listing_data.get('district'),
                    listing_data.get('subway_lines'),
                    listing_data.get('deposit_won'),
                    listing_data.get('rent_won'),
                    listing_data.get('supply_total_units'),
                    listing_data.get('public_units'),
                    listing_data.get('private_units'),
                    listing_data.get('area_m2_min'),
                    listing_data.get('area_m2_max'),
                    listing_data.get('announce_date'),
                    listing_data.get('deadline_date'),
                    listing_data.get('detail_url'),
                    listing_data.get('list_url'),
                    json.dumps(raw_payload, ensure_ascii=False),
                    json.dumps(extra_attrs, ensure_ascii=False),
                    html_sha256,
                    listing_data.get('source_id'),
                    listing_data.get('region_id'),
                    listing_data.get('location'),
                    listing_data.get('crawled_at', datetime.now())
                ))
                
                conn.commit()
                return listing_id
    
    def store_attachment(self, listing_id: str, file_path: str, 
                        file_name: str, mime_type: str, file_size: int) -> int:
        """Store attachment metadata"""
        file_sha256 = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO attachments (listing_id, file_name, stored_path, mime, bytes, file_sha256)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (listing_id, file_name, file_path, mime_type, file_size, file_sha256))
                
                conn.commit()
                return cursor.lastrowid
    
    def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing by ID with JSONB data"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT *, 
                           JSON_EXTRACT(raw_payload, '$') as raw_payload_json,
                           JSON_EXTRACT(extra_attrs, '$') as extra_attrs_json
                    FROM listings 
                    WHERE listing_id = %s
                """, (listing_id,))
                
                result = cursor.fetchone()
                if result:
                    # Parse JSONB fields
                    result['raw_payload'] = json.loads(result['raw_payload_json']) if result['raw_payload_json'] else None
                    result['extra_attrs'] = json.loads(result['extra_attrs_json']) if result['extra_attrs_json'] else None
                    del result['raw_payload_json']
                    del result['extra_attrs_json']
                
                return result
    
    def search_listings(self, filters: Dict[str, Any] = None, 
                       limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Search listings with JSONB filters"""
        where_conditions = []
        params = []
        
        if filters:
            # Standard column filters
            if 'platform' in filters:
                where_conditions.append("platform = %s")
                params.append(filters['platform'])
            
            if 'city' in filters:
                where_conditions.append("city = %s")
                params.append(filters['city'])
            
            if 'district' in filters:
                where_conditions.append("district = %s")
                params.append(filters['district'])
            
            # JSONB filters
            if 'min_room_count' in filters:
                where_conditions.append("CAST(extra_attrs->>'room_count' AS UNSIGNED) >= %s")
                params.append(filters['min_room_count'])
            
            if 'max_room_count' in filters:
                where_conditions.append("CAST(extra_attrs->>'room_count' AS UNSIGNED) <= %s")
                params.append(filters['max_room_count'])
            
            if 'pet_ok' in filters:
                where_conditions.append("CAST(extra_attrs->>'pet_ok' AS BOOLEAN) = %s")
                params.append(filters['pet_ok'])
            
            if 'heating_type' in filters:
                where_conditions.append("extra_attrs->>'heating_type' = %s")
                params.append(filters['heating_type'])
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT *, 
                           JSON_EXTRACT(raw_payload, '$') as raw_payload_json,
                           JSON_EXTRACT(extra_attrs, '$') as extra_attrs_json
                    FROM listings 
                    WHERE {where_clause}
                    ORDER BY crawled_at DESC
                    LIMIT %s OFFSET %s
                """, params + [limit, offset])
                
                results = cursor.fetchall()
                
                # Parse JSONB fields
                for result in results:
                    result['raw_payload'] = json.loads(result['raw_payload_json']) if result['raw_payload_json'] else None
                    result['extra_attrs'] = json.loads(result['extra_attrs_json']) if result['extra_attrs_json'] else None
                    del result['raw_payload_json']
                    del result['extra_attrs_json']
                
                return results
    
    def get_html_content(self, html_sha256: str) -> Optional[bytes]:
        """Get HTML content by SHA256"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT bytes FROM listing_html WHERE html_sha256 = %s
                """, (html_sha256,))
                
                result = cursor.fetchone()
                return result['bytes'] if result else None
    
    def migrate_existing_data(self):
        """Migrate existing data to new JSONB structure"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get all existing listings
                cursor.execute("SELECT * FROM listings WHERE raw_payload IS NULL")
                listings = cursor.fetchall()
                
                for listing in listings:
                    # Create basic extra_attrs
                    builder = ExtraAttrsBuilder(listing['platform'], "v1")
                    
                    # Add basic info if available
                    if listing.get('area_m2_min'):
                        builder.add_room_count(int(listing['area_m2_min'] / 30))  # Rough estimate
                    
                    extra_attrs = builder.build()
                    
                    # Create basic raw_payload
                    raw_payload = RawPayloadBuilder(
                        listing.get('detail_url', ''),
                        "v1"
                    ).add_original_data({
                        "title": listing.get('title'),
                        "address": listing.get('address_full'),
                        "platform": listing.get('platform')
                    }).build()
                    
                    # Update the listing
                    cursor.execute("""
                        UPDATE listings 
                        SET raw_payload = %s, extra_attrs = %s
                        WHERE listing_id = %s
                    """, (
                        json.dumps(raw_payload, ensure_ascii=False),
                        json.dumps(extra_attrs, ensure_ascii=False),
                        listing['listing_id']
                    ))
                
                conn.commit()
                print(f"Migrated {len(listings)} listings to new JSONB structure")
