#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주거지원정책 PDF 텍스트 노말라이징 및 청킹 스크립트

입력: backend/data/raw/finance_support/모든_주거지원_정책.txt
출력: backend/data/raw/finance_support/주거지원정책_chunked.json

노말라이징 규칙: FAQ와 동일
청킹 규칙: 페이지 단위로 청킹
"""

import re
import json
from pathlib import Path


def normalize_text(text: str) -> str:
    """
    텍스트 노말라이징 (FAQ 규칙 적용)

    규칙:
    1. . ? ! 로 끝나면 줄 바꾸기
    2. 그걸로 끝나지 않았는데 줄이 바뀌어져 있다면 줄이 안바뀌도록
    3. ※, ☞ -> (참고) 로 변경
    4. ▶ -> 공백 한 개로 변경
    5. ■, * 삭제
    6. 한자어 삭제 (괄호 안의 한자)
    7. 빈 괄호 삭제
    8. 페이지정보는 유지 (나중에 분리 처리)
    9. 원문자 -> 아라비아 숫자 매핑
    10. URL 삭제
    11. 여러 공백을 하나로
    """

    # 원문자 -> 아라비아 숫자 매핑
    circle_numbers = {
        '①': '1.', '②': '2.', '③': '3.', '④': '4.',
        '⑤': '5.', '⑥': '6.', '⑦': '7.', '⑧': '8.',
        '⑨': '9.', '⑩': '10.'
    }

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # 빈 줄 유지
        if not stripped:
            cleaned_lines.append("")
            continue

        # 원문자 -> 아라비아 숫자 변환
        for old, new in circle_numbers.items():
            stripped = stripped.replace(old, new)

        # ※, ☞ -> (참고) 변경
        stripped = stripped.replace('※', '(참고)')
        stripped = stripped.replace('☞', '(참고)')

        # ▶ -> 공백 한 개로 변경
        stripped = stripped.replace('▶', ' ')

        # ■, * 삭제
        stripped = stripped.replace('■', '')
        stripped = stripped.replace('*', '')

        # URL 제거
        stripped = re.sub(r'\(https?://[^\)]+\)', '', stripped)
        stripped = re.sub(r'https?://[^\s\)]+', '', stripped)

        # 한자어 삭제 (괄호 안의 한자 유니코드 범위: 4E00-9FFF)
        # 예: "주소득자(主所得者)" -> "주소득자"
        stripped = re.sub(r'\([一-龥]+\)', '', stripped)

        # 빈 괄호 삭제 (여러 번 실행하여 중첩된 빈 괄호도 제거)
        for _ in range(3):
            stripped = re.sub(r'\(\s*\)', '', stripped)

        # ㅇ -> - 변경 (리스트 표시)
        if stripped.startswith('ㅇ '):
            stripped = '-' + stripped[1:]

        # < 꺽쇄 -> ( 괄호로 변경
        stripped = stripped.replace('<', '(')
        stripped = stripped.replace('>', ')')

        # 여러 공백을 하나로
        stripped = re.sub(r' +', ' ', stripped)

        # 앞뒤 공백 제거
        stripped = stripped.strip()

        # 물음표/마침표/느낌표 앞 공백 제거
        stripped = re.sub(r'\s+\?', '?', stripped)
        stripped = re.sub(r'\s+\.', '.', stripped)
        stripped = re.sub(r'\s+!', '!', stripped)

        # 닫는 괄호 앞 공백 제거
        stripped = re.sub(r'\s+\)', ')', stripped)

        # 콤마 앞 공백 제거
        stripped = re.sub(r'\s+,', ',', stripped)

        cleaned_lines.append(stripped)

    # 문장 끝이 아닌 곳에서 줄바꿈된 부분은 공백으로 연결
    combined_text = ""
    for i, line in enumerate(cleaned_lines):
        if not line.strip():
            combined_text += "\n"
        elif i == 0:
            combined_text += line
        else:
            prev_text = combined_text.rstrip()
            # 이전 텍스트가 . ? ! ) 로 끝나지 않았고, 현재 줄이 빈 줄이 아니면 공백으로 연결
            if prev_text and prev_text[-1] not in '.?!\n)' and line.strip():
                # 특수 케이스: === 구분선이나 [페이지 N] 같은 메타데이터는 줄바꿈 유지
                if line.startswith('===') or line.startswith('[페이지') or line.startswith('파일명:'):
                    combined_text += "\n" + line
                else:
                    combined_text += " " + line
            else:
                combined_text += "\n" + line

    return combined_text


def parse_policy_document(input_file: str) -> list:
    """
    주거지원정책 문서를 파싱하여 페이지별로 분리

    Returns:
        list: [{'source': 'PDF파일명', 'page': 페이지번호, 'content': '내용'}, ...]
    """

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 먼저 노말라이징
    normalized_content = normalize_text(content)

    # 파일별로 분리 (=== 구분선 기준)
    file_pattern = r'={80,}\n파일명: (.+?\.pdf)\n={80,}'
    file_splits = re.split(file_pattern, normalized_content)

    pages = []

    for i in range(1, len(file_splits), 2):
        pdf_filename = file_splits[i].strip()
        file_content = file_splits[i + 1] if i + 1 < len(file_splits) else ""

        # 페이지별로 분리
        page_pattern = r'\[페이지 (\d+)\]'
        page_splits = re.split(page_pattern, file_content)

        for j in range(1, len(page_splits), 2):
            page_num = int(page_splits[j])
            page_content = page_splits[j + 1].strip() if j + 1 < len(page_splits) else ""

            if page_content:
                pages.append({
                    'source': pdf_filename,
                    'page': page_num,
                    'content': page_content
                })

    return pages


def create_json_chunks(pages: list, output_file: str):
    """
    페이지별 청크를 JSON 파일로 저장

    Args:
        pages: 페이지 정보 리스트
        output_file: 출력 JSON 파일 경로
    """

    json_data = []

    for idx, page in enumerate(pages, 1):
        json_data.append({
            'chunk_id': idx,
            'content': page['content'],
            'metadata': {
                'source': page['source'],
                'page': page['page'],
                'document_type': 'housing_policy'
            }
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"JSON 파일 저장 완료: {output_file}")
    print(f"총 {len(json_data)}개의 페이지 청크 생성")


def main():
    # 경로 설정
    script_dir = Path(__file__).parent  # for_pgvector
    backend_dir = script_dir.parent.parent.parent  # backend
    input_file = backend_dir / 'data' / 'raw' / 'finance_support' / '모든_주거지원_정책.txt'
    output_json = backend_dir / 'data' / 'raw' / 'finance_support' / '주거지원정책_chunked.json'

    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_json}")
    print(f"입력 파일 존재: {input_file.exists()}\n")

    if not input_file.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_file}")
        return

    # 문서 파싱
    print("문서 파싱 중...")
    pages = parse_policy_document(str(input_file))
    print(f"총 {len(pages)}개의 페이지 파싱 완료\n")

    # JSON 청크 생성
    print("JSON 청크 생성 중...")
    create_json_chunks(pages, str(output_json))

    # 통계 출력
    print(f"\n[통계]")
    print(f"- 총 페이지: {len(pages)}개")

    # 파일별 페이지 수 통계
    file_stats = {}
    for page in pages:
        source = page['source']
        if source not in file_stats:
            file_stats[source] = 0
        file_stats[source] += 1

    print(f"- 총 PDF 파일: {len(file_stats)}개")
    print("\n[파일별 페이지 수]")
    for source, count in sorted(file_stats.items()):
        print(f"  {source}: {count}페이지")


if __name__ == '__main__':
    main()
