"""
출력 파서
구조화된 JSON 출력을 위한 Pydantic 파서
"""

from typing import List, Dict, Optional
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


# 개별 주택 추천 모델
class HousingItem(BaseModel):
    """개별 주택 정보 - 모든 상세 정보 포함"""
    housing_name: str = Field(description="주택명")
    address_road: str = Field(description="도로명주소")
    address_jibun: Optional[str] = Field(default=None, description="지번주소")
    district: str = Field(description="시군구")
    dong: str = Field(description="동명")
    subway: Optional[str] = Field(default=None, description="가까운 지하철역")
    theme: Optional[str] = Field(default=None, description="테마 (청년, 신혼, 육아 등)")
    requirements: Optional[str] = Field(default=None, description="자격요건")
    nearby_facilities: Optional[str] = Field(default=None, description="주변 편의시설 (마트, 병원, 학교 등)")
    reason: str = Field(description="추천 이유 - 사용자 조건에 맞는 이유 설명")


# 전체 추천 응답 모델
class HousingRecommendation(BaseModel):
    """주택 추천 응답 구조"""
    understanding: str = Field(
        description="사용자 상황 이해 - 사용자가 찾는 주택의 조건을 한 문장으로 요약"
    )
    recommendations: List[HousingItem] = Field(
        description="추천 주택 목록 - 검색된 주택의 모든 정보 포함 (최대 5개)",
        max_items=5
    )
    summary: str = Field(
        description="전체 요약 - 추천 주택들의 공통점이나 특징을 간략히 정리"
    )
    additional_tips: Optional[str] = Field(
        default=None,
        description="추가 팁 - 신청 방법, 주의사항, 문의처 등"
    )


# Pydantic 파서 생성
output_parser = PydanticOutputParser(pydantic_object=HousingRecommendation)


# 파서 지시문 (프롬프트에 추가할 포맷 설명)
def get_format_instructions() -> str:
    """파서의 포맷 지시문 반환"""
    return output_parser.get_format_instructions()


# 간단한 문자열 파서 (대안)
from langchain.schema.output_parser import StrOutputParser

simple_parser = StrOutputParser()


# 테스트용 함수
def test_parser():
    """파서 테스트"""
    # 테스트 JSON 응답
    test_response = """{
    "understanding": "사용자는 강남 지역의 청년 주택을 찾고 계십니다.",
    "recommendations": [
        {
            "housing_name": "역삼 청년주택",
            "address_road": "서울특별시 강남구 테헤란로 123",
            "address_jibun": "서울특별시 강남구 역삼동 456-78",
            "district": "강남구",
            "dong": "역삼동",
            "subway": "2호선 강남역",
            "theme": "청년",
            "requirements": "만 19-39세 무주택자",
            "nearby_facilities": "마트: 이마트, 병원: 강남세브란스병원, 학교: 역삼초등학교",
            "reason": "지하철 2호선 강남역에서 도보 5분으로 교통이 편리하고, 청년 특화 주택으로 다양한 커뮤니티 프로그램이 있습니다"
        }
    ],
    "summary": "강남역 인근의 교통 편리한 청년 주택입니다.",
    "additional_tips": "신청은 공식 홈페이지에서 가능하며, 소득 제한이 있을 수 있습니다."
}"""
    
    try:
        parsed = output_parser.parse(test_response)
        print("=" * 80)
        print("Parser Test - Parsed Object:")
        print("=" * 80)
        print(f"Understanding: {parsed.understanding}")
        print(f"\nRecommendations ({len(parsed.recommendations)}):")
        for i, rec in enumerate(parsed.recommendations, 1):
            print(f"\n  {i}. {rec.housing_name}")
            print(f"     📍 주소: {rec.address_road}")
            print(f"     🏘️  지역: {rec.district} {rec.dong}")
            print(f"     🚇 지하철: {rec.subway or 'N/A'}")
            print(f"     🏷️  테마: {rec.theme or 'N/A'}")
            print(f"     ✅ 자격요건: {rec.requirements or 'N/A'}")
            print(f"     🏪 주변시설: {rec.nearby_facilities or 'N/A'}")
            print(f"     💡 추천이유: {rec.reason}")
        print(f"\n📊 전체 요약: {parsed.summary}")
        if parsed.additional_tips:
            print(f"💬 추가 팁: {parsed.additional_tips}")
        print("=" * 80)
        return True
    except Exception as e:
        print(f"Parser Test Failed: {e}")
        return False


# 포맷 지시문 출력
def print_format_instructions():
    """파서의 포맷 지시문 출력"""
    instructions = get_format_instructions()
    print("=" * 80)
    print("Format Instructions (프롬프트에 추가할 내용):")
    print("=" * 80)
    print(instructions)
    print("=" * 80)




