#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAQ 청크 생성 스크립트
물음표 기준으로 3개씩 Q&A 쌍을 묶어서 청크로 생성

원본 PDF 파일: (붙임1)신혼부부 사업 FAQ.pdf
입력: 신혼부부 사업FAQ_normalized.txt
"""

import re
import json
from pathlib import Path


def chunk_faq(input_file: str, output_file: str, chunk_size: int = 3):
    """
    노말라이징된 FAQ 파일을 청크로 나눕니다.

    Args:
        input_file: 노말라이징된 FAQ 파일 경로
        output_file: 청크 결과 저장 파일 경로
        chunk_size: 한 청크당 Q&A 쌍 개수 (기본값: 3)
    """

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 전체 텍스트를 물음표로 분리
    parts = re.split(r'(\?)', content)

    qa_pairs = []
    i = 0

    while i < len(parts):
        if i + 1 < len(parts) and parts[i + 1] == '?':
            # 질문 찾기
            question_text = parts[i].strip()

            # 질문의 시작점 찾기 (마지막 줄바꿈 또는 마침표/괄호 이후)
            last_break_idx = -1
            for idx in range(len(question_text) - 1, -1, -1):
                char = question_text[idx]
                if char == '\n':
                    last_break_idx = idx
                    break
                elif char in '.)':
                    # 다음 문자가 공백이나 한글이면 문장 끝
                    if idx + 1 < len(question_text):
                        next_char = question_text[idx + 1]
                        if next_char in ' \n' or (next_char >= '가' and next_char <= '힣'):
                            last_break_idx = idx
                            break

            question = question_text[last_break_idx + 1:].strip() + '?'

            # 답변 찾기 (다음 질문 전까지 전체)
            i += 2
            answer = ''
            if i < len(parts):
                answer_text = parts[i].strip()

                # 답변에서 다음 질문 제거
                # 답변은 마침표(.) 또는 괄호())로 끝나야 함
                # 그 이후에 나오는 텍스트는 다음 질문임

                # 마지막 마침표 또는 괄호 위치 찾기
                last_end_pos = -1
                i_char = 0
                while i_char < len(answer_text):
                    char = answer_text[i_char]

                    if char == '.':
                        # 마침표 뒤에 공백이나 줄바꿈 또는 한글이 오면 문장 끝
                        if i_char + 1 < len(answer_text):
                            next_char = answer_text[i_char + 1]
                            if next_char in ' \n' or (next_char >= '가' and next_char <= '힣'):
                                last_end_pos = i_char
                        else:
                            last_end_pos = i_char

                    elif char == ')':
                        # 괄호는 앞에 숫자가 없고, 뒤에 공백/줄바꿈/한글이 올 때만 문장 끝
                        # 숫자) 는 목록 번호이므로 제외
                        if i_char > 0:
                            prev_char = answer_text[i_char - 1]
                            if not prev_char.isdigit():  # 숫자가 아닐 때만
                                if i_char + 1 < len(answer_text):
                                    next_char = answer_text[i_char + 1]
                                    if next_char in ' \n' or (next_char >= '가' and next_char <= '힣'):
                                        last_end_pos = i_char
                                else:
                                    last_end_pos = i_char

                    i_char += 1

                if last_end_pos >= 0:
                    answer = answer_text[:last_end_pos + 1].strip()
                else:
                    answer = answer_text.strip()

            if question.replace('?', '').strip():
                qa_pairs.append({
                    'question': question,
                    'answer': answer
                })
        else:
            i += 1

    print(f"총 {len(qa_pairs)}개의 Q&A 쌍을 추출했습니다.")

    # 청크로 나누기
    chunks = []
    for i in range(0, len(qa_pairs), chunk_size):
        chunk_qa_pairs = qa_pairs[i:i + chunk_size]

        # 청크 텍스트 생성
        chunk_text = ""
        for qa in chunk_qa_pairs:
            chunk_text += qa['question'] + "\n"
            if qa['answer']:
                chunk_text += qa['answer'] + "\n"
            chunk_text += "\n"

        chunks.append({
            'chunk_id': len(chunks) + 1,
            'qa_count': len(chunk_qa_pairs),
            'text': chunk_text.strip()
        })

    print(f"총 {len(chunks)}개의 청크를 생성했습니다.")

    # 결과 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(f"=== 청크 {chunk['chunk_id']} (Q&A 쌍: {chunk['qa_count']}개) ===\n")
            f.write(chunk['text'])
            f.write("\n\n" + "="*80 + "\n\n")

    print(f"청크 파일 저장 완료: {output_file}")

    # JSON 파일 생성
    json_output_file = output_file.replace('_chunked.txt', '_chunked.json')
    json_data = []

    for chunk in chunks:
        json_data.append({
            'chunk_id': chunk['chunk_id'],
            'content': chunk['text'],
            'metadata': {
                'source': '서울시 신혼부부 임차보증금 지원 FAQ',
                'document_type': 'FAQ'
            }
        })

    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"JSON 파일 저장 완료: {json_output_file}")

    # 통계 출력
    print(f"\n[통계]")
    print(f"- 총 Q&A 쌍: {len(qa_pairs)}개")
    print(f"- 총 청크: {len(chunks)}개")
    print(f"- 청크당 Q&A 쌍: {chunk_size}개")
    print(f"- 마지막 청크 Q&A 쌍: {chunks[-1]['qa_count']}개")


if __name__ == '__main__':
    # 경로 설정
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent.parent
    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '신혼부부 사업FAQ_normalized.txt'
    output_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '신혼부부 사업FAQ_chunked.txt'

    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print(f"입력 파일 존재: {input_file.exists()}\n")

    chunk_faq(str(input_file), str(output_file), chunk_size=3)
