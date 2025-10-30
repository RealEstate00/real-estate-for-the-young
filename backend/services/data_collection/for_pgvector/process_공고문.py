import re
from pathlib import Path

def convert_circled_numbers(text):
    """동그라미로 감싼 숫자를 일반 숫자로 변환"""
    circled_map = {
        '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
        '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10',
        '⑪': '11', '⑫': '12', '⑬': '13', '⑭': '14', '⑮': '15',
        '⑯': '16', '⑰': '17', '⑱': '18', '⑲': '19', '⑳': '20'
    }
    for circled, number in circled_map.items():
        text = text.replace(circled, number)
    return text

def clean_text(text):
    """텍스트 정제"""
    # 동그라미 숫자 변환
    text = convert_circled_numbers(text)

    # ※ -> (참고) 교체
    text = text.replace('※', '(참고)')

    # ☑ 삭제
    text = text.replace('☑', '')

    # ☎가 들어가있는 괄호 및 그 내용 모두 삭제
    text = re.sub(r'\([^)]*☎[^)]*\)', '', text)

    # 꺽쇄<> 를 괄호()로 변경
    text = text.replace('<', '(').replace('>', ')')

    # * 삭제
    text = text.replace('*', '')

    # URL 삭제 후 빈 괄호 삭제
    text = re.sub(r'https?://[^\s)]+', '', text)
    text = re.sub(r'\(\s*\)', '', text)

    # 마침표 다음에 ○가 나오는 경우 줄바꿈 추가
    text = re.sub(r'\.\s*○', '.\n○', text)

    # 각 줄의 앞뒤 공백 제거
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # 연속된 빈 줄을 하나로 줄이기
    text = re.sub(r'\n\s*\n', '\n\n', text)

    return text.strip()

def chunk_by_sentence(text, source_title):
    """문장 단위로 청크를 나눔 (마침표 기준, 문장이 짤리면 안됨)"""
    chunks = []

    # 문단 단위로 먼저 나누기
    paragraphs = text.split('\n\n')

    current_chunk = []
    current_length = 0
    max_chunk_size = 1000  # 청크당 최대 문자 수

    for paragraph in paragraphs:
        if not paragraph.strip():
            continue

        # 문장 단위로 나누기 (마침표 기준)
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)

            # 현재 청크에 추가하면 너무 길어지는 경우
            if current_length + sentence_length > max_chunk_size and current_chunk:
                # 현재 청크를 저장하고 새 청크 시작
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'source': source_title,
                        'document_type': '공고'
                    }
                })
                current_chunk = []
                current_length = 0

            # 현재 문장을 청크에 추가
            current_chunk.append(sentence)
            current_length += sentence_length

    # 마지막 청크 추가
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append({
            'text': chunk_text,
            'metadata': {
                'source': source_title,
                'document_type': '공고'
            }
        })

    return chunks

def process_announcement_file(input_path, output_dir):
    """공고문 파일 처리"""
    # 파일 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 공고문들을 "서울특별시 공고" 또는 "서울특별시공고"로 구분
    announcements = re.split(r'(?=서울특별시\s*공고)', content)
    announcements = [a.strip() for a in announcements if a.strip()]

    all_chunks = []

    for announcement in announcements:
        if not announcement:
            continue

        # 공고 제목 추출 (첫 번째 줄에서 3줄 정도)
        lines = announcement.split('\n')
        title_lines = []
        for line in lines[:5]:
            if line.strip():
                title_lines.append(line.strip())
                if len(title_lines) >= 2:
                    break

        source_title = ' '.join(title_lines) if title_lines else "공고"

        # 텍스트 정제
        cleaned = clean_text(announcement)

        # 청크 생성
        chunks = chunk_by_sentence(cleaned, source_title)
        all_chunks.extend(chunks)

    # 출력 디렉토리 생성
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 정제된 전체 텍스트 저장
    cleaned_output = output_dir / "공고문_cleaned.txt"
    with open(cleaned_output, 'w', encoding='utf-8') as f:
        for i, announcement in enumerate(announcements, 1):
            cleaned = clean_text(announcement)
            f.write(f"{'='*80}\n")
            f.write(f"공고문 {i}\n")
            f.write(f"{'='*80}\n\n")
            f.write(cleaned)
            f.write(f"\n\n")

    print(f"정제된 텍스트 저장: {cleaned_output}")

    # 청크 저장 (JSON)
    import json
    chunks_output = output_dir / "공고문_chunks.json"
    with open(chunks_output, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"청크 파일 저장: {chunks_output}")
    print(f"총 {len(all_chunks)}개의 청크가 생성되었습니다.")

    # 청크 통계 출력
    avg_length = sum(len(chunk['text']) for chunk in all_chunks) / len(all_chunks) if all_chunks else 0
    print(f"평균 청크 길이: {avg_length:.0f} 문자")

    return all_chunks

if __name__ == "__main__":
    input_file = Path("backend/data/raw/finance_support/공고문/공고문.txt")
    output_directory = Path("backend/data/processed/공고문")

    print("공고문 처리 시작...")
    chunks = process_announcement_file(input_file, output_directory)
    print("\n처리 완료!")

    # 샘플 청크 출력
    if chunks:
        print("\n[첫 번째 청크 샘플]")
        print(f"Source: {chunks[0]['metadata']['source']}")
        print(f"Type: {chunks[0]['metadata']['document_type']}")
        print(f"Text: {chunks[0]['text'][:200]}...")
