#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
텍스트 정제 및 정규화 모듈
OCR 결과를 정리하고 정규화합니다.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TextNormalizer:
    """텍스트 정제 및 정규화 클래스 (NLTK 통합)"""

    def __init__(self):
        # NLTK 초기화
        self._init_nltk()

        # 정규화 패턴들
        self.patterns = {
            # 공백 정리
            'multiple_spaces': re.compile(r'\s+'),
            'multiple_newlines': re.compile(r'\n\s*\n\s*\n+'),

            # OCR 잡음 제거
            'ocr_noise': re.compile(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]'),
            'repeated_chars': re.compile(r'(.)\1{3,}'),

            # 페이지 번호/헤더/푸터 패턴
            'page_number': re.compile(r'^\s*\d+\s*$'),
            'header_footer': re.compile(r'^(서울특별시|서울시|제\d+호|공고|붙임\d*)\s*$', re.MULTILINE),

            # 특수 문자 정리
            'bullet_points': re.compile(r'^[\s]*[•·▪▫◦‣⁃]\s*'),
            'dash_points': re.compile(r'^[\s]*[-–—]\s*'),
            'number_points': re.compile(r'^[\s]*\d+[\.\)]\s*'),

            # 인용/각주 번호
            'footnote_ref': re.compile(r'\[\d+\]'),
            'citation_ref': re.compile(r'\(\d+\)'),
        }

    def _init_nltk(self):
        """NLTK 초기화 및 필요한 데이터 다운로드"""
        try:
            import nltk

            # 필요한 데이터 다운로드 (이미 있으면 스킵)
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("NLTK punkt 데이터 다운로드 중...")
                nltk.download('punkt', quiet=True)

            try:
                nltk.data.find('tokenizers/punkt_tab')
            except LookupError:
                logger.info("NLTK punkt_tab 데이터 다운로드 중...")
                nltk.download('punkt_tab', quiet=True)

            self.nltk = nltk
            self.nltk_available = True
            logger.info("NLTK 초기화 완료")

        except Exception as e:
            logger.warning(f"NLTK 초기화 실패: {str(e)}. 기본 방식 사용")
            self.nltk = None
            self.nltk_available = False
    
    # ============================================================================
    # Main Normalization Methods
    # ============================================================================
    
    def normalize_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """문서 전체 정규화"""
        if 'full_text' not in doc_data:
            return doc_data
        
        text = doc_data['full_text']
        
        # 1. 기본 정리
        text = self.clean_text(text)
        
        # 2. 헤더/푸터 제거
        text = self.remove_headers_footers(text)
        
        # 3. 구조 정규화
        text = self.normalize_structure(text)
        
        # 4. 섹션 감지
        sections = self.detect_sections(text)
        
        # 5. 정규화된 결과 반환
        normalized_doc = {
            'file_name': doc_data.get('file_name', ''),
            'original_text': doc_data.get('full_text', ''),
            'normalized_text': text,
            'sections': sections,
            'metadata': {
                'total_sections': len(sections),
                'has_tables': any(section.get('type') == 'table' for section in sections),
                'has_lists': any(section.get('type') == 'list' for section in sections),
            }
        }
        
        return normalized_doc
    
    # ============================================================================
    # Text Cleaning
    # ============================================================================
    
    def clean_text(self, text: str) -> str:
        """기본 텍스트 정리 (개선됨)"""
        if not text:
            return ""

        # 1. 앞뒤 공백 제거
        text = text.strip()

        # 2. 제어 문자 제거
        text = re.sub(r'[\u0001-\u0008\u000B\u000C\u000E-\u001F\u007F]', '', text)

        # 3. 숨겨진 레이어 텍스트 제거 (PDF에서 흔한 노이즈)
        text = self._remove_hidden_layer_patterns(text)

        # 4. OCR 잡음 제거 (한글, 영문, 숫자, 기본 문장부호만 유지)
        text = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-/]', ' ', text)

        # 5. 반복 문자 정리 (3번 이상 반복되는 문자를 1번으로)
        text = re.sub(r'(.)\1{2,}', r'\1', text)

        # 6. 공백 정리 (문단 구조 보존)
        text = re.sub(r'[ \t]+', ' ', text)  # 공백과 탭 정리
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 여러 줄바꿈 정리

        # 7. 각 라인의 앞뒤 공백 제거
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines]
        text = '\n'.join(cleaned_lines)

        return text

    def _remove_hidden_layer_patterns(self, text: str) -> str:
        """숨겨진 레이어 텍스트 패턴 제거"""
        # PDF에서 자주 나타나는 숨겨진 레이어 텍스트 패턴
        hidden_patterns = [
            r'글로벌서울.*?SeoulMyHope.*?온라인\s*상담알림소통',
            r'서울특별시\s+글로벌서울.*?청년·신혼부부\s+지원행복주택',
            r'로그인주거\s+정책임대/분양\s+정보청년·신혼부부\s+지원',
        ]

        for pattern in hidden_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)

        return text
    
    def remove_headers_footers(self, text: str) -> str:
        """헤더/푸터 제거"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 줄의 앞뒤 공백만 제거 (들여쓰기 보존)
            original_line = line
            line = line.strip()
            
            # 빈 줄은 유지 (원래 들여쓰기 포함)
            if not line:
                cleaned_lines.append(original_line)
                continue
            
            # 페이지 번호 제거
            if re.match(r'^\s*\d+\s*$', line):
                continue
            
            # 헤더/푸터 패턴 제거
            if re.match(r'^(서울특별시|서울시|제\d+호|공고|붙임\d*)\s*$', line):
                continue
            
            # 너무 짧은 줄 (3자 이하) 제거 (단, 숫자나 특수문자가 아닌 경우)
            if len(line) <= 3 and not re.match(r'^[\d\s\-•·▪▫◦‣⁃]+$', line):
                continue
            
            # 원래 들여쓰기 보존하여 추가
            cleaned_lines.append(original_line)
        
        return '\n'.join(cleaned_lines)
    
    # ============================================================================
    # Text Structure Normalization
    # ============================================================================
    
    def normalize_structure(self, text: str) -> str:
        """문서 구조 정규화"""
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # 원래 들여쓰기 보존
            original_line = line
            line_stripped = line.strip()
            
            if not line_stripped:
                normalized_lines.append(original_line)
                continue
            
            # 불릿 포인트 정규화 (들여쓰기 보존) - 다양한 불릿포인트 지원
            if re.match(r'^[\s]*[•·▪▫□ㅇ◦‣⁃]\s*', line_stripped):
                # 들여쓰기 부분 추출
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                line = re.sub(r'^[\s]*[•·▪▫□ㅇ◦‣⁃]\s*', f'{indent_str}• ', line)
            
            # 대시 포인트 정규화 (들여쓰기 보존)
            elif re.match(r'^[\s]*[-–—]\s*', line_stripped):
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                line = re.sub(r'^[\s]*[-–—]\s*', f'{indent_str}- ', line)
            
            # 번호 포인트 정규화 (들여쓰기 보존)
            elif re.match(r'^[\s]*\d+[\.\)]\s*', line_stripped):
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                line = re.sub(r'^[\s]*\d+[\.\)]\s*', lambda m: f'{indent_str}{m.group(0).strip()}', line)
            
            # 리스트 항목 감지 및 불릿포인트 자동 추가
            elif self._is_list_item(line_stripped):
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                line = f'{indent_str}• {line_stripped}'
            
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    # ============================================================================
    # Section Detection and Parsing
    # ============================================================================
    
    def detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """문서에서 섹션들을 감지하고 분류 (TableProcessor 통합)"""
        if not text:
            return []
        
        # 문단 단위로 분할 (FAQ 형식 우선 처리)
        paragraphs = self._split_into_paragraphs(text)
        
        sections = []
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            # 문단 타입 감지
            paragraph_type = self._detect_paragraph_type(paragraph)
            
            # 제목 추출
            title = self._extract_paragraph_title(paragraph)
            
            # 표인 경우 TableProcessor로 고급 처리
            if paragraph_type == 'table':
                content = self._process_table_section(paragraph)
            else:
                content = [paragraph]
            
            section = {
                'id': f"section_{i+1}",
                'type': paragraph_type,
                'title': title,
                'content': content,
                'original_text': paragraph,
                'word_count': len(paragraph.split()),
                'char_count': len(paragraph)
            }
            
            sections.append(section)
        
        return sections
    
    def _process_table_section(self, table_text: str) -> List[Dict[str, Any]]:
        """표 섹션을 TableProcessor로 고급 처리"""
        try:
            from backend.services.vector_db.jina.table_processor import TableProcessor
            processor = TableProcessor()
            
            # 1. 기본 JSON 변환
            json_result = processor.process_table(table_text)
            
            # 2. CSV 변환
            csv_result = processor.convert_to_csv(table_text)
            
            # 3. 청킹 (너무 큰 표인 경우)
            chunks = processor.chunk_table_by_width(table_text, max_width=100)
            
            # 결과를 구조화된 형태로 반환
            processed_content = []
            
            # 기본 행 단위 분할
            rows = self._split_table_into_rows(table_text)
            processed_content.extend(rows)
            
            # 추가 메타데이터
            if json_result and 'table_type' in json_result:
                processed_content.append({
                    'metadata': {
                        'table_type': json_result['table_type'],
                        'columns': json_result.get('columns', []),
                        'has_csv': bool(csv_result and not csv_result.startswith("CSV 변환 오류")),
                        'chunk_count': len(chunks) if chunks else 1
                    }
                })
            
            return processed_content
            
        except Exception as e:
            logger.warning(f"표 고급 처리 실패, 기본 방식 사용: {str(e)}")
            # 기본 방식으로 폴백
            return self._split_table_into_rows(table_text)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """텍스트를 문단 단위로 분할 (FAQ/QA 형식 우선 처리)"""
        if not text:
            return []
        
        # FAQ 형식 감지 및 처리
        if self._is_faq_format(text):
            return self._process_faq_format(text)
        
        # 빈 줄로 문단 구분 (원래 줄바꿈 보존)
        paragraphs = []
        current_paragraph = []
        
        for line in text.split('\n'):
            if line.strip():  # 빈 줄이 아닌 경우
                current_paragraph.append(line)  # 원래 들여쓰기 보존
            else:  # 빈 줄인 경우 - 문단 구분자
                if current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []
        
        # 마지막 문단 처리
        if current_paragraph:
            paragraphs.append('\n'.join(current_paragraph))
        
        return paragraphs
    
    def _is_faq_format(self, text: str) -> bool:
        """FAQ/QA 형식인지 감지"""
        # FAQ 패턴들
        faq_patterns = [
            r'구분\s*답\s*변',  # "구분답변" 패턴
            r'질문\s*내용',     # "질문내용" 패턴
            r'질문\s*답변',
            r'Q\d+\.',          # "Q1.", "Q2." 패턴
            r'Q\s*:\s*.*\s*A\s*:',
            r'문의\s*답변',
            r'신청\s*절차',
            r'언제\s*할\s*수\s*있나요\?',
            r'어떻게\s*되나요\?',
            r'무엇인가요\?',
            r'가능한가요\?',
            r'하나요\?',
        ]

        for pattern in faq_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _process_faq_format(self, text: str) -> List[str]:
        """FAQ 형식을 Q&A로 구조화"""
        paragraphs = []

        # Q1., Q2. 패턴 처리 (가장 명확한 형식)
        if re.search(r'Q\d+\.', text):
            paragraphs = self._process_q_number_format(text)
        # "구분답변" 패턴 처리
        elif '구분답변' in text:
            paragraphs = self._process_guibun_dabbyeon_format(text)
        # "질문내용" 패턴 처리
        elif '질문내용' in text:
            paragraphs = self._process_question_content_format(text)
        else:
            # 일반 FAQ 형식 처리 - 재귀 방지
            paragraphs = self._split_text_into_paragraphs_basic(text)

        return paragraphs

    def _process_q_number_format(self, text: str) -> List[str]:
        """Q1., Q2. 형식 처리"""
        paragraphs = []

        # Q1., Q2. 패턴으로 분할
        qa_blocks = re.split(r'(Q\d+\.)', text)

        for i in range(1, len(qa_blocks), 2):
            if i + 1 < len(qa_blocks):
                question = qa_blocks[i].strip()
                answer = qa_blocks[i + 1].strip()

                if question and answer:
                    paragraphs.append(f"**{question}**")
                    paragraphs.append(f"**답변:** {self._clean_faq_answer(answer)}")

        return paragraphs

    def _process_guibun_dabbyeon_format(self, text: str) -> List[str]:
        """구분답변 형식 처리 - 완전히 새로 작성"""
        paragraphs = []
        
        # "구분답변" 이후의 텍스트만 처리
        if '구분답변' in text:
            parts = text.split('구분답변', 1)
            if len(parts) > 1:
                text = parts[1]

        # 질문과 답변을 더 정확하게 분리
        lines = text.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 질문 패턴 감지 (더 포괄적)
            is_question = (
                line.endswith('?') or
                line.endswith('하나요') or
                line.endswith('되나요') or
                line.endswith('인가요') or
                line.endswith('가능한가요') or
                line.endswith('있나요') or
                line.endswith('되나요') or
                ('어떻게' in line and ('?' in line or '하나요' in line)) or
                ('언제' in line and ('?' in line or '하나요' in line)) or
                ('무엇' in line and ('?' in line or '하나요' in line)) or
                ('신청' in line and ('?' in line or '하나요' in line)) or
                ('발급' in line and ('?' in line or '하나요' in line)) or
                ('가입' in line and ('?' in line or '하나요' in line)) or
                ('지원' in line and ('?' in line or '하나요' in line)) or
                ('대출' in line and ('?' in line or '하나요' in line)) or
                ('절차' in line and ('?' in line or '하나요' in line)) or
                ('방법' in line and ('?' in line or '하나요' in line)) or
                ('조건' in line and ('?' in line or '하나요' in line)) or
                ('요건' in line and ('?' in line or '하나요' in line))
            )

            if is_question:
                # 이전 Q&A 저장
                if current_question and current_answer:
                    paragraphs.append(f"**질문:** {current_question}")
                    paragraphs.append(f"**답변:** {self._clean_faq_answer(' '.join(current_answer))}")

                current_question = line
                current_answer = []
            else:
                if current_question:
                    current_answer.append(line)

        # 마지막 Q&A 추가
        if current_question and current_answer:
            paragraphs.append(f"**질문:** {current_question}")
            paragraphs.append(f"**답변:** {self._clean_faq_answer(' '.join(current_answer))}")

        return paragraphs

    def _process_question_content_format(self, text: str) -> List[str]:
        """질문내용 형식 처리"""
        paragraphs = []

        # 질문내용 표에서 질문들 추출
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and ('Q' in line or '?' in line):
                # 질문 정리
                cleaned_question = self._clean_faq_question(line)
                if cleaned_question:
                    paragraphs.append(f"**질문:** {cleaned_question}")

        return paragraphs

    def _clean_faq_question(self, question: str) -> str:
        """FAQ 질문 내용 정리"""
        # 불필요한 접두사 제거
        question = re.sub(r'^Q\d+\.\s*', '', question)
        question = re.sub(r'^\d+\.\s*', '', question)

        # 질문 마무리
        if not question.endswith('?'):
            question += '?'

        return question.strip()

    def _split_text_into_paragraphs_basic(self, text: str) -> List[str]:
        """기본 문단 분할 (재귀 방지용)"""
        if not text:
            return []

        # 빈 줄로 문단 구분
        paragraphs = []
        current_paragraph = []

        for line in text.split('\n'):
            if line.strip():  # 빈 줄이 아닌 경우
                current_paragraph.append(line)  # 원래 들여쓰기 보존
            else:  # 빈 줄인 경우 - 문단 구분자
                if current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []

        # 마지막 문단 처리
        if current_paragraph:
            paragraphs.append('\n'.join(current_paragraph))

        return paragraphs
    
    def _clean_faq_answer(self, answer: str) -> str:
        """FAQ 답변 내용 정리"""
        # 불필요한 접두사 제거
        answer = re.sub(r'^답\s*변\s*', '', answer)
        answer = re.sub(r'^변\s*', '', answer)
        
        # 문장 단위로 정리
        sentences = re.split(r'[.!?]', answer)
        cleaned_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:  # 의미있는 문장만
                cleaned_sentences.append(sentence)
        
        return '. '.join(cleaned_sentences) + '.' if cleaned_sentences else ""
    
    def _is_list_item(self, text: str) -> bool:
        """리스트 항목인지 판단"""
        # 이미 불릿포인트나 번호가 있는 경우 제외
        if re.match(r'^[•·▪▫□ㅇ◦‣⁃\-–—]\s*', text) or re.match(r'^\d+[\.\)]\s*', text):
            return False
        
        # 콜론으로 끝나는 제목
        if re.match(r'^[가-힣\s]+:$', text):
            return True
        
        # 짧은 설명문 (30자 이하)이고 특정 패턴
        if len(text) <= 30 and not re.match(r'^[A-Z\s]+$', text):
            # 특징, 조건, 요건 등의 키워드 포함
            list_keywords = [
                '특징', '조건', '요건', '대상', '자격', '기준', '방법', '절차',
                '장점', '혜택', '지원', '제공', '서비스', '기능', '특성',
                '기간', '규모', '비용', '금액', '혜택', '혜택', '혜택'
            ]
            
            for keyword in list_keywords:
                if keyword in text:
                    return True
        
        # ":"로 끝나는 설명문
        if text.endswith(':') and len(text) <= 50:
            return True
        
        return False
    
    def _is_table_header(self, text: str) -> bool:
        """표 헤더인지 판단"""
        # 표 헤더 패턴들
        table_header_patterns = [
            r'^단\s*계\s*세\s*부\s*내\s*용\s*주\s*관$',
            r'^소\s*득\s*유\s*형\s*세\s*부\s*내\s*용$',
            r'^구\s*분\s*.*가구.*$',
            r'^담당부서.*연락처.*$',
            r'^.*단계.*세부내용.*주관.*$',
            r'^.*구분.*내용.*$',
            r'^.*항목.*내용.*$',
            r'^.*구분.*.*가구.*$'
        ]
        
        for pattern in table_header_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    # ============================================================================
    # Text Type Detection
    # ============================================================================
    
    def _detect_paragraph_type(self, paragraph: str) -> str:
        """문단 타입 감지"""
        if self._is_markdown_table(paragraph):
            return 'table'
        elif self._is_list(paragraph):
            return 'list'
        elif self._is_title(paragraph):
            return 'title'
        else:
            return 'text'
    
    def _optimize_paragraph_size(self, paragraph: str) -> List[str]:
        """문단 크기를 200-800자 범위로 최적화"""
        if len(paragraph) <= 800:
            return [paragraph]
        
        # 문장 단위로 분할 시도
        sentences = self._split_into_sentences(paragraph)
        if not sentences:
            return [paragraph]
        
        optimized = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # 현재 청크에 추가했을 때 800자를 초과하면 새 청크 시작
            if current_length + sentence_length > 800 and current_chunk:
                optimized.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # 마지막 청크 추가
        if current_chunk:
            optimized.append(' '.join(current_chunk))
        
        return optimized
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """문장 단위로 분할 (NLTK 활용)"""
        if not text:
            return []

        # NLTK 사용 가능 시
        if self.nltk_available and self.nltk:
            try:
                # NLTK의 sent_tokenize 사용
                sentences = self.nltk.sent_tokenize(text, language='english')

                # 한국어 특화 후처리
                refined_sentences = []
                for sent in sentences:
                    # 너무 짧은 문장 필터링 (5자 미만)
                    if len(sent.strip()) < 5:
                        continue

                    # 문장 정리
                    sent = sent.strip()

                    # 한국어 문장 구분 기호 처리
                    # 예: "입니다." "습니다." "됩니다." 등으로 끝나는 경우
                    if any(sent.endswith(ending) for ending in ['다.', '요.', '요?', '까?', '나요?', '습니다.', '입니다.']):
                        refined_sentences.append(sent)
                    else:
                        refined_sentences.append(sent)

                return refined_sentences

            except Exception as e:
                logger.warning(f"NLTK 문장 분리 실패: {str(e)}. 기본 방식 사용")

        # 기본 방식 (NLTK 없을 때)
        # 한국어 문장 구분자를 고려한 분할
        sentences = re.split(r'(?<=[.!?])\s+(?=[가-힣A-Z])', text)

        # 추가 정제
        refined = []
        for sent in sentences:
            sent = sent.strip()
            if sent and len(sent) >= 5:
                refined.append(sent)

        return refined

    def tokenize_korean_text(self, text: str) -> List[str]:
        """한국어 텍스트를 토큰화 (NLTK 활용)"""
        if not text:
            return []

        if self.nltk_available and self.nltk:
            try:
                # 단어 토큰화
                tokens = self.nltk.word_tokenize(text)

                # 한국어 특화 필터링
                korean_tokens = []
                for token in tokens:
                    # 한글, 영문, 숫자만 유지
                    if re.match(r'^[가-힣a-zA-Z0-9]+$', token):
                        korean_tokens.append(token)

                return korean_tokens

            except Exception as e:
                logger.warning(f"NLTK 토큰화 실패: {str(e)}. 기본 방식 사용")

        # 기본 방식: 공백 기반 분리
        return text.split()

    def remove_stopwords_korean(self, tokens: List[str]) -> List[str]:
        """한국어 불용어 제거"""
        # 기본 한국어 불용어 목록
        korean_stopwords = {
            '이', '그', '저', '것', '수', '등', '및', '또는',
            '을', '를', '이를', '그를', '저를',
            '은', '는', '이는', '그는', '저는',
            '가', '이가', '그가', '저가',
            '에', '에서', '으로', '로', '와', '과',
            '의', '도', '만', '까지', '부터',
            '하다', '되다', '있다', '없다', '이다',
        }

        return [token for token in tokens if token not in korean_stopwords]
    
    def _split_table_into_rows(self, table_text: str) -> List[str]:
        """표를 행 단위로 분할 (TableProcessor 사용)"""
        try:
            from backend.services.vector_db.jina.table_processor import TableProcessor
            processor = TableProcessor()
            
            # TableProcessor로 표 구조 분석
            structure = processor._analyze_table_structure(table_text)
            
            # 행 단위로 변환
            rows = []
            for row in structure.rows:
                if row.cells:
                    # 셀 내용을 |로 구분하여 결합
                    row_text = '| ' + ' | '.join(cell.content for cell in row.cells) + ' |'
                    rows.append(row_text)
            
            return rows
            
        except Exception as e:
            logger.warning(f"TableProcessor를 사용한 표 분할 실패, 기본 방식 사용: {str(e)}")
            # 기본 방식으로 폴백
            return self._split_table_into_rows_basic(table_text)
    
    def _split_table_into_rows_basic(self, table_text: str) -> List[str]:
        """표를 행 단위로 분할 (기본 방식)"""
        rows = []
        lines = table_text.split('\n')
        
        current_row = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            
            # === 표 N === 헤더 무시
            if line.startswith('=== 표') and line.endswith('==='):
                continue
            
            # 빈 줄 무시
            if not line:
                continue
            
            # 마크다운 표 라인인지 확인
            if '|' in line:
                if not in_table:
                    in_table = True
                
                # 구분선 라인 무시
                if line.startswith('|---') or re.match(r'^\|[\s\-]+\|$', line):
                    continue
                
                # 행이 시작되면 현재 행을 완료하고 새 행 시작
                if line.startswith('|') and current_row:
                    # 현재 행 완료
                    complete_row = ' '.join(current_row)
                    if complete_row.strip():
                        rows.append(complete_row)
                    current_row = []
                
                # 새 행에 추가
                current_row.append(line)
            else:
                # 표가 아닌 라인이면 현재 행에 추가 (멀티라인 셀)
                if in_table and current_row:
                    current_row.append(line)
        
        # 마지막 행 처리
        if current_row:
            complete_row = ' '.join(current_row)
            if complete_row.strip():
                rows.append(complete_row)
        
        return rows
    
    def _extract_table_row_title(self, row: str) -> str:
        """표 행에서 제목 추출"""
        # 첫 번째 셀을 제목으로 사용
        cells = row.split('|')
        if len(cells) > 1:
            first_cell = cells[1].strip()  # 첫 번째 | 다음이 실제 첫 번째 셀
            if first_cell:
                return first_cell[:50] + ('...' if len(first_cell) > 50 else '')
        
        return row[:50] + ('...' if len(row) > 50 else '')
    
    def _detect_paragraph_type(self, paragraph: str) -> str:
        """문단 타입 감지"""
        # 표 감지 (마크다운 표)
        if self._is_markdown_table(paragraph):
            return 'table'
        
        # 표 감지 (=== 표 N === 패턴)
        if paragraph.startswith('=== 표') and paragraph.endswith('==='):
            return 'table'
        
        # 제목 감지
        if self._is_title(paragraph):
            return 'title'
        
        # 리스트 감지
        if self._is_list(paragraph):
            return 'list'
        
        # 일반 문단
        return 'paragraph'
    
    def _is_markdown_table(self, text):
        """마크다운 테이블인지 확인"""
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # === 표 N === 라인 제외하고 분석
        table_lines = []
        for line in lines:
            line = line.strip()
            # === 표 N === 패턴 제외
            if not (line.startswith('=== 표') and line.endswith('===')):
                table_lines.append(line)
        
        if len(table_lines) < 2:
            return False
        
        # 마크다운 테이블 패턴 확인
        pipe_lines = 0
        separator_lines = 0
        
        for line in table_lines:
            if '|' in line:
                pipe_lines += 1
                # 구분선 확인 (더 유연한 패턴)
                if re.match(r'^\|.*---.*\|$', line) or re.match(r'^\|[\s\-]+\|$', line):
                    separator_lines += 1
        
        # 2개 이상의 |가 포함된 라인이 있고, 구분선이 있으면 표로 판단
        return pipe_lines >= 2 and separator_lines >= 1
    
    def _is_title(self, text: str) -> bool:
        """제목인지 판단 (표 데이터 제외)"""
        # 표 데이터 패턴 제외
        if self._is_table_data(text):
            return False
        
        # 마크다운 볼드체 패턴 (**텍스트**)
        if re.match(r'^\*\*.*\*\*$', text.strip()):
            return True
        
        # 콜론으로 끝나는 경우
        if text.endswith(':'):
            return True
        
        # 번호로 시작하는 경우
        if re.match(r'^\d+[\.\)]\s*', text):
            return True
        
        # 짧은 텍스트 (30자 이하)이고 특정 패턴
        if len(text) <= 30:
            # 특정 키워드 포함
            title_keywords = [
                '개요', '조건', '요건', '절차', '방법', '내용', '안내', '지원', '혜택',
                '대상', '자격', '기준', '기간', '규모', '비용', '금액', '혜택',
                '신청', '접수', '제출', '서류', '문서', '확인', '사항'
            ]
            if any(keyword in text for keyword in title_keywords):
                return True
            
            # 한 줄로만 구성된 경우
            if '\n' not in text:
                return True
        
        return False
    
    def _is_table_data(self, text: str) -> bool:
        """표 데이터인지 판단"""
        # 숫자와 하이픈이 많이 포함된 경우 (표 데이터 패턴)
        if re.search(r'\d+.*[-–—].*\d+', text):
            return True
        
        # 지역명 + 숫자 패턴 (예: "수도권 150백만원")
        if re.search(r'(수도권|광역시|기타|서울|경기|인천).*\d+', text):
            return True
        
        # 구분 + 숫자 패턴 (예: "구분 수도권 광역시")
        if re.search(r'구분.*\d+', text):
            return True
        
        return False
    
    def _is_list(self, text: str) -> bool:
        """리스트인지 판단"""
        # 불릿포인트나 번호로 시작하는 경우
        if re.match(r'^[•·▪▫□◦‣⁃\-–—]\s*', text) or re.match(r'^\d+[\.\)]\s*', text):
            return True
        
        # 여러 줄에 걸친 리스트인지 확인
        lines = text.split('\n')
        if len(lines) > 1:
            list_count = 0
            for line in lines:
                if re.match(r'^[•·▪▫□◦‣⁃\-–—]\s*', line.strip()) or re.match(r'^\d+[\.\)]\s*', line.strip()):
                    list_count += 1
            
            # 50% 이상이 리스트 패턴이면 리스트로 판단
            if list_count / len(lines) >= 0.5:
                return True
        
        return False
    
    def _extract_paragraph_title(self, paragraph: str) -> str:
        """문단에서 제목 추출"""
        lines = paragraph.split('\n')
        
        # 첫 번째 줄이 제목인지 확인
        first_line = lines[0].strip()
        if self._is_title(first_line):
            return first_line
        
        # 문단의 첫 50자를 제목으로 사용
        return paragraph[:50] + ('...' if len(paragraph) > 50 else '')
    
    def detect_sections_old(self, text: str) -> List[Dict[str, Any]]:
        """기존 섹션 감지 (비활성화)"""
        lines = text.split('\n')
        sections = []
        current_section = None
        
        for i, line in enumerate(lines):
            # 들여쓰기 보존하면서 제목 감지
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # 표 감지
            if line_stripped.startswith('=== 표'):
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'title': line_stripped,
                    'level': 2,  # 표는 2단계 제목
                    'content': [],
                    'start_line': i,
                    'indent': 0,
                    'type': 'table'
                }
                continue
            
            # 마크다운 테이블 라인 감지 (개선)
            if line_stripped.startswith('|') and '|' in line_stripped[1:]:
                if current_section and current_section.get('type') == 'table':
                    current_section['content'].append(line)
                else:
                    # 표 섹션이 없으면 새로 생성
                    if current_section:
                        sections.append(current_section)
                    
                    current_section = {
                        'title': '표',
                        'level': 2,
                        'content': [line],
                        'start_line': i,
                        'indent': 0,
                        'type': 'table'
                    }
                continue
            
            # 표 헤더 패턴 감지 (단계, 세부내용, 주관 등)
            if self._is_table_header(line_stripped):
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'title': line_stripped,
                    'level': 2,
                    'content': [],
                    'start_line': i,
                    'indent': 0,
                    'type': 'table_header'
                }
                continue
            
            # 제목 패턴 감지
            title_patterns = [
                r'^\d+\.\s+.+',  # 1. 제목
                r'^[가-힣\s]+:$',  # 제목:
                r'^[A-Z\s]+$',  # 대문자 제목
                r'^[가-힣\s]{2,20}$',  # 짧은 한글 제목
            ]
            
            is_title = any(re.match(pattern, line_stripped) for pattern in title_patterns)
            
            if is_title:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)
                
                # 새 섹션 시작
                current_section = {
                    'title': line_stripped,
                    'level': self._get_title_level(line_stripped),
                    'content': [],
                    'start_line': i,
                    'indent': len(line) - len(line.lstrip()),  # 들여쓰기 정보 보존
                    'type': 'text'
                }
            else:
                if current_section:
                    current_section['content'].append(line)  # 원래 들여쓰기 보존
                else:
                    # 제목이 없는 경우 기본 섹션 생성
                    if not sections:
                        sections.append({
                            'title': '본문',
                            'level': 0,
                            'content': [line],
                            'start_line': i,
                            'indent': 0,
                            'type': 'text'
                        })
                    else:
                        sections[-1]['content'].append(line)
        
            # 마지막 섹션 저장
            if current_section:
                sections.append(current_section)
            
            # 의미 단위 기반 섹션 그룹화 (현재 비활성화)
            # return self._group_related_sections(sections)
            return sections
    
    def _group_related_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """관련된 섹션들을 그룹화하여 의미 단위로 통합"""
        if not sections:
            return sections
        
        grouped_sections = []
        current_group = None
        
        for section in sections:
            # 현재 섹션이 그룹화 가능한지 확인
            if self._should_group_with_previous(section, current_group):
                # 이전 그룹에 추가
                if current_group:
                    current_group['content'].extend(section['content'])
                    # 제목 업데이트 (더 구체적인 제목으로)
                    if len(section['title']) > len(current_group['title']):
                        current_group['title'] = section['title']
            else:
                # 새 그룹 시작
                if current_group:
                    grouped_sections.append(current_group)
                
                current_group = {
                    'title': section['title'],
                    'level': section['level'],
                    'content': section['content'].copy(),
                    'start_line': section['start_line'],
                    'indent': section['indent'],
                    'type': section.get('type', 'text')
                }
        
        # 마지막 그룹 추가
        if current_group:
            grouped_sections.append(current_group)
        
        return grouped_sections
    
    def _should_group_with_previous(self, current_section: Dict[str, Any], previous_group: Dict[str, Any]) -> bool:
        """현재 섹션을 이전 그룹과 합칠지 판단"""
        if not previous_group:
            return False
        
        # 표나 표 헤더는 그룹화하지 않음
        if current_section.get('type') in ['table', 'table_header']:
            return False
        
        # 이전 그룹이 표인 경우 그룹화하지 않음
        if previous_group.get('type') in ['table', 'table_header']:
            return False
        
        # 현재 섹션이 너무 작은 경우 (1줄만)
        if len(current_section['content']) <= 1:
            # 이전 그룹도 작은 경우에만 그룹화 (3줄 이하)
            if len(previous_group['content']) <= 3:
                return True
        
        # 제목이 유사한 경우 (키워드 기반)
        if self._are_titles_related(current_section['title'], previous_group['title']):
            return True
        
        return False
    
    def _are_titles_related(self, title1: str, title2: str) -> bool:
        """두 제목이 관련되어 있는지 판단"""
        # 공통 키워드가 있는지 확인
        keywords1 = set(title1.split())
        keywords2 = set(title2.split())
        
        # 공통 키워드가 1개 이상 있으면 관련성 있음
        common_keywords = keywords1.intersection(keywords2)
        if len(common_keywords) > 0:
            return True
        
        # 제목이 너무 짧은 경우 (1단어) 그룹화
        if len(keywords1) <= 1 and len(keywords2) <= 1:
            return True
        
        return False
    
    def _get_title_level(self, title: str) -> int:
        """제목 레벨 결정"""
        if re.match(r'^\d+\.\s+', title):
            return 1
        elif re.match(r'^\d+\.\d+\.\s+', title):
            return 2
        elif re.match(r'^\d+\.\d+\.\d+\.\s+', title):
            return 3
        elif re.match(r'^[가-힣\s]+:$', title):
            return 1
        else:
            return 0
    
    def normalize_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """문서 전체 정규화"""
        if 'full_text' not in doc_data:
            return doc_data
        
        text = doc_data['full_text']
        
        # 1. 기본 정리
        text = self.clean_text(text)
        
        # 2. 헤더/푸터 제거
        text = self.remove_headers_footers(text)
        
        # 3. 구조 정규화
        text = self.normalize_structure(text)
        
        # 4. 섹션 감지
        sections = self.detect_sections(text)
        
        # 5. 정규화된 결과 반환
        normalized_doc = {
            'file_name': doc_data.get('file_name', ''),
            'original_text': doc_data.get('full_text', ''),
            'normalized_text': text,
            'sections': sections,
            'metadata': {
                'original_length': len(doc_data.get('full_text', '')),
                'normalized_length': len(text),
                'section_count': len(sections),
                'processing_timestamp': doc_data.get('processing_timestamp', '')
            }
        }
        
        return normalized_doc
    
    def process_json_files(self, input_dir: str, output_dir: str) -> List[Dict[str, Any]]:
        """JSON 파일들 일괄 처리"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        json_files = list(input_path.glob("*.json"))
        logger.info(f"처리할 JSON 파일 수: {len(json_files)}")
        
        results = []
        
        for json_file in json_files:
            logger.info(f"정규화 중: {json_file.name}")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # 개별 문서 정규화
                if 'files' in doc_data:
                    # 통합 파일인 경우
                    normalized_files = []
                    for file_data in doc_data['files']:
                        normalized_file = self.normalize_document(file_data)
                        normalized_files.append(normalized_file)
                    
                    result = {
                        'total_files': doc_data.get('total_files', 0),
                        'successful_files': doc_data.get('successful_files', 0),
                        'failed_files': doc_data.get('failed_files', 0),
                        'files': normalized_files
                    }
                else:
                    # 개별 파일인 경우
                    result = self.normalize_document(doc_data)
                
                # 결과 저장
                output_file = output_path / f"{json_file.stem}_normalized.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                results.append(result)
                logger.info(f"저장 완료: {output_file}")
                
            except Exception as e:
                logger.error(f"파일 처리 중 오류 발생 {json_file.name}: {str(e)}")
                continue
        
        return results
    
    # ============================================================================
    # Table Processing (Moved from Extractor)
    # ============================================================================
    
    def convert_table_to_markdown(self, table) -> str:
        """표를 마크다운 형식으로 변환"""
        if not table or len(table) < 2:
            return ""
        
        # 표 데이터 정리
        cleaned_table = self._clean_table_data(table)
        if not cleaned_table:
            return ""
        
        # 마크다운 테이블 생성
        markdown_lines = []
        
        # 헤더 행
        if cleaned_table:
            header = "| " + " | ".join(str(cell) for cell in cleaned_table[0]) + " |"
            markdown_lines.append(header)
            
            # 구분선
            separator = "| " + " | ".join("---" for _ in cleaned_table[0]) + " |"
            markdown_lines.append(separator)
            
            # 데이터 행들
            for row in cleaned_table[1:]:
                if row:  # 빈 행이 아닌 경우만
                    row_line = "| " + " | ".join(str(cell) for cell in row) + " |"
                    markdown_lines.append(row_line)
        
        return "\n".join(markdown_lines)
    
    def _clean_table_data(self, table) -> list:
        """표 데이터 정리"""
        cleaned = []
        for row in table:
            if row:  # 빈 행이 아닌 경우
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        cleaned_row.append(str(cell).strip())
                cleaned.append(cleaned_row)
        return cleaned
    
    def post_process_tables(self, tables: List[List[List[str]]]) -> List[List[List[str]]]:
        """표 후처리로 품질 개선 -> 빈 행 제거 + None값을 빈 문자열로 변환"""
        processed_tables = []
        
        for table in tables:
            if not table:
                continue
            
            processed_table = []
            for row in table:
                if not row:
                    continue
                
                # None 값을 빈 문자열로 변환
                processed_row = [cell if cell is not None else "" for cell in row]
                
                # 빈 행 제거
                if any(cell.strip() for cell in processed_row):
                    processed_table.append(processed_row)
            
            if processed_table:
                processed_tables.append(processed_table)
        
        return processed_tables

def main():
    """메인 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent
    input_dir = base_dir / "data" / "vector_db" / "raw_json"
    output_dir = base_dir / "data" / "vector_db" / "normalized"
    
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    
    # 정규화 처리기 생성 및 실행
    normalizer = TextNormalizer()
    results = normalizer.process_json_files(str(input_dir), str(output_dir))
    
    print(f"\n=== 정규화 완료 ===")
    print(f"처리된 파일 수: {len(results)}")

if __name__ == "__main__":
    main()
