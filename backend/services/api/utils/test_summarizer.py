"""
mT5-base 요약 기능 테스트 스크립트
요약이 제대로 작동하는지 점검
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from backend.services.api.utils.summarizer import summarize_title, summarize_conversation_batch
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_title_summarizer():
    """제목 요약 기능 테스트"""
    print("=" * 60)
    print("1. mT5-base 제목 요약 테스트")
    print("=" * 60)
    
    # 테스트 텍스트 (실제 LLM 응답 예시)
    test_text = """버팀목전세자금 전세 대출 안내 (송파구 30세 여성) 안녕하세요. 송파구에 거주하시는 30세 여성분의 전세 대출에 대한 안내입니다. 버팀목전세자금 대출에 대한 정보를 아래와 같이 정리했습니다.

1. 신청 자격
* 세대주 조건: 민법상 성년자인 세대주로서 대출 신청일 현재 세대주여야 합니다.
* 무주택 세대주 조건: 세대주를 포함한 모든 세대원이 무주택이어야 합니다.
* 소득 조건: 부부 연간소득 합계가 5,000만원 이하이어야 합니다.
* 순자산 요건: 순자산액이 3억 3,700만원 이하여야 합니다.

2. 대출 조건
* 대출 한도: 전세보증금의 80% 이내
* 대출 금리: 연 2.5% (고정금리)
* 상환 기간: 최대 20년"""
    
    print(f"\n입력 텍스트 길이: {len(test_text)}자")
    print(f"입력 텍스트 일부:\n{test_text[:100]}...\n")
    
    try:
        print("제목 요약 시작...")
        result = summarize_title(test_text, max_length=25)
        
        print("\n" + "=" * 60)
        print("✅ 제목 요약 결과")
        print("=" * 60)
        print(f"제목: '{result}'")
        print(f"길이: {len(result)}자")
        print(f"25자 기준: {'✅ 적절' if len(result) <= 25 else '⚠️ 초과'}")
        
        if len(result) > 25:
            print(f"\n⚠️ 경고: 제목이 25자를 초과합니다 ({len(result)}자)")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_conversation_summarizer():
    """대화 배치 요약 기능 테스트"""
    print("\n" + "=" * 60)
    print("2. mT5-base 대화 배치 요약 테스트")
    print("=" * 60)
    
    # 테스트 메시지들 (실제 대화 예시)
    test_messages = [
        {
            "role": "user",
            "content": "안녕하세요. 저는 송파구에 거주중인 30살 여성입니다. 전세 대출금에 대해 알고 싶어요."
        },
        {
            "role": "assistant",
            "content": """안녕하세요. 송파구에 거주하시는 30세 여성분의 전세 대출에 대한 안내입니다.

1. 신청 자격
* 세대주 조건: 민법상 성년자인 세대주로서 대출 신청일 현재 세대주여야 합니다.
* 무주택 세대주 조건: 세대주를 포함한 모든 세대원이 무주택이어야 합니다.
* 소득 조건: 부부 연간소득 합계가 5,000만원 이하이어야 합니다.

2. 대출 조건
* 대출 한도: 전세보증금의 80% 이내
* 대출 금리: 연 2.5% (고정금리)
* 상환 기간: 최대 20년"""
        },
        {
            "role": "user",
            "content": "대출 한도는 얼마인가요?"
        },
        {
            "role": "assistant",
            "content": "버팀목전세자금 대출 한도는 전세보증금의 80% 이내입니다. 예를 들어 전세보증금이 3억원이면 최대 2억 4천만원까지 대출 가능합니다."
        },
        {
            "role": "user",
            "content": "금리는 어떻게 되나요?"
        },
        {
            "role": "assistant",
            "content": "버팀목전세자금 대출 금리는 연 2.5%의 고정금리입니다. 변동금리와 달리 대출 기간 동안 금리가 변동하지 않아 안정적입니다."
        }
    ]
    
    print(f"\n테스트 메시지 개수: {len(test_messages)}개")
    print("테스트 메시지 일부:")
    for i, msg in enumerate(test_messages[:2], 1):
        print(f"  {i}. [{msg['role']}] {msg['content'][:50]}...")
    
    try:
        print("\n대화 요약 시작...")
        result = summarize_conversation_batch(test_messages)
        
        print("\n" + "=" * 60)
        print("✅ 대화 요약 결과")
        print("=" * 60)
        print(f"요약: '{result}'")
        print(f"길이: {len(result)}자")
        print(f"3-5문장 기준: {'✅ 적절' if 50 <= len(result) <= 300 else '⚠️ 확인 필요'}")
        
        # 핵심 정보 확인
        keywords = ["송파구", "30세", "여성", "전세", "대출"]
        found_keywords = [kw for kw in keywords if kw in result]
        print(f"\n핵심 정보 포함 여부:")
        print(f"  발견된 키워드: {found_keywords if found_keywords else '없음'}")
        print(f"  포함률: {len(found_keywords)}/{len(keywords)} ({len(found_keywords)/len(keywords)*100:.0f}%)")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_summarizer():
    """모든 요약 기능 테스트"""
    print("\n" + "=" * 60)
    print("허깅페이스 mT5-base 요약 LLM 점검")
    print("=" * 60)
    
    # 1. 제목 요약 테스트
    title_result = test_title_summarizer()
    
    # 2. 대화 배치 요약 테스트
    conversation_result = test_conversation_summarizer()
    
    # 최종 결과
    print("\n" + "=" * 60)
    print("최종 점검 결과")
    print("=" * 60)
    print(f"1. 제목 요약: {'✅ 성공' if title_result else '❌ 실패'}")
    print(f"2. 대화 요약: {'✅ 성공' if conversation_result else '❌ 실패'}")
    
    if title_result and conversation_result:
        print("\n✅ 모든 요약 기능이 정상 작동 중입니다!")
    else:
        print("\n❌ 일부 요약 기능에 문제가 있습니다. 위의 오류 메시지를 확인하세요.")
    
    return title_result is not None and conversation_result is not None

if __name__ == "__main__":
    test_summarizer()
