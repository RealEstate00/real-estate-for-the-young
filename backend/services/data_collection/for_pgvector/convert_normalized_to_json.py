"""
정규화된 TXT 파일을 JSON으로 변환하는 스크립트
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


def txt_to_json(input_txt: str, output_json: str, category: str = "신혼부부 임차보증금 지원"):
    """
    정규화된 TXT를 JSON으로 변환

    TXT 형식:
    - 홀수 줄 (1, 3, 5...): 질문
    - 빈 줄
    - 짝수 줄 (3, 5, 7...): 답변
    - 빈 줄
    """

    with open(input_txt, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    qa_list = []
    i = 0
    page_number = 1

    while i < len(lines):
        line = lines[i].strip()

        # 빈 줄 스킵
        if not line:
            i += 1
            continue

        # 질문으로 간주 (물음표로 끝나는 줄)
        if '?' in line:
            question = line.strip()
            i += 1

            # 다음 빈 줄 스킵
            while i < len(lines) and not lines[i].strip():
                i += 1

            # 답변 읽기
            if i < len(lines):
                answer = lines[i].strip()
                i += 1

                # QA 추가
                qa_list.append({
                    "question": question,
                    "answer": answer,
                    "category": category,
                    "page_number": page_number,
                    "metadata": {
                        "source": "서울시 신혼부부 임차보증금 지원 FAQ",
                        "document_type": "FAQ",
                        "language": "ko"
                    }
                })

                # 페이지 번호 추정 (대략 10개 질문당 1페이지)
                if len(qa_list) % 10 == 0:
                    page_number += 1
            else:
                i += 1
        else:
            # 질문이 아니면 스킵 (헤더 등)
            i += 1

    # JSON 저장
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(qa_list, f, ensure_ascii=False, indent=2)

    print(f"[OK] 변환 완료: {output_json}")
    print(f"     총 {len(qa_list)}개의 QA 쌍")

    return qa_list


def print_samples(qa_list: List[Dict], num_samples: int = 5):
    """샘플 출력"""
    print("\n" + "="*80)
    print(f"샘플 {min(num_samples, len(qa_list))}개")
    print("="*80)

    for i, qa in enumerate(qa_list[:num_samples], 1):
        print(f"\n[QA {i}]")
        print(f"질문: {qa['question']}")
        answer = qa['answer'][:150] + '...' if len(qa['answer']) > 150 else qa['answer']
        print(f"답변: {answer}")


def main():
    """메인 실행"""
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent.parent

    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'pre_normalize' / '신혼부부 사업FAQ_normalized.txt'
    output_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'pre_normalize' / '신혼부부 사업FAQ_normalized.json'

    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}\n")

    if not input_file.exists():
        print(f"[ERROR] 파일이 존재하지 않습니다: {input_file}")
        return

    # 변환
    qa_list = txt_to_json(str(input_file), str(output_file))

    # 샘플 출력
    print_samples(qa_list)

    print("\n[SUCCESS] 모든 작업 완료!")


if __name__ == "__main__":
    main()
