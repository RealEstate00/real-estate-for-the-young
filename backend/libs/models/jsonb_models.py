#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSONB data models and validation for housing data
Following the two-lane approach: raw_payload + extra_attrs
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json


@dataclass
class MetaInfo:
    """Standard metadata for extra_attrs"""
    source: str
    schema: str
    fetched_at: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "source": self.source,
            "schema": self.schema,
            "fetched_at": self.fetched_at
        }


class ExtraAttrsBuilder:
    """Builder for curated extra_attrs JSONB data"""
    
    def __init__(self, platform: str, schema_version: str = "v1"):
        self.data = {}
        self.meta = MetaInfo(
            source=platform,
            schema=schema_version,
            fetched_at=datetime.now().isoformat()
        )
    
    def add_room_count(self, count: int) -> 'ExtraAttrsBuilder':
        """Add room count (0-20)"""
        if 0 <= count <= 20:
            self.data['room_count'] = count
        return self
    
    def add_floor(self, floor: int) -> 'ExtraAttrsBuilder':
        """Add floor number (-5 to 100)"""
        if -5 <= floor <= 100:
            self.data['floor'] = floor
        return self
    
    def add_heating_type(self, heating_type: str) -> 'ExtraAttrsBuilder':
        """Add heating type (standardized)"""
        valid_types = ['central', 'individual', 'district', 'gas', 'electric', 'oil']
        if heating_type in valid_types:
            self.data['heating_type'] = heating_type
        return self
    
    def add_pet_ok(self, pet_ok: bool) -> 'ExtraAttrsBuilder':
        """Add pet allowance"""
        self.data['pet_ok'] = pet_ok
        return self
    
    def add_move_in_date(self, date_str: str) -> 'ExtraAttrsBuilder':
        """Add move-in date (ISO format)"""
        try:
            # Validate ISO date format
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            self.data['move_in_date'] = date_str
        except ValueError:
            pass
        return self
    
    def add_distance_subway(self, distance_m: int) -> 'ExtraAttrsBuilder':
        """Add distance to subway in meters"""
        if 0 <= distance_m <= 10000:  # Max 10km
            self.data['distance_subway_m'] = distance_m
        return self
    
    def add_amenities(self, amenities: List[str]) -> 'ExtraAttrsBuilder':
        """Add amenities list"""
        valid_amenities = [
            'laundry_room', 'bike_storage', 'parking', 'elevator', 
            'security', 'gym', 'rooftop', 'garden', 'concierge'
        ]
        filtered = [a for a in amenities if a in valid_amenities]
        if filtered:
            self.data['amenities'] = filtered
        return self
    
    def add_platform_specific(self, key: str, value: Any) -> 'ExtraAttrsBuilder':
        """Add platform-specific field with prefix"""
        if not key.startswith('_'):
            prefixed_key = f"{self.meta.source}_{key}"
            self.data[prefixed_key] = value
        return self
    
    def add_has_elevator(self, has_elevator: bool) -> 'ExtraAttrsBuilder':
        """Add elevator availability"""
        self.data['has_elevator'] = has_elevator
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build final extra_attrs JSONB object"""
        result = self.data.copy()
        result['_meta'] = self.meta.to_dict()
        return result


class SocialHousingExtraAttrsBuilder:
    """Builder for social/community housing specific extra_attrs JSONB data"""
    
    def __init__(self, platform: str, schema_version: str = "v1"):
        self.data = {}
        self.meta = MetaInfo(
            source=platform,
            schema=schema_version,
            fetched_at=datetime.now().isoformat()
        )
    
    def add_building_details(self, district_type: str = None, building_scale: str = None, 
                           building_structure: str = None, site_area: str = None, 
                           total_floor_area: str = None, approval_date: str = None) -> 'SocialHousingExtraAttrsBuilder':
        """Add building detail information"""
        building_info = {}
        if district_type:
            building_info['district_type'] = district_type
        if building_scale:
            building_info['building_scale'] = building_scale
        if building_structure:
            building_info['building_structure'] = building_structure
        if site_area:
            building_info['site_area'] = site_area
        if total_floor_area:
            building_info['total_floor_area'] = total_floor_area
        if approval_date:
            building_info['approval_date'] = approval_date
        
        if building_info:
            self.data['building_details'] = building_info
        return self
    
    def add_facilities(self, subway_station: str = None, bus_info: str = None, 
                      nearby_mart: str = None, nearby_hospital: str = None, 
                      nearby_school: str = None, nearby_facilities: str = None, 
                      nearby_cafe: str = None) -> 'SocialHousingExtraAttrsBuilder':
        """Add facility and transportation information"""
        facilities = {}
        if subway_station:
            facilities['subway_station'] = subway_station
        if bus_info:
            facilities['bus_info'] = bus_info
        if nearby_mart:
            facilities['nearby_mart'] = nearby_mart
        if nearby_hospital:
            facilities['nearby_hospital'] = nearby_hospital
        if nearby_school:
            facilities['nearby_school'] = nearby_school
        if nearby_facilities:
            facilities['nearby_facilities'] = nearby_facilities
        if nearby_cafe:
            facilities['nearby_cafe'] = nearby_cafe
        
        if facilities:
            self.data['facilities'] = facilities
        return self
    
    def add_company_info(self, company_name: str = None, representative: str = None, 
                        contact_phone: str = None, homepage: str = None) -> 'SocialHousingExtraAttrsBuilder':
        """Add company/operator information"""
        company_info = {}
        if company_name:
            company_info['company_name'] = company_name
        if representative:
            company_info['representative'] = representative
        if contact_phone:
            company_info['contact_phone'] = contact_phone
        if homepage:
            company_info['homepage'] = homepage
        
        if company_info:
            self.data['company_info'] = company_info
        return self
    
    def add_housing_specific(self, deposit_range: str = None, monthly_rent_range: str = None,
                           target_occupancy_detail: str = None, housing_features: str = None) -> 'SocialHousingExtraAttrsBuilder':
        """Add housing-specific information"""
        housing_info = {}
        if deposit_range:
            housing_info['deposit_range'] = deposit_range
        if monthly_rent_range:
            housing_info['monthly_rent_range'] = monthly_rent_range
        if target_occupancy_detail:
            housing_info['target_occupancy_detail'] = target_occupancy_detail
        if housing_features:
            housing_info['housing_features'] = housing_features
        
        if housing_info:
            self.data['housing_specific'] = housing_info
        return self
    
    def add_platform_specific(self, key: str, value: Any) -> 'SocialHousingExtraAttrsBuilder':
        """Add platform-specific field with prefix"""
        if not key.startswith('_'):
            prefixed_key = f"{self.meta.source}_{key}"
            self.data[prefixed_key] = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build final extra_attrs JSONB object"""
        result = self.data.copy()
        result['_meta'] = self.meta.to_dict()
        return result


class RawPayloadBuilder:
    """Builder for raw_payload JSONB data (original snapshot)"""
    
    def __init__(self, url: str, parser_version: str = "v1"):
        self.data = {
            "_meta": {
                "url": url,
                "parser": parser_version,
                "fetched_at": datetime.now().isoformat()
            }
        }
    
    def add_api_response(self, response: Dict[str, Any]) -> 'RawPayloadBuilder':
        """Add original API response"""
        self.data['api_response'] = response
        return self
    
    def add_html_ref(self, html_sha256: str, store_path: str = None) -> 'RawPayloadBuilder':
        """Add HTML reference (not inline)"""
        self.data['html_ref'] = {
            "sha256": html_sha256,
            "store": store_path or f"s3://bucket/html/{html_sha256}"
        }
        return self
    
    def add_original_data(self, data: Dict[str, Any]) -> 'RawPayloadBuilder':
        """Add original structured data"""
        self.data['original_data'] = data
        return self
    
    def add_parsing_metadata(self, metadata: Dict[str, Any]) -> 'RawPayloadBuilder':
        """Add parsing metadata"""
        self.data['parsing_metadata'] = metadata
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build final raw_payload JSONB object"""
        return self.data


class JSONBValidator:
    """Validator for JSONB data integrity"""
    
    @staticmethod
    def validate_extra_attrs(data: Dict[str, Any]) -> List[str]:
        """Validate extra_attrs structure and return errors"""
        errors = []
        
        # Check required _meta
        if '_meta' not in data:
            errors.append("Missing required _meta field")
        else:
            meta = data['_meta']
            required_meta = ['source', 'schema', 'fetched_at']
            for field in required_meta:
                if field not in meta:
                    errors.append(f"Missing required _meta.{field}")
        
        # Validate room_count
        if 'room_count' in data:
            try:
                count = int(data['room_count'])
                if not (0 <= count <= 20):
                    errors.append("room_count must be between 0 and 20")
            except (ValueError, TypeError):
                errors.append("room_count must be an integer")
        
        # Validate floor
        if 'floor' in data:
            try:
                floor = int(data['floor'])
                if not (-5 <= floor <= 100):
                    errors.append("floor must be between -5 and 100")
            except (ValueError, TypeError):
                errors.append("floor must be an integer")
        
        # Validate pet_ok
        if 'pet_ok' in data and not isinstance(data['pet_ok'], bool):
            errors.append("pet_ok must be a boolean")
        
        # Validate move_in_date
        if 'move_in_date' in data:
            try:
                datetime.fromisoformat(data['move_in_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                errors.append("move_in_date must be valid ISO date")
        
        # Validate amenities
        if 'amenities' in data:
            if not isinstance(data['amenities'], list):
                errors.append("amenities must be a list")
            else:
                valid_amenities = [
                    'laundry_room', 'bike_storage', 'parking', 'elevator', 
                    'security', 'gym', 'rooftop', 'garden', 'concierge'
                ]
                for amenity in data['amenities']:
                    if not isinstance(amenity, str) or amenity not in valid_amenities:
                        errors.append(f"Invalid amenity: {amenity}")
        
        return errors
    
    @staticmethod
    def validate_raw_payload(data: Dict[str, Any]) -> List[str]:
        """Validate raw_payload structure and return errors"""
        errors = []
        
        # Check required _meta
        if '_meta' not in data:
            errors.append("Missing required _meta field")
        else:
            meta = data['_meta']
            required_meta = ['url', 'parser', 'fetched_at']
            for field in required_meta:
                if field not in meta:
                    errors.append(f"Missing required _meta.{field}")
        
        return errors


# Example usage and factory functions
def create_sohouse_extra_attrs(platform_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create extra_attrs for sohouse platform"""
    builder = ExtraAttrsBuilder("sohouse", "v1")
    
    # Extract and normalize data
    if 'room_count' in platform_data:
        builder.add_room_count(int(platform_data['room_count']))
    
    if 'floor' in platform_data:
        builder.add_floor(int(platform_data['floor']))
    
    if 'heating_type' in platform_data:
        builder.add_heating_type(platform_data['heating_type'])
    
    if 'pet_ok' in platform_data:
        builder.add_pet_ok(bool(platform_data['pet_ok']))
    
    if 'move_in_date' in platform_data:
        builder.add_move_in_date(platform_data['move_in_date'])
    
    if 'amenities' in platform_data:
        builder.add_amenities(platform_data['amenities'])
    
    # Platform-specific fields
    if 'sohouse_notice_id' in platform_data:
        builder.add_platform_specific('notice_id', platform_data['sohouse_notice_id'])
    
    return builder.build()


def create_lh_extra_attrs(platform_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create extra_attrs for LH platform"""
    builder = ExtraAttrsBuilder("lh", "v1")
    
    # Extract and normalize data
    if 'room_count' in platform_data:
        builder.add_room_count(int(platform_data['room_count']))
    
    if 'floor' in platform_data:
        builder.add_floor(int(platform_data['floor']))
    
    if 'heating_type' in platform_data:
        builder.add_heating_type(platform_data['heating_type'])
    
    if 'pet_ok' in platform_data:
        builder.add_pet_ok(bool(platform_data['pet_ok']))
    
    # Platform-specific fields
    if 'lh_notice_type' in platform_data:
        builder.add_platform_specific('notice_type', platform_data['lh_notice_type'])
    
    if 'lh_application_period' in platform_data:
        builder.add_platform_specific('application_period', platform_data['lh_application_period'])
    
    return builder.build()


def create_raw_payload(url: str, original_data: Dict[str, Any], html_sha256: str = None) -> Dict[str, Any]:
    """Create raw_payload for any platform"""
    builder = RawPayloadBuilder(url, "v1")
    
    builder.add_original_data(original_data)
    
    if html_sha256:
        builder.add_html_ref(html_sha256)
    
    return builder.build()
