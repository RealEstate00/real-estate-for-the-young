#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAQ 파일을 질문-답변 한 줄 형식으로 재포맷하는 스크립트
"""

import re
from pathlib import Path


def reformat_qa(input_file: str, output_file: str):
    """
    FAQ 파일을 질문-답변 한 줄 형식으로 재포맷합니다.
    
    규칙:
    - 물음표로 끝나는 문장 = 질문
    - 그 다음 물음표가 포함된 문장이 나오기 전까지 = 답변
    - 질문과 답변을 한 줄로 표시
    - 각 질문-답변 쌍 사이는 한 줄 띄우기
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    # 줄 단위로 처리
    lines = [line.strip() for line in all_lines if line.strip()]
    
    # 전체 텍스트를 하나로 합치기
    full_text = ' '.join(lines)
    
    # 물음표 위치 찾기
    question_marks = [m.start() for m in re.finditer(r'\?', full_text)]
    
    qa_pairs = []
    
    for i, q_pos in enumerate(question_marks):
        # 질문 범위: 이전 답변의 끝부터 현재 물음표까지
        if i == 0:
            question_range = full_text[0:q_pos]
        else:
            prev_answer_end = question_marks[i - 1] + 1
            question_range = full_text[prev_answer_end:q_pos]
        
        # 질문 텍스트에서 마지막 문장 추출
        # 물음표 바로 앞의 문장을 찾기 위해 역순 검색
        # 문장 끝 패턴(. ? ! 뒤 공백) 찾기
        sentence_end_positions = list(re.finditer(r'[.!?]\s+', question_range))
        
        # 마지막 문장 추출
        if sentence_end_positions:
            # 마지막 문장 끝 이후부터가 질문
            last_match = sentence_end_positions[-1]
            last_end = last_match.end()
            question_text = question_range[last_end:].strip() + '?'
        else:
            # 문장 끝이 없으면 역순으로 단어 단위로 검색
            # 질문 키워드가 포함된 부분 찾기
            words = question_range.split()
            if len(words) > 0:
                # 마지막 몇 단어를 질문으로 추출 (질문 키워드 포함 여부 확인)
                question_keywords = ['어떻게', '무엇', '가능', '필요', '받', '하', '될', '인지', '있나', '되나']
                question_words = []
                for word in reversed(words):
                    question_words.insert(0, word)
                    # 질문 키워드가 포함되어 있고 충분한 길이면 중단
                    if any(kw in ' '.join(question_words) for kw in question_keywords) and len(question_words) >= 3:
                        break
                    # 최대 10단어까지
                    if len(question_words) >= 10:
                        break
                question_text = ' '.join(question_words).strip() + '?'
            else:
                question_text = question_range.strip() + '?'
        
        # 답변: 현재 물음표 다음부터 다음 질문 시작 전까지
        if i + 1 < len(question_marks):
            next_q_start = question_marks[i + 1]
            answer = full_text[q_pos + 1:next_q_start].strip()
        else:
            # 마지막 질문
            answer = full_text[q_pos + 1:].strip()
        
        # 공백 정리
        question = ' '.join(question_text.split())
        answer = ' '.join(answer.split())
        
        # 질문이 유효한지 확인 (너무 짧거나 의미없는 질문 제외)
        if question and question.endswith('?') and len(question.replace('?', '').strip()) > 3:
            qa_pairs.append({
                'question': question,
                'answer': answer
            })
    
    # 출력 형식으로 변환: 질문과 답변을 한 줄로, 쌍 사이는 한 줄 띄우기
    output_lines = []
    for pair in qa_pairs:
        question = pair['question'].strip()
        answer = pair['answer'].strip()
        
        if question:
            if answer:
                output_lines.append(f"{question} {answer}")
            else:
                output_lines.append(question)
            output_lines.append("")  # 질문-답변 쌍 사이 한 줄 띄기
    
    # 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"재포맷 완료: {len(qa_pairs)}개의 질문-답변 쌍을 생성했습니다.")


if __name__ == '__main__':
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent.parent
    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'pre_normalize' / '신혼부부 사업FAQ_normalized.txt'
    output_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'pre_normalize' / '신혼부부 사업FAQ_normalized.txt'
    
    reformat_qa(str(input_file), str(output_file))

