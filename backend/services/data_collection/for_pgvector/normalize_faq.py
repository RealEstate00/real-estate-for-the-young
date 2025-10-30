#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신혼부부 사업 FAQ 노말라이징 스크립트

원본 PDF 파일: (붙임1)신혼부부 사업 FAQ.pdf
"""

import re
from pathlib import Path


def normalize_faq(input_file: str, output_file: str):
    """
    FAQ 파일을 노말라이징합니다.

    규칙:
    1. . ? ! 로 끝나면 줄 바꾸기
    2. 그걸로 끝나지 않았는데 줄이 바뀌어져 있다면 줄이 안바뀌도록
    3. '구분 답변' 삭제. '답 변'으로 된 것도 삭제
    4. ※ -> (참고) 로 변경
    5. 페이지정보 삭제
    6. 질문과 답변 쌍 하나 완료시 한줄띄기. 질문과 답변쌍은 물음표가 포함된 문장을 기준으로 그 문장이 새로운 쌍의 시작임
    7. 원문자 -> 아라비아 숫자 매핑
    8. URL 삭제 및 빈 괄호 삭제
    9. 여러 공백을 하나로
    10. 질문(?로 끝나는 문장) 앞에 \n\n 추가
    """

    # 원문자 -> 아라비아 숫자 매핑
    circle_numbers = {
        '①': '1.', '②': '2.', '③': '3.', '④': '4.',
        '⑤': '5.', '⑥': '6.', '⑦': '7.', '⑧': '8.',
        '⑨': '9.', '⑩': '10.'
    }

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1단계: 페이지정보, 구분 답변 삭제 및 ※ 변경
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()

        # 빈 줄 유지
        if not stripped:
            cleaned_lines.append("")
            continue

        # 페이지정보 삭제 (예: -1-, -2- 등)
        if re.match(r'^-\d+-', stripped):
            continue

        # '구분 답변' 또는 '답 변' 삭제
        if '구분 답' in stripped and '변' in stripped:
            continue

        # 원문자 -> 아라비아 숫자 변환
        for old, new in circle_numbers.items():
            stripped = stripped.replace(old, new)

        # ※ -> (참고) 변경
        stripped = stripped.replace('※', '(참고)')

        # URL 제거 (http://..., https://... 등)
        stripped = re.sub(r'\(https?://[^\)]+\)', '', stripped)
        stripped = re.sub(r'https?://[^\s\)]+', '', stripped)

        # 빈 괄호 삭제 (텍스트 없는 괄호)
        stripped = re.sub(r'\(\s*\)', '', stripped)

        # ㅇ -> - 변경
        stripped = stripped.replace('ㅇ', '-')

        # < 꺽쇄 -> ( 괄호로 변경
        stripped = stripped.replace('<', '(')

        # > -> '이후; 변경
        stripped = stripped.replace('>', '\'이후;')

        # 여러 공백을 하나로
        stripped = re.sub(r' +', ' ', stripped)

        # 앞뒤 공백 제거
        stripped = stripped.strip()

        # 추가 정규화 규칙
        # 1. 한글자씩 띄어쓰기된 텍스트만 정규화
        # 예: "신 청  완 료  후" -> "신청완료후"
        # 하지만 "서울시 융자추천서" 같은 정상 띄어쓰기는 유지

        # 1-1. 먼저 2개 이상 연속 공백만 찾아서 제거 (비정상 패턴)
        # "신 청  완 료" 같은 경우
        for _ in range(10):
            new_stripped = re.sub(r'([가-힣])\s{2,}([가-힣])', r'\1\2', stripped)
            if new_stripped == stripped:
                break
            stripped = new_stripped

        # 2. 물음표 앞 공백 제거 (예: "되나요 ?" -> "되나요?")
        stripped = re.sub(r'\s+\?', '?', stripped)

        # 3. 마침표 앞 공백 제거 (예: "됩니다 ." -> "됩니다.")
        stripped = re.sub(r'\s+\.', '.', stripped)

        # 4. 닫는 괄호 앞 공백 제거 (예: "가능 )" -> "가능)")
        stripped = re.sub(r'\s+\)', ')', stripped)

        # 5. 콤마 앞 공백 제거 (예: "대출자격 ," -> "대출자격,")
        stripped = re.sub(r'\s+,', ',', stripped)

        # 6. 닫는 대괄호 앞 공백 제거 (예: "융자추천서 ]" -> "융자추천서]")
        stripped = re.sub(r'\s+\]', ']', stripped)

        cleaned_lines.append(stripped)
    
    # 2단계: 줄들을 하나의 텍스트로 결합하되, 문장 끝이 아닌 곳에서 줄바꿈된 부분은 공백으로 연결
    combined_text = ""
    for i, line in enumerate(cleaned_lines):
        if not line.strip():
            combined_text += "\n"
        elif i == 0:
            combined_text += line
        else:
            prev_text = combined_text.rstrip()
            # 이전 텍스트가 . ? ! ) 로 끝나지 않았고, 현재 줄이 빈 줄이 아니면 공백으로 연결
            # ) 는 괄호로 문장이 끝나는 경우를 처리
            if prev_text and prev_text[-1] not in '.?!\n)' and line.strip():
                combined_text += " " + line
            elif prev_text and prev_text[-1] == ')' and line.strip():
                # 괄호로 끝나는 경우, 줄바꿈 추가
                combined_text += "\n" + line
            else:
                combined_text += line

    # 2-1단계: 마침표 뒤에 바로 질문이 시작되는 경우 분리
    # 예: "불가능합니다 .융자추천서 신청인이" -> "불가능합니다 .\n융자추천서 신청인이"
    combined_text = re.sub(r'\.([가-힣]{2,})', r'.\n\1', combined_text)
    combined_text = re.sub(r'\)([가-힣]{2,})', r')\n\1', combined_text)
    
    # 3단계: 질문과 답변 쌍 추출
    # 물음표를 기준으로 질문과 답변 분리
    qa_pairs = []
    
    # 물음표를 찾아서 질문과 답변 분리
    current_question_parts = []
    current_answer_parts = []
    
    # 텍스트를 물음표로 분리
    parts = re.split(r'([^?]*\?)', combined_text)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # 물음표가 포함된 부분 처리
        if '?' in part:
            # 물음표 기준으로 질문과 답변 분리
            q_match = re.match(r'^(.*?)(\?)(.*)$', part)
            if q_match:
                question_part = q_match.group(1) + '?'
                answer_part = q_match.group(3).strip()
                
                # 이전 질문-답변 쌍 저장
                if current_question_parts:
                    question = ' '.join(current_question_parts).strip()
                    answer = ' '.join(current_answer_parts).strip()

                    # 질문 검증 1: 질문에 마침표가 있으면 마침표 이후만 질문으로 간주
                    if '.' in question:
                        last_period = question.rfind('.')
                        # 마침표가 물음표 앞에 있으면
                        if last_period < len(question) - 1:  # 마침표가 끝이 아님
                            # 마침표 이전을 답변에 추가
                            if last_period > 0:
                                # 이전 답변에 추가
                                prev_answer_part = question[:last_period + 1].strip()
                                if prev_answer_part:
                                    answer = (prev_answer_part + ' ' + answer).strip()
                                question = question[last_period + 1:].strip()

                    # 질문 검증 2: 답변이 마침표나 괄호로 끝나는지 확인
                    # 답변이 없거나 마침표/괄호로 끝나지 않으면 질문이 아님
                    has_valid_answer = answer and (answer.endswith('.') or answer.endswith(')'))

                    if question and has_valid_answer:
                        qa_pairs.append({
                            'question': question,
                            'answer': answer
                        })

                # 새 질문 시작
                current_question_parts = [question_part]
                current_answer_parts = []

                # 물음표 뒤의 텍스트가 있으면 답변에 추가
                if answer_part:
                    current_answer_parts.append(answer_part)
            else:
                # 물음표만 있는 경우
                if current_question_parts:
                    question = ' '.join(current_question_parts).strip()
                    answer = ' '.join(current_answer_parts).strip()
                    if question:
                        qa_pairs.append({
                            'question': question,
                            'answer': answer
                        })
                
                current_question_parts = [part]
                current_answer_parts = []
        else:
            if current_question_parts:
                # 답변에 추가
                current_answer_parts.append(part)
            else:
                # 질문이 아직 없는 경우 (파일 시작 부분 등) 질문으로 처리
                current_question_parts.append(part)
    
    # 마지막 쌍 저장
    if current_question_parts:
        question = ' '.join(current_question_parts).strip()
        answer = ' '.join(current_answer_parts).strip()

        # 질문 검증 1: 질문에 마침표가 있으면 마침표 이후만 질문으로 간주
        if '.' in question:
            last_period = question.rfind('.')
            if last_period < len(question) - 1:
                if last_period > 0:
                    prev_answer_part = question[:last_period + 1].strip()
                    if prev_answer_part:
                        answer = (prev_answer_part + ' ' + answer).strip()
                    question = question[last_period + 1:].strip()

        # 질문 검증 2: 답변이 마침표나 괄호로 끝나는지 확인
        has_valid_answer = answer and (answer.endswith('.') or answer.endswith(')'))

        if question and has_valid_answer:
            qa_pairs.append({
                'question': question,
                'answer': answer
            })
    
    # 4단계: 각 질문과 답변에서 문장을 . ? ! 기준으로 분리하고 줄바꿈 처리
    formatted_pairs = []
    for pair in qa_pairs:
        # 질문 처리: 물음표로 끝나므로 그대로 유지 (여러 줄일 수 있으므로 공백으로 합침)
        question = pair['question'].strip()
        
        # 답변 처리: 문장을 . ? ! ) 기준으로 분리하고 각 문장을 줄바꿈으로 구분
        answer = pair['answer'].strip()
        if answer:
            # 문장 분리: . ? ! ) 뒤에 공백이나 새로운 문장이 오는 경우 분리
            # 정규식을 사용하여 문장 분리
            # . ? ! ) 뒤에 공백이 오거나 문자열 끝인 경우 문장 끝으로 간주
            sentence_pattern = r'([^.!?\)]*[.!?\)]+)'
            matches = re.findall(sentence_pattern, answer)
            
            # 매칭되지 않은 부분도 추가
            if matches:
                sentences = [s.strip() for s in matches if s.strip()]
                # 마지막 문장이 . ? ! 로 끝나지 않은 경우 추가
                last_match_end = answer.rfind(matches[-1]) + len(matches[-1])
                if last_match_end < len(answer):
                    remaining = answer[last_match_end:].strip()
                    if remaining:
                        sentences.append(remaining)
            else:
                sentences = [answer]
            
            # 문장들을 줄바꿈으로 연결
            answer = '\n'.join([s for s in sentences if s])
        else:
            answer = ""
        
        formatted_pairs.append({
            'question': question,
            'answer': answer
        })
    
    # 5단계: 출력 형식으로 변환
    output_lines = []
    for pair in formatted_pairs:
        if pair['question']:
            output_lines.append(pair['question'])
        if pair['answer']:
            output_lines.append(pair['answer'])
        output_lines.append("")  # 질문-답변 쌍 사이 한 줄 띄기
    
    # 6단계: 줄바꿈 표시를 공백으로 변경
    for pair in formatted_pairs:
        pair['question'] = pair['question'].replace('\n', ' ')
        pair['answer'] = pair['answer'].replace('\n', ' ')

    # 7단계: TXT 파일 저장
    output_lines = []
    for pair in formatted_pairs:
        if pair['question']:
            output_lines.append(pair['question'])
        if pair['answer']:
            output_lines.append(pair['answer'])
        output_lines.append("")  # 질문-답변 쌍 사이 한 줄 띄기

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"노말라이징 완료: {len(formatted_pairs)}개의 질문-답변 쌍을 생성했습니다.")
    print(f"저장 위치: {output_file}")


if __name__ == '__main__':
    # 현재 스크립트 위치: backend/services/data_collection/for_pgvector/normalize_faq.py
    # 데이터 파일 위치: backend/data/raw/finance_support/FAQ/신혼부부 사업FAQ.txt
    script_dir = Path(__file__).parent  # for_pgvector
    backend_dir = script_dir.parent.parent.parent  # backend
    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '신혼부부 사업FAQ.txt'
    output_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '신혼부부 사업FAQ_normalized.txt'
    
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print(f"입력 파일 존재: {input_file.exists()}")
    
    normalize_faq(str(input_file), str(output_file))
