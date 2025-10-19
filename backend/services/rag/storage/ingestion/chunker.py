#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
간소화된 문서 청킹 모듈 (v2)
정규화된 섹션을 검색에 최적화된 청크로 분할합니다.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """청크 데이터 클래스"""
    chunk_id: str
    content: str
    chunk_type: str  # 'text', 'table', 'list', 'mixed'
    document_id: str
    section_id: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'chunk_type': self.chunk_type,
            'document_id': self.document_id,
            'section_id': self.section_id,
            'metadata': self.metadata
        }


class DocumentChunker:
    """간소화된 문서 청킹 클래스"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000
    ):
        """
        초기화

        Args:
            chunk_size: 목표 청크 크기 (문자 수)
            chunk_overlap: 청크 간 중복 크기 (문자 수)
            min_chunk_size: 최소 청크 크기
            max_chunk_size: 최대 청크 크기
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        logger.info(f"DocumentChunker 초기화: chunk_size={chunk_size}, overlap={chunk_overlap}")

    def chunk_document(
        self,
        normalized_doc: Dict[str, Any]
    ) -> List[Chunk]:
        """
        정규화된 문서를 청크로 분할

        Args:
            normalized_doc: normalizer.normalize_document() 결과

        Returns:
            청크 리스트
        """
        if 'sections' not in normalized_doc:
            logger.warning("문서에 섹션이 없습니다")
            return []

        document_id = normalized_doc.get('file_name', 'unknown')
        sections = normalized_doc.get('sections', [])

        all_chunks = []

        for section in sections:
            section_chunks = self._chunk_section(section, document_id)
            all_chunks.extend(section_chunks)

        logger.info(f"총 {len(all_chunks)}개 청크 생성됨")
        return all_chunks

    def _chunk_section(
        self,
        section: Dict[str, Any],
        document_id: str
    ) -> List[Chunk]:
        """섹션을 청크로 분할"""
        section_id = section.get('id', 'unknown')
        section_type = section.get('type', 'text')
        title = section.get('title', '')
        content = section.get('content', [])

        # 표는 하나의 청크로 유지
        if section_type == 'table':
            return self._chunk_table_section(section, document_id)

        # 일반 텍스트/리스트는 크기 기반 청킹
        if isinstance(content, list):
            text_content = '\n'.join(str(c) for c in content)
        else:
            text_content = str(content)

        # 제목 포함
        if title:
            text_content = f"{title}\n\n{text_content}"

        return self._chunk_text(
            text_content,
            document_id,
            section_id,
            section_type,
            section.get('metadata', {})
        )

    def _chunk_table_section(
        self,
        section: Dict[str, Any],
        document_id: str
    ) -> List[Chunk]:
        """표 섹션 처리 (하나의 청크로 유지)"""
        section_id = section.get('id', 'unknown')
        content = section.get('content', [])

        if isinstance(content, list):
            table_text = '\n'.join(str(c) for c in content)
        else:
            table_text = str(content)

        # 표가 너무 크면 행 단위로 분할
        if len(table_text) > self.max_chunk_size:
            return self._chunk_large_table(
                table_text,
                document_id,
                section_id,
                section.get('title', ''),
                section.get('metadata', {})
            )

        # 일반 표는 하나의 청크
        chunk = Chunk(
            chunk_id=f"{document_id}_{section_id}_0",
            content=table_text,
            chunk_type='table',
            document_id=document_id,
            section_id=section_id,
            metadata={
                'title': section.get('title', ''),
                'original_type': 'table',
                **section.get('metadata', {})
            }
        )

        return [chunk]

    def _chunk_large_table(
        self,
        table_text: str,
        document_id: str,
        section_id: str,
        title: str,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """큰 표를 행 단위로 분할"""
        lines = table_text.split('\n')
        chunks = []

        # 헤더 찾기 (=== 표 N === 또는 첫 번째 마크다운 행)
        header_lines = []
        data_lines = []

        in_header = True
        for line in lines:
            if line.strip().startswith('===') or line.strip().startswith('|---'):
                in_header = False
                header_lines.append(line)
            elif in_header or len(header_lines) < 3:
                header_lines.append(line)
            else:
                data_lines.append(line)

        # 헤더를 모든 청크에 포함
        header_text = '\n'.join(header_lines)

        # 데이터 행을 청크로 분할
        current_chunk_lines = []
        current_size = len(header_text)
        chunk_idx = 0

        for line in data_lines:
            line_size = len(line)

            if current_size + line_size > self.chunk_size and current_chunk_lines:
                # 청크 생성
                chunk_content = f"{header_text}\n" + '\n'.join(current_chunk_lines)
                chunks.append(Chunk(
                    chunk_id=f"{document_id}_{section_id}_{chunk_idx}",
                    content=chunk_content,
                    chunk_type='table',
                    document_id=document_id,
                    section_id=section_id,
                    metadata={
                        'title': title,
                        'original_type': 'table',
                        'chunk_part': chunk_idx + 1,
                        **metadata
                    }
                ))

                # 리셋
                current_chunk_lines = [line]
                current_size = len(header_text) + line_size
                chunk_idx += 1
            else:
                current_chunk_lines.append(line)
                current_size += line_size

        # 마지막 청크
        if current_chunk_lines:
            chunk_content = f"{header_text}\n" + '\n'.join(current_chunk_lines)
            chunks.append(Chunk(
                chunk_id=f"{document_id}_{section_id}_{chunk_idx}",
                content=chunk_content,
                chunk_type='table',
                document_id=document_id,
                section_id=section_id,
                metadata={
                    'title': title,
                    'original_type': 'table',
                    'chunk_part': chunk_idx + 1,
                    **metadata
                }
            ))

        logger.info(f"큰 표를 {len(chunks)}개 청크로 분할")
        return chunks

    def _chunk_text(
        self,
        text: str,
        document_id: str,
        section_id: str,
        section_type: str,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """텍스트를 크기 기반으로 청킹"""
        if not text or len(text) < self.min_chunk_size:
            # 너무 작으면 하나의 청크로
            if text:
                return [Chunk(
                    chunk_id=f"{document_id}_{section_id}_0",
                    content=text,
                    chunk_type=section_type,
                    document_id=document_id,
                    section_id=section_id,
                    metadata=metadata
                )]
            return []

        # 문장 단위로 분할 (한국어 고려)
        sentences = self._split_sentences(text)

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_idx = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # 문장 하나가 max_chunk_size보다 크면 강제 분할
            if sentence_size > self.max_chunk_size:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(self._create_chunk(
                        ' '.join(current_chunk),
                        document_id,
                        section_id,
                        section_type,
                        chunk_idx,
                        metadata
                    ))
                    chunk_idx += 1

                # 긴 문장을 강제 분할
                for i in range(0, len(sentence), self.chunk_size):
                    sub_sentence = sentence[i:i + self.chunk_size]
                    chunks.append(self._create_chunk(
                        sub_sentence,
                        document_id,
                        section_id,
                        section_type,
                        chunk_idx,
                        metadata
                    ))
                    chunk_idx += 1

                current_chunk = []
                current_size = 0
                continue

            # 청크 크기 초과 시 새 청크 시작
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(
                    ' '.join(current_chunk),
                    document_id,
                    section_id,
                    section_type,
                    chunk_idx,
                    metadata
                ))
                chunk_idx += 1

                # 오버랩 처리 (마지막 몇 문장 유지)
                if self.chunk_overlap > 0 and len(current_chunk) > 1:
                    overlap_text = ' '.join(current_chunk)
                    if len(overlap_text) > self.chunk_overlap:
                        # 마지막 overlap 크기만큼만 유지
                        overlap_text = overlap_text[-self.chunk_overlap:]
                        current_chunk = [overlap_text, sentence]
                        current_size = len(overlap_text) + sentence_size
                    else:
                        current_chunk = [sentence]
                        current_size = sentence_size
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # 마지막 청크
        if current_chunk:
            chunks.append(self._create_chunk(
                ' '.join(current_chunk),
                document_id,
                section_id,
                section_type,
                chunk_idx,
                metadata
            ))

        return chunks

    def _create_chunk(
        self,
        content: str,
        document_id: str,
        section_id: str,
        chunk_type: str,
        chunk_idx: int,
        metadata: Dict[str, Any]
    ) -> Chunk:
        """청크 객체 생성"""
        return Chunk(
            chunk_id=f"{document_id}_{section_id}_{chunk_idx}",
            content=content.strip(),
            chunk_type=chunk_type,
            document_id=document_id,
            section_id=section_id,
            metadata={
                **metadata,
                'chunk_index': chunk_idx,
                'char_count': len(content)
            }
        )

    def _split_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분할 (한국어 고려)"""
        # 한국어 문장 구분자 패턴
        # ., !, ? 뒤에 공백이나 줄바꿈이 오는 경우
        pattern = r'(?<=[.!?])\s+(?=[가-힣A-Z"])'

        sentences = re.split(pattern, text)

        # 빈 문장 제거
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences


def main():
    """메인 함수 - 정규화된 파일들을 청크로 변환하여 backend/data/vector_db/chunks에 저장"""
    import json
    from pathlib import Path

    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent

    # 입력: 정규화된 JSON 파일
    input_dir = base_dir / 'backend' / 'data' / 'vector_db' / 'normalized'

    # 출력: 청크 저장 디렉토리
    output_dir = base_dir / 'backend' / 'data' / 'vector_db' / 'chunks'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 정규화된 파일들 찾기
    normalized_files = list(input_dir.glob('*_normalized.json'))

    if not normalized_files:
        print(f"정규화된 파일이 없습니다: {input_dir}")
        print("먼저 normalizer를 실행하세요.")
        return

    print(f"발견된 정규화 파일: {len(normalized_files)}개")
    print(f"입력: {input_dir}")
    print(f"출력: {output_dir}")
    print("=" * 70)

    # 청킹 설정
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)

    total_chunks = 0

    for norm_file in normalized_files:
        print(f"\n처리 중: {norm_file.name}")

        try:
            with open(norm_file, 'r', encoding='utf-8') as f:
                normalized_doc = json.load(f)

            # 청킹
            chunks = chunker.chunk_document(normalized_doc)

            if not chunks:
                print(f"  경고: 청크가 생성되지 않음")
                continue

            # 청크를 딕셔너리로 변환
            chunks_dict = [chunk.to_dict() for chunk in chunks]

            # 저장
            output_file = output_dir / f"{norm_file.stem}_chunks.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunks_dict, f, ensure_ascii=False, indent=2)

            print(f"  완료: {len(chunks)}개 청크 → {output_file.name}")
            total_chunks += len(chunks)

            # 첫 파일만 샘플 출력
            if norm_file == normalized_files[0]:
                print(f"\n  샘플 청크 (첫 3개):")
                for i, chunk in enumerate(chunks[:3]):
                    print(f"    {i+1}. [{chunk.chunk_type}] {len(chunk.content)}자: {chunk.content[:80]}...")

        except Exception as e:
            print(f"  오류: {str(e)}")
            continue

    print(f"\n{'='*70}")
    print(f"총 {len(normalized_files)}개 파일 처리 완료")
    print(f"총 {total_chunks}개 청크 생성")
    print(f"저장 위치: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
