"""
출력 파서
구조화된 JSON 출력을 위한 Pydantic 파서
"""

from typing import List, Dict, Optional
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


# 개별 주택 추천 모델
class HousingItem(BaseModel):
    """개별 주택 정보"""
    housing_name: str = Field(description="주택명")
    location: str = Field(description="위치 (시군구 + 동)")
    reason: str = Field(description="추천 이유")
    features: Optional[str] = Field(default=None, description="주요 특징")


# 전체 추천 응답 모델
class HousingRecommendation(BaseModel):
    """주택 추천 응답 구조"""
    understanding: str = Field(
        description="사용자 상황 이해 - 사용자가 찾는 주택의 조건을 간단히 요약"
    )
    recommendations: List[HousingItem] = Field(
        description="추천 주택 목록 (최대 3개)",
        max_items=3
    )
    additional_info: str = Field(
        description="추가 정보 - 교통, 편의시설, 신청 방법 등"
    )
    confidence: Optional[str] = Field(
        default="검색된 정보 기반",
        description="답변의 신뢰도 또는 출처"
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
            "location": "강남구 역삼동",
            "reason": "지하철 2호선 강남역에서 도보 5분으로 교통이 편리합니다",
            "features": "청년 특화 주택, 현대적 시설"
        }
    ],
    "additional_info": "지하철 2호선 강남역 근처로 교통이 매우 편리하며, 주변에 다양한 편의시설이 있습니다. 자세한 신청 자격은 공식 홈페이지를 참고하세요.",
    "confidence": "검색된 정보 기반"
}"""
    
    try:
        parsed = output_parser.parse(test_response)
        print("=" * 80)
        print("Parser Test - Parsed Object:")
        print("=" * 80)
        print(f"Understanding: {parsed.understanding}")
        print(f"\nRecommendations ({len(parsed.recommendations)}):")
        for i, rec in enumerate(parsed.recommendations, 1):
            print(f"  {i}. {rec.housing_name}")
            print(f"     위치: {rec.location}")
            print(f"     이유: {rec.reason}")
        print(f"\nAdditional Info: {parsed.additional_info}")
        print(f"Confidence: {parsed.confidence}")
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




