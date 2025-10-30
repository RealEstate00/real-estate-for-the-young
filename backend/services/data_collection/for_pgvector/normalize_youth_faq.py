#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
청년 임차보증금 이자지원사업 FAQ 노말라이징 및 청크 생성 스크립트

원본 PDF 파일: [붙임1]  청년 임차보증금 이자지원사업 FAQ.pdf
"""

import re
import json
from pathlib import Path


def normalize_and_chunk_youth_faq(input_file: str, output_txt: str, output_json: str):
    """
    청년 FAQ 파일을 노말라이징하고 청크로 나눕니다.

    노말라이징 규칙:
    1. * 삭제
    2. [cite_start], [cite: %] 삭제
    3. [] -> ()
    4. 원문자 -> 아라비아 숫자 매핑
    5. ※ -> (참고) 변경
    6. URL 삭제 및 빈 괄호 삭제
    7. 여러 공백을 하나로
    8. 질문(?로 끝나는 문장) 앞에 \n\n 추가

    청크 규칙:
    1. ### 을 기준으로 청크 나눔
    2. 메타데이터: 제목(### 뒤), source, document_type
    """

    # 원문자 -> 아라비아 숫자 매핑
    circle_numbers = {
        '①': '1.', '②': '2.', '③': '3.', '④': '4.',
        '⑤': '5.', '⑥': '6.', '⑦': '7.', '⑧': '8.',
        '⑨': '9.', '⑩': '10.'
    }

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 노말라이징
    # 1. [cite_start] 삭제
    normalized = re.sub(r'\[cite_start\]', '', content)

    # 2. [cite: %] 삭제 (% 는 숫자)
    normalized = re.sub(r'\[cite:\s*\d+\]', '', normalized)

    # 3. * 삭제 (목록 기호)
    normalized = re.sub(r'^\s*\*\s+', '', normalized, flags=re.MULTILINE)

    # 4. ** 삭제 (볼드 마크다운)
    normalized = re.sub(r'\*\*', '', normalized)

    # 5. [] -> ()
    # 대괄호로 묶인 URL 등을 괄호로 변경
    normalized = re.sub(r'\[([^\]]+)\]', r'(\1)', normalized)

    # 6. 원문자 -> 아라비아 숫자 변환
    for old, new in circle_numbers.items():
        normalized = normalized.replace(old, new)

    # 7. ※ -> (참고) 변경
    normalized = normalized.replace('※', '(참고)')

    # 8. URL 삭제 (http:// 또는 https://)
    # 괄호 안의 URL도 삭제
    normalized = re.sub(r'\(https?://[^\)]+\)', '', normalized)
    normalized = re.sub(r'https?://[^\s\)]+', '', normalized)

    # 9. 빈 괄호 삭제 (텍스트 없는 괄호)
    normalized = re.sub(r'\(\s*\)', '', normalized)

    # 10. > -> '이후; 변경
    normalized = normalized.replace('>', '\'이후;')

    # 11. 여러 공백을 하나로 (단, 줄바꿈은 제외)
    normalized = re.sub(r' +', ' ', normalized)

    # 12. 질문(?로 끝나는 문장) 앞에 \n\n 추가
    # 물음표 앞에 줄바꿈이 없거나 하나만 있으면 두 개로 변경
    normalized = re.sub(r'([^\n])\n?([^\n]+\?)', r'\1\n\n\2', normalized)

    # 13. 앞뒤 공백 제거
    normalized = normalized.strip()

    # TXT 파일 저장
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(normalized)

    print(f"노말라이징 완료: {output_txt}")

    # 청크 생성 (### 기준)
    chunks = []

    # ### 로 분리 (이미 **가 제거되었으므로 ### 뒤 텍스트만 매칭)
    sections = re.split(r'(###[^\n]+)', normalized)

    chunk_id = 1
    current_title = "서울시 청년 임차보증금 이자지원사업 FAQ"
    current_content = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # ### 제목인 경우
        if section.startswith('###'):
            # 이전 청크 저장
            if current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text:
                    chunks.append({
                        'chunk_id': chunk_id,
                        'content': current_title + '\n' + content_text,
                        'metadata': {
                            'title': current_title,
                            'source': '청년 임차보증금 이자지원사업FAQ.pdf',
                            'document_type': 'FAQ'
                        }
                    })
                    chunk_id += 1

            # 새 청크 시작
            # 제목 추출 (### 제목 형태)
            title_match = re.search(r'###\s+(.+)', section)
            if title_match:
                current_title = title_match.group(1).strip()

            # 제목만 content에 포함 (### 제거)
            current_content = [current_title]
        else:
            # 내용인 경우
            if section.startswith('##') or section.startswith('---'):
                continue

            # 내용 추가
            if section.strip():
                current_content.append(section)

    # 마지막 청크 저장
    if current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            chunks.append({
                'chunk_id': chunk_id,
                'content': content_text,
                'metadata': {
                    'title': current_title,
                    'source': '청년 임차보증금 이자지원사업FAQ.pdf',
                    'document_type': 'FAQ'
                }
            })

    # JSON 파일 저장
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"청크 생성 완료: {len(chunks)}개 청크")
    print(f"JSON 파일 저장: {output_json}")

    return len(chunks)


if __name__ == '__main__':
    # 경로 설정
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent.parent

    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '청년 임차보증금 이자지원사업FAQ.txt'
    output_txt = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '청년 임차보증금 이자지원사업FAQ_normalized.txt'
    output_json = backend_dir / 'data' / 'raw' / 'finance_support' / 'FAQ' / '청년 임차보증금 이자지원사업FAQ_chunked.json'

    print(f"입력 파일: {input_file}")
    print(f"출력 TXT: {output_txt}")
    print(f"출력 JSON: {output_json}")
    print(f"입력 파일 존재: {input_file.exists()}\n")

    chunk_count = normalize_and_chunk_youth_faq(str(input_file), str(output_txt), str(output_json))

    print(f"\n[통계]")
    print(f"- 총 청크: {chunk_count}개")
