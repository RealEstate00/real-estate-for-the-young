#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF OCR 처리 스크립트
finance_support 디렉토리의 PDF 파일들을 OCR 처리하여 텍스트를 추출합니다.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
import pdfplumber
from tqdm import tqdm
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFOCRProcessor:
    """PDF OCR 처리 클래스"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ============================================================================
    # Main Extraction Methods
    # ============================================================================
        
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """PDF에서 텍스트 추출 (레이아웃 정보 보존)"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_content = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # 레이아웃 정보를 활용한 텍스트 추출
                    page_text = self._extract_text_with_layout(page)
                    
                    if page_text:
                        text_content.append(page_text)
                    else:
                        logger.warning(f"페이지 {page_num}에서 텍스트를 추출할 수 없습니다: {pdf_path.name}")
                
                return {
                    "file_name": pdf_path.name,
                    "full_text": "\n\n".join(text_content),
                }
                
        except Exception as e:
            logger.error(f"PDF 처리 중 오류 발생 {pdf_path.name}: {str(e)}")
            return {
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "error": str(e),
                "full_text": "",
            }
    
    def _extract_text_with_layout(self, page) -> str:
        """레이아웃 정보를 활용한 텍스트 추출 (개선됨)"""
        try:
            # 1. 표 추출 (중복 제거 적용)
            tables = self._extract_tables_enhanced(page)
            table_bboxes = self._get_table_bboxes(page, tables) if tables else []

            # 2. 표를 제외한 텍스트 추출
            text = self._extract_text_excluding_tables(page, table_bboxes)

            # 3. 표 내용을 마크다운으로 변환 (중복 제거)
            table_content = ""
            if tables:
                # 중복된 표 제거
                unique_tables = self._remove_duplicate_tables(tables)
                table_content = self._process_tables(unique_tables)
                logger.info(f"표 {len(unique_tables)}개 추출됨 (원본 {len(tables)}개에서 중복 제거)")

            # 4. 텍스트와 표를 결합
            if text.strip() and table_content.strip():
                return f"{text}\n\n{table_content}"
            elif table_content.strip():
                return table_content
            else:
                return text

        except Exception as e:
            logger.warning(f"레이아웃 기반 추출 실패, 기본 추출 사용: {str(e)}")
            return page.extract_text() or ""

    def _get_table_bboxes(self, page, tables) -> List[Dict[str, float]]:
        """추출된 표들의 경계 박스(bbox) 정보 추출"""
        bboxes = []
        try:
            # pdfplumber의 find_tables로 표 객체 가져오기
            table_objects = page.find_tables()
            for table_obj in table_objects:
                if hasattr(table_obj, 'bbox'):
                    bboxes.append({
                        'x0': table_obj.bbox[0],
                        'y0': table_obj.bbox[1],
                        'x1': table_obj.bbox[2],
                        'y1': table_obj.bbox[3]
                    })
        except Exception as e:
            logger.warning(f"표 bbox 추출 실패: {str(e)}")
        return bboxes

    def _remove_duplicate_tables(self, tables: List[List[List[str]]]) -> List[List[List[str]]]:
        """중복된 표 제거"""
        if not tables:
            return []

        unique_tables = []
        seen_tables = set()

        for table in tables:
            # 표의 내용을 문자열로 변환하여 해시
            table_str = str(table)
            table_hash = hash(table_str)

            if table_hash not in seen_tables:
                seen_tables.add(table_hash)
                unique_tables.append(table)

        return unique_tables

    def _extract_text_excluding_tables(self, page, table_bboxes: List[Dict[str, float]]) -> str:
        """표 영역을 제외한 텍스트 추출"""
        try:
            chars = page.chars
            if not chars:
                return ""

            # 표 영역에 속하지 않는 문자만 필터링
            filtered_chars = []
            for char in chars:
                char_x, char_y = char['x0'], char['top']

                # 표 영역 확인
                is_in_table = False
                for bbox in table_bboxes:
                    if (bbox['x0'] <= char_x <= bbox['x1'] and
                        bbox['y0'] <= char_y <= bbox['y1']):
                        is_in_table = True
                        break

                if not is_in_table:
                    filtered_chars.append(char)

            if not filtered_chars:
                return ""

            # 시각적으로 보이는 텍스트만 필터링
            visible_chars = self._filter_visible_text(filtered_chars)

            # 문자들을 라인으로 그룹화
            lines = self._group_chars_into_lines(visible_chars)

            # 라인들을 문단으로 그룹화
            paragraphs = self._group_lines_into_paragraphs(lines)

            # 문단 텍스트 생성
            paragraph_texts = []
            for para in paragraphs:
                para_text = " ".join(para)
                if para_text.strip():
                    paragraph_texts.append(para_text.strip())

            return "\n\n".join(paragraph_texts)

        except Exception as e:
            logger.warning(f"표 제외 텍스트 추출 실패: {str(e)}")
            return ""
    
    # ============================================================================
    # Table Extraction
    # ============================================================================
    
    def _extract_tables_enhanced(self, page) -> List[List[List[str]]]:
        """개선된 표 추출"""
        try:
            # 1. 기본 표 추출
            basic_tables = page.extract_tables()
            
            # 2. 다양한 전략으로 표 추출 시도
            strategies = [
                # 전략 1: 선 기반 추출
                {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                },
                # 전략 2: 텍스트 기반 추출
                {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "text_tolerance": 3,
                    "text_x_tolerance": 3,
                    "text_y_tolerance": 3,
                },
                # 전략 3: 혼합 전략
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                    "join_tolerance": 5,
                }
            ]
            
            best_tables = basic_tables
            best_score = self._score_table_quality(basic_tables)
            
            # 각 전략 시도
            for i, strategy in enumerate(strategies):
                try:
                    tables = page.extract_tables(table_settings=strategy)
                    if tables:
                        score = self._score_table_quality(tables)
                        if score > best_score:
                            best_tables = tables
                            best_score = score
                            logger.info(f"전략 {i+1}이 더 나은 결과 제공 (점수: {score})")
                except Exception as e:
                    logger.warning(f"전략 {i+1} 실패: {str(e)}")
                    continue
            
            # 3. 표 후처리로 품질 개선
            if best_tables:
                best_tables = self._post_process_tables(best_tables)
            
            return best_tables
                
        except Exception as e:
            logger.warning(f"개선된 표 추출 실패, 기본 추출 사용: {str(e)}")
            return page.extract_tables()
    
    def _score_table_quality(self, tables: List[List[List[str]]]) -> float:
        """
        표 품질 점수 계산 (개선된 기준)
        1. 구조 / 2. 빈셀 비율 / 3. 데이터 풍부성 / 4. 데이터 일관성(열 개수 동일 여부) / 5. 헤더 체크
        """
        if not tables:
            return 0.0
        
        total_score = 0.0
        for table in tables:
            if not table or len(table) < 2:  # 최소 헤더 + 1행
                continue
            
            score = 0.0
            
            # 1. 기본 구조 점수 (30점)
            if len(table) >= 2:  # 헤더 + 최소 1행
                score += 30
            
            # 2. 빈 셀 비율 점수 (40점)
            total_cells = sum(len(row) for row in table)
            empty_cells = sum(
                sum(1 for cell in row if cell is None or cell == '') 
                for row in table
            )
            if total_cells > 0:
                empty_ratio = empty_cells / total_cells
                score += (1 - empty_ratio) * 40
            
            # 3. 데이터 풍부성 점수 (20점)
            data_cells = sum(
                sum(1 for cell in row if cell and len(str(cell).strip()) > 0) 
                for row in table
            )
            if total_cells > 0:
                data_ratio = data_cells / total_cells
                score += data_ratio * 20
            
            # 4. 표 일관성 점수 (10점)
            # 모든 행이 같은 수의 열을 가지는지 확인
            if len(table) > 1:
                col_counts = [len(row) for row in table]
                if len(set(col_counts)) == 1:  # 모든 행이 같은 열 수
                    score += 10
            
            # 5. 헤더 품질 점수 (10점)
            # 첫 번째 행이 의미 있는 헤더인지 확인
            if table and table[0]:
                header_cells = [cell for cell in table[0] if cell and cell.strip()]
                if len(header_cells) >= 2:  # 최소 2개 컬럼
                    score += 10
            
            total_score += score
        
        return total_score
    
    def _post_process_tables(self, tables: List[List[List[str]]]) -> List[List[List[str]]]:
        """표 후처리로 품질 개선 (Normalizer 함수 사용)"""
        from backend.services.vector_db.jina.normalizer import TextNormalizer
        normalizer = TextNormalizer()
        return normalizer.post_process_tables(tables)
    
    def _process_tables(self, tables) -> str:
        """표를 마크다운으로 변환 (TableProcessor 사용)"""
        if not tables:
            return ""
        
        from backend.services.vector_db.jina.table_processor import TableProcessor
        processor = TableProcessor()
        
        markdown_tables = []
        for i, table in enumerate(tables, 1):
            if table:
                # 기존 방식으로 마크다운 변환
                markdown_table = self._convert_table_to_markdown(table)
                if markdown_table:
                    table_text = f"=== 표 {i} ===\n{markdown_table}"
                    markdown_tables.append(table_text)
                    
                    # TableProcessor로 추가 처리 (CSV 변환, 청킹 등)
                    try:
                        # CSV 변환 결과를 주석으로 추가
                        csv_result = processor.convert_to_csv(table_text)
                        if csv_result and not csv_result.startswith("CSV 변환 오류"):
                            markdown_tables.append(f"<!-- CSV 형식:\n{csv_result}\n-->")
                        
                        # 청킹 결과를 주석으로 추가
                        chunks = processor.chunk_table_by_width(table_text, max_width=100)
                        if chunks and len(chunks) > 1:
                            markdown_tables.append(f"<!-- 표 청킹 결과: {len(chunks)}개 청크로 분할 -->")
                    except Exception as e:
                        logger.warning(f"표 추가 처리 실패: {str(e)}")
        
        return "\n\n".join(markdown_tables)
    
    def _convert_table_to_markdown(self, table) -> str:
        """표를 마크다운 형식으로 변환 (라인별 구조 보존)"""
        if not table:
            return ""
        
        markdown_lines = []
        
        for row_idx, row in enumerate(table):
            if not row:
                continue
                
            # 각 셀의 내용을 정리하고 라인별로 분리
            processed_cells = []
            for cell in row:
                if cell:
                    # 셀 내용을 라인별로 분리하여 정리
                    cell_lines = self._process_table_cell(cell)
                    processed_cells.append(cell_lines)
                else:
                    processed_cells.append("")
            
            # 마크다운 행 생성
            if processed_cells:
                markdown_row = "| " + " | ".join(processed_cells) + " |"
                markdown_lines.append(markdown_row)
                
                # 헤더 행 다음에 구분선 추가
                if row_idx == 0:
                    separator = "|" + "|".join([" --- " for _ in processed_cells]) + "|"
                    markdown_lines.append(separator)
        
        return "\n".join(markdown_lines)
    
    def _process_table_cell(self, cell_content: str) -> str:
        """표 셀 내용을 라인별로 정리"""
        if not cell_content:
            return ""
        
        # 셀 내용을 라인별로 분리
        lines = cell_content.strip().split('\n')
        
        # 각 라인을 정리
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        # 라인들을 적절히 조합
        if len(cleaned_lines) == 1:
            return cleaned_lines[0]
        elif len(cleaned_lines) <= 3:
            # 짧은 경우 공백으로 연결
            return " ".join(cleaned_lines)
        else:
            # 긴 경우 첫 번째 라인만 사용 (요약)
            return cleaned_lines[0] + "..."
    
    def _analyze_table_structure(self, table) -> str:
        """표 구조 분석"""
        if not table or len(table) < 2:
            return "empty"
        
        # 첫 번째 행의 텍스트 비율 확인
        first_row_ratio = self._get_text_ratio(table[0])
        
        if first_row_ratio > 0.7:
            return "header_heavy"  # 헤더가 많은 표
        elif first_row_ratio < 0.3:
            return "data_heavy"    # 데이터가 많은 표
        else:
            return "balanced"      # 균형잡힌 표
    
    def _get_text_ratio(self, row) -> float:
        """행의 텍스트 비율 계산"""
        if not row:
            return 0.0
        
        text_cells = sum(1 for cell in row if cell and str(cell).strip())
        total_cells = len(row)
        
        return text_cells / total_cells if total_cells > 0 else 0.0
    
    # ============================================================================
    # Bold Text Extraction
    # ============================================================================
    
    def _extract_structured_text_with_bold(self, page, tables=None) -> str:
        """볼드체를 활용한 구조화된 텍스트 추출 (표 영역 제외)"""
        try:
            # 표 영역 확인 (매개변수로 받은 tables 사용)
            table_areas = self._get_table_areas(tables) if tables else []
            
            # 문자 객체에서 볼드체 정보 추출
            chars = page.chars
            if not chars:
                return ""
            
            # 볼드체 문자들을 그룹화하여 구조화 (표 영역 제외)
            structured_lines = self._group_chars_by_bold_and_position(chars, table_areas)
            
            if not structured_lines:
                return ""
            
            # 구조화된 텍스트로 변환
            paragraphs = []
            current_paragraph = []
            
            for line in structured_lines:
                if line['is_bold'] and line['text'].strip() and not line['is_in_table']:
                    # 볼드체 텍스트는 제목으로 처리 (표 내부 제외)
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                    paragraphs.append(f"**{line['text'].strip()}**")  # 마크다운 볼드체
                else:
                    # 일반 텍스트는 문단에 추가
                    if line['text'].strip():
                        current_paragraph.append(line['text'].strip())
            
            # 마지막 문단 처리
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            return '\n\n'.join(paragraphs)
            
        except Exception as e:
            logger.warning(f"볼드체 기반 추출 실패: {str(e)}")
            return ""
    
    def _get_table_areas(self, tables):
        """표 영역의 좌표 정보 추출"""
        table_areas = []
        for table in tables:
            if table and len(table) > 0:
                # 표의 첫 번째 행에서 좌표 정보 추출
                first_row = table[0]
                if first_row and len(first_row) > 0:
                    # 간단한 좌표 추정 (실제로는 더 정교한 방법 필요)
                    table_areas.append({
                        'x0': 0,  # 실제로는 표의 실제 좌표를 추출해야 함
                        'y0': 0,
                        'x1': 1000,
                        'y1': 1000
                    })
        return table_areas
    
    def _group_chars_by_bold_and_position(self, chars, table_areas=None):
        """문자들을 볼드체와 위치를 기준으로 그룹화 (표 영역 제외)"""
        if not chars:
            return []
        
        if table_areas is None:
            table_areas = []
        
        # y좌표 기준으로 정렬
        sorted_chars = sorted(chars, key=lambda c: (c['top'], c['x0']))
        
        lines = []
        current_line = []
        current_y = None
        y_tolerance = 5
        
        for char in sorted_chars:
            char_y = char['top']
            
            # 같은 라인인지 확인
            if current_y is None or abs(char_y - current_y) <= y_tolerance:
                current_line.append(char)
                current_y = char_y if current_y is None else current_y
            else:
                # 새 라인 시작
                if current_line:
                    line_text = self._extract_line_text_with_bold_info(current_line, table_areas)
                    if line_text['text'].strip():
                        lines.append(line_text)
                current_line = [char]
                current_y = char_y
        
        # 마지막 라인 처리
        if current_line:
            line_text = self._extract_line_text_with_bold_info(current_line, table_areas)
            if line_text['text'].strip():
                lines.append(line_text)
        
        return lines
    
    def _extract_line_text_with_bold_info(self, chars, table_areas=None):
        """문자 리스트에서 텍스트와 볼드체 정보 추출 (표 영역 확인)"""
        if not chars:
            return {'text': '', 'is_bold': False, 'is_in_table': False}
        
        if table_areas is None:
            table_areas = []
        
        # 텍스트 추출
        text = ''.join(char['text'] for char in chars)
        
        # 표 영역 내부인지 확인
        is_in_table = self._is_in_table_area(chars, table_areas)
        
        # 볼드체 여부 판단 (50% 이상이 볼드체면 볼드체로 판단)
        bold_count = sum(1 for char in chars if char.get('fontname', '').lower().find('bold') != -1)
        is_bold = bold_count / len(chars) >= 0.5
        
        return {'text': text, 'is_bold': is_bold, 'is_in_table': is_in_table}
    
    def _is_in_table_area(self, chars, table_areas):
        """문자가 표 영역 내부에 있는지 확인"""
        if not chars or not table_areas:
            return False
        
        # 문자의 평균 위치 계산
        avg_x = sum(char['x0'] for char in chars) / len(chars)
        avg_y = sum(char['top'] for char in chars) / len(chars)
        
        # 표 영역과 겹치는지 확인
        for area in table_areas:
            if (area['x0'] <= avg_x <= area['x1'] and 
                area['y0'] <= avg_y <= area['y1']):
                return True
        
        return False
    
    def _extract_text_excluding_tables(self, page, tables) -> str:
        """표 영역을 제외한 텍스트 추출"""
        try:
            # 표 영역의 좌표 정보 수집
            table_areas = []
            for table in tables:
                if table:
                    # 표의 첫 번째와 마지막 셀의 좌표로 영역 계산
                    first_cell = table[0][0] if table[0] else None
                    last_cell = table[-1][-1] if table[-1] else None
                    
                    if first_cell and last_cell:
                        # 간단한 영역 계산 (실제로는 더 정교한 계산 필요)
                        table_areas.append({
                            'x0': 0,  # 표는 보통 페이지 전체 폭 사용
                            'y0': 0,  # 표 영역 시작
                            'x1': page.width,
                            'y1': page.height  # 표 영역 끝
                        })
            
            # 문자 객체로 텍스트 추출하면서 표 영역 제외
            chars = page.chars
            if not chars:
                return ""
            
            filtered_chars = []
            for char in chars:
                char_x, char_y = char['x0'], char['top']
                
                # 표 영역에 포함되지 않는 문자만 선택
                is_in_table = False
                for area in table_areas:
                    if (area['x0'] <= char_x <= area['x1'] and 
                        area['y0'] <= char_y <= area['y1']):
                        is_in_table = True
                        break
                
                if not is_in_table:
                    filtered_chars.append(char)
            
            if not filtered_chars:
                return ""
            
            # 필터링된 문자들을 라인으로 그룹화
            lines = self._group_chars_into_lines(filtered_chars)
            paragraphs = self._group_lines_into_paragraphs(lines)
            
            paragraph_texts = []
            for para in paragraphs:
                para_text = " ".join(para)
                if para_text.strip():
                    paragraph_texts.append(para_text.strip())
            
            return "\n\n".join(paragraph_texts)
            
        except Exception as e:
            logger.warning(f"표 제외 텍스트 추출 실패: {str(e)}")
            return ""
    
    def _combine_text_and_tables(self, content_parts) -> str:
        """표와 텍스트를 결합하고 중복 제거"""
        try:
            if len(content_parts) < 2:
                return content_parts[0] if content_parts else ""
            
            # 첫 번째는 표, 두 번째는 일반 텍스트
            table_content = content_parts[0]
            text_content = content_parts[1]
            
            # 표 내용에서 추출된 텍스트와 일반 텍스트의 중복 제거
            # 표 내용이 일반 텍스트에 포함되어 있는지 확인
            table_lines = table_content.split('\n')
            text_lines = text_content.split('\n')
            
            # 중복되지 않는 텍스트 라인만 필터링
            filtered_text_lines = []
            for text_line in text_lines:
                text_line_clean = text_line.strip()
                if not text_line_clean:
                    filtered_text_lines.append(text_line)
                    continue
                
                # 표 라인과 중복되는지 확인
                is_duplicate = False
                for table_line in table_lines:
                    table_line_clean = table_line.strip()
                    if (table_line_clean and 
                        text_line_clean in table_line_clean or 
                        table_line_clean in text_line_clean):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    filtered_text_lines.append(text_line)
            
            # 필터링된 텍스트와 표 내용 결합
            filtered_text = '\n'.join(filtered_text_lines)
            
            # 표와 텍스트를 결합 (표 먼저, 그 다음 텍스트)
            if filtered_text.strip():
                return f"{table_content}\n\n{filtered_text}"
            else:
                return table_content
                
        except Exception as e:
            logger.warning(f"텍스트와 표 결합 실패: {str(e)}")
            return '\n\n'.join(content_parts)
    
    def _process_tables(self, tables) -> str:
        """표 데이터를 구조화된 텍스트로 변환"""
        processed_content = []
        
        for table_idx, table in enumerate(tables):
            if not table:
                continue
                
            processed_content.append(f"=== 표 {table_idx + 1} ===")
            
            # 표를 마크다운 테이블 형태로 변환
            markdown_table = self._convert_table_to_markdown(table)
            processed_content.append(markdown_table)
            processed_content.append("")  # 빈 줄 추가
        
        return "\n".join(processed_content)
    
    def _extract_text_preserving_layout(self, page) -> str:
        """pdfplumber 기반 텍스트 추출 (표 구조 보존)"""
        try:
            # pdfplumber로 텍스트 추출
            return self._extract_text_with_pdfplumber(page)

        except Exception as e:
            logger.warning(f"텍스트 추출 실패: {str(e)}")
            # 폴백: 기본 텍스트 추출
            return page.extract_text() or ""
    
    def _extract_text_with_pdfplumber(self, page) -> str:
        """pdfplumber를 사용한 텍스트 추출 (기존 방식)"""
        try:
            # 문자 단위로 추출하여 줄바꿈 보존
            chars = page.chars
            if not chars:
                return ""
            
            # 시각적으로 보이는 텍스트만 필터링
            visible_chars = self._filter_visible_text(chars)
            
            # 문자들을 y좌표 기준으로 라인으로 그룹화
            lines = self._group_chars_into_lines(visible_chars)
            
            # 각 라인을 텍스트로 변환
            text_lines = []
            for line_chars in lines:
                if line_chars:
                    # x좌표 기준으로 정렬하여 텍스트 순서 보장
                    sorted_chars = sorted(line_chars, key=lambda x: x['x0'])
                    line_text = ''.join(char['text'] for char in sorted_chars)
                    
                    # 빈 라인이나 공백만 있는 라인은 제외
                    if line_text.strip():
                        text_lines.append(line_text)
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.warning(f"pdfplumber 텍스트 추출 실패: {str(e)}")
            return page.extract_text() or ""
    
    def _filter_visible_text(self, chars):
        """시각적으로 보이는 텍스트만 필터링"""
        if not chars:
            return []
        
        # 폰트 크기 기준으로 필터링 (너무 작은 텍스트 제외)
        font_sizes = [char.get('size', 0) for char in chars if char.get('size')]
        if font_sizes:
            min_font_size = max(6, min(font_sizes) * 0.8)  # 최소 폰트 크기의 80%
        else:
            min_font_size = 6
        
        visible_chars = []
        for char in chars:
            # 기본 필터링 조건
            if not char.get('text') or not char['text'].strip():
                continue
            
            # 폰트 크기 필터링
            if char.get('size', 0) < min_font_size:
                continue
            
            # 투명도 필터링 (투명한 텍스트 제외)
            if char.get('non_stroking_color') and len(char['non_stroking_color']) >= 3:
                # RGB 값이 모두 1에 가까우면 투명한 텍스트
                r, g, b = char['non_stroking_color'][:3]
                if r > 0.9 and g > 0.9 and b > 0.9:
                    continue
            
            # 특정 패턴 제외 (숨겨진 레이어 텍스트 패턴)
            text = char['text']
            if any(pattern in text for pattern in [
                '글로벌서울', 'SeoulMySoul', 'SeoulMyHope', 
                '서울소식응답소', '정보공개분야별정보',
                '로그인주거', '임대/분양', '온라인 상담알림소통'
            ]):
                continue
            
            visible_chars.append(char)
        
        return visible_chars
    
    def _remove_hidden_layer_text(self, text):
        """숨겨진 레이어 텍스트 제거"""
        import re
        
        # 숨겨진 레이어 텍스트 패턴들 (정확한 패턴으로 수정)
        hidden_patterns = [
            # 첫 번째 패턴: 글로벌서울부터 시작하는 긴 텍스트
            r'서울특별시\s+글로벌서울아이디어제안숏폼챌린지영상공모전\(SeoulMySoul,SeoulMyHope\),\'25\.10\.20\.\(월\)10:0…서울소식응답소정보공개분야별정보서울소식\s+로그인주거\s+정책임대/분양\s+정보청년·신혼부부\s+지원온라인\s+상담알림소통\s+청년·신혼부부\s+지원\s+서울시\s+청년·신혼부부\s+지원\s+정보를\s+제공합니다\.\s+청년·신혼부부\s+지원행복주택',
            # 두 번째 패턴: 중복된 텍스트
            r'서울특별시\s+글로벌서울아이디어제안숏폼챌린지영상공모전\(SeoulMySoul,SeoulMyHope\),\'25\.10\.20\.\(월\)10:0…서울소식응답소정보공개분야별정보서울소식\s+로그인주거\s+정책임대/분양\s+정보청년·신혼부부\s+지원온라인\s+상담알림소통',
        ]
        
        cleaned_text = text
        
        # 각 패턴에 대해 제거
        for pattern in hidden_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
        
        # 연속된 공백 정리
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # 빈 줄 정리
        lines = cleaned_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        return '\n'.join(cleaned_lines)
    
    # ============================================================================
    # Text Grouping and Structure
    # ============================================================================
    
    def _group_chars_into_lines(self, chars):
        """문자들을 y좌표 기준으로 라인으로 그룹화"""
        if not chars:
            return []
        
        # y좌표 기준으로 정렬
        sorted_chars = sorted(chars, key=lambda x: (x['top'], x['x0']))
        
        lines = []
        current_line = []
        current_y = None
        y_tolerance = 5  # y좌표 허용 오차
        
        for char in sorted_chars:
            char_y = char['top']
            
            if current_y is None or abs(char_y - current_y) <= y_tolerance:
                # 같은 라인
                current_line.append(char)
                current_y = char_y if current_y is None else current_y
            else:
                # 새 라인 시작
                if current_line:
                    lines.append(current_line)
                current_line = [char]
                current_y = char_y
        
        # 마지막 라인 추가
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _group_lines_into_paragraphs(self, lines):
        """라인들을 문단으로 그룹화"""
        if not lines:
            return []
        
        paragraphs = []
        current_paragraph = []
        
        for line in lines:
            # 라인 텍스트 추출
            line_text = "".join(char['text'] for char in line).strip()
            
            if not line_text:
                # 빈 라인 - 문단 구분자
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = []
                continue
            
            # 제목 패턴 감지 (대문자, 번호, 특수문자 등)
            is_title = self._is_title_line(line_text)
            
            if is_title and current_paragraph:
                # 제목이면 이전 문단 종료하고 새 문단 시작
                paragraphs.append(current_paragraph)
                current_paragraph = [line]
            else:
                # 일반 텍스트 - 현재 문단에 추가
                current_paragraph.append(line)
        
        # 마지막 문단 추가
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        return paragraphs
    
    def _is_title_line(self, text):
        """라인이 제목인지 판단"""
        if not text or len(text.strip()) < 2:
            return False
        
        text = text.strip()
        
        # 제목 패턴들
        title_patterns = [
            r'^\d+\.',  # 1. 2. 3.
            r'^[IVX]+\.',  # I. II. III.
            r'^[가-힣]+$',  # 한글만
            r'^[A-Z\s]+$',  # 대문자만
            r'^제\d+',  # 제1장, 제2절
            r'^[가-힣]+\s*\(',  # 한글(괄호)
        ]
        
        import re
        for pattern in title_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _analyze_table_structure(self, table) -> str:
        """표 구조 분석"""
        if not table or len(table) < 2:
            return "simple"
        
        # 첫 번째 행과 첫 번째 열 분석
        first_row = table[0]
        first_col = [row[0] if row and len(row) > 0 else "" for row in table]
        
        # 첫 번째 행이 헤더인지 확인 (숫자나 특수문자가 적고, 텍스트가 많음)
        first_row_text_ratio = self._get_text_ratio(first_row)
        
        # 첫 번째 열이 헤더인지 확인 (구분, 대학생, 취업준비생 등)
        first_col_keywords = ['구분', '대학생', '취업준비생', '일반형', '쉐어형']
        first_col_has_keywords = any(keyword in str(cell) for cell in first_col if cell for keyword in first_col_keywords)
        
        if first_col_has_keywords and first_row_text_ratio < 0.3:
            return "header_first_column"
        elif first_row_text_ratio > 0.7:
            return "header_first_row"
        else:
            return "simple"
    
    def _get_text_ratio(self, row) -> float:
        """행의 텍스트 비율 계산"""
        if not row:
            return 0.0
        
        text_count = 0
        total_count = 0
        
        for cell in row:
            if cell is not None:
                total_count += 1
                cell_str = str(cell).strip()
                # 숫자나 특수문자가 아닌 텍스트인지 확인
                if cell_str and not cell_str.replace('.', '').replace(',', '').replace('백만원', '').replace('호', '').isdigit():
                    text_count += 1
        
        return text_count / max(total_count, 1)
    
    def _group_chars_into_lines(self, chars):
        """문자들을 y좌표 기준으로 라인으로 그룹화"""
        if not chars:
            return []
        
        # y좌표 기준으로 정렬
        sorted_chars = sorted(chars, key=lambda c: (c['top'], c['x0']))
        
        lines = []
        current_line = []
        current_y = None
        y_tolerance = 5  # y좌표 허용 오차
        
        for char in sorted_chars:
            char_y = char['top']
            
            if current_y is None or abs(char_y - current_y) <= y_tolerance:
                # 같은 라인
                current_line.append(char)
                current_y = char_y if current_y is None else current_y
            else:
                # 새 라인 시작
                if current_line:
                    lines.append(current_line)
                current_line = [char]
                current_y = char_y
        
        # 마지막 라인 추가
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _group_lines_into_paragraphs(self, lines):
        """라인들을 문단으로 그룹화"""
        if not lines:
            return []
        
        paragraphs = []
        current_paragraph = []
        
        for line in lines:
            # 라인 텍스트 추출
            line_text = "".join(char['text'] for char in line).strip()
            
            if not line_text:
                # 빈 라인 - 문단 구분자
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = []
                continue
            
            # 제목 패턴 감지 (대문자, 번호, 특수문자 등)
            is_title = self._is_title_line(line_text)
            
            if is_title and current_paragraph:
                # 제목이면 이전 문단 종료하고 새 문단 시작
                paragraphs.append(current_paragraph)
                current_paragraph = [line_text]
            else:
                # 일반 텍스트면 현재 문단에 추가
                current_paragraph.append(line_text)
        
        # 마지막 문단 추가
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        return paragraphs
    
    def _is_title_line(self, text):
        """제목 라인인지 판단"""
        if not text or len(text) < 2:
            return False
        
        # 제목 패턴들
        title_patterns = [
            r'^\d+\.\s+',  # 1. 제목
            r'^[가-힣\s]+:$',  # 제목:
            r'^[A-Z\s]+$',  # 대문자 제목
            r'^[가-힣\s]{2,20}$',  # 짧은 한글 제목
            r'^※',  # 주석
            r'^\*',  # 별표
        ]
        
        import re
        return any(re.match(pattern, text) for pattern in title_patterns)
    
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """모든 PDF 파일 처리"""
        pdf_files = list(self.input_dir.glob("*.pdf"))
        logger.info(f"처리할 PDF 파일 수: {len(pdf_files)}")
        
        results = []
        
        for pdf_file in tqdm(pdf_files, desc="PDF OCR 처리 중"):
            logger.info(f"처리 중: {pdf_file.name}")
            result = self.extract_text_from_pdf(pdf_file)
            results.append(result)
            
            # 개별 파일 결과 저장
            output_file = self.output_dir / f"{pdf_file.stem}_ocr.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"저장 완료: {output_file}")
        
        return results
    
    def save_combined_results(self, results: List[Dict[str, Any]]):
        """모든 결과를 하나의 파일로 저장"""
        combined_file = self.output_dir / "finance_support_ocr_combined.json"
        
        combined_data = {
            "total_files": len(results),
            "successful_files": len([r for r in results if "error" not in r]),
            "failed_files": len([r for r in results if "error" in r]),
            "files": results
        }
        
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"통합 결과 저장 완료: {combined_file}")
        
        # 통계 출력
        print(f"\n=== OCR 처리 완료 ===")
        print(f"총 파일 수: {combined_data['total_files']}")
        print(f"성공한 파일: {combined_data['successful_files']}")
        print(f"실패한 파일: {combined_data['failed_files']}")
        print(f"결과 저장 위치: {self.output_dir}")

def main():
    """메인 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent
    input_dir = base_dir / "data" / "vector_db" / "finance_support_pdf"
    output_dir = base_dir / "data" / "vector_db" /  "raw_json"
    
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    
    # OCR 처리기 생성 및 실행
    processor = PDFOCRProcessor(str(input_dir), str(output_dir))
    results = processor.process_all_pdfs()
    processor.save_combined_results(results)

if __name__ == "__main__":
    main()
