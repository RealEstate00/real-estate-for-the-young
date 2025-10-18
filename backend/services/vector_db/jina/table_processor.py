"""
표 처리 및 JSON 구조화 모듈
다양한 유형의 표를 통합적으로 처리하여 JSON으로 변환
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TableCell:
    """표 셀 데이터"""
    content: str
    row_span: int = 1
    col_span: int = 1
    is_header: bool = False
    is_group_header: bool = False


@dataclass
class TableRow:
    """표 행 데이터"""
    cells: List[TableCell]
    is_header: bool = False
    is_group_header: bool = False
    group_name: Optional[str] = None


@dataclass
class TableStructure:
    """표 구조 데이터"""
    title: str
    columns: List[str]
    rows: List[TableRow]
    table_type: str  # 'simple', 'grouped', 'hierarchical', 'complex'
    metadata: Dict[str, Any]


class TableProcessor:
    """표 처리 및 JSON 변환 클래스"""
    
    def __init__(self):
        self.table_types = {
            'simple': self._process_simple_table,
            'grouped': self._process_grouped_table,
            'hierarchical': self._process_hierarchical_table,
            'complex': self._process_complex_table
        }
    
    def process_table(self, table_text: str) -> Dict[str, Any]:
        """표 텍스트를 JSON으로 변환"""
        try:
            # 1. 표 구조 분석
            structure = self._analyze_table_structure(table_text)
            
            # 2. 표 유형별 처리
            processor = self.table_types.get(structure.table_type, self._process_simple_table)
            result = processor(structure)
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "table_text": table_text[:200] + "..." if len(table_text) > 200 else table_text
            }
    
    def _analyze_table_structure(self, table_text: str) -> TableStructure:
        """표 구조 분석"""
        lines = table_text.strip().split('\n')
        
        # === 표 N === 헤더 제거
        content_lines = []
        for line in lines:
            if not (line.startswith('=== 표') and line.endswith('===')):
                content_lines.append(line)
        
        if not content_lines:
            raise ValueError("표 내용이 없습니다")
        
        # 마크다운 테이블 파싱
        rows = self._parse_markdown_table(content_lines)
        
        # 표 유형 결정
        table_type = self._determine_table_type(rows)
        
        # 제목 추출
        title = self._extract_table_title(table_text)
        
        # 컬럼 추출
        columns = self._extract_columns(rows[0]) if rows else []
        
        return TableStructure(
            title=title,
            columns=columns,
            rows=rows,
            table_type=table_type,
            metadata={}
        )
    
    def _parse_markdown_table(self, lines: List[str]) -> List[TableRow]:
        """마크다운 테이블을 파싱하여 행 리스트로 변환"""
        rows = []
        current_row = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # 마크다운 테이블 라인인지 확인
            if '|' in line:
                if not in_table:
                    in_table = True
                
                # 구분선 라인 무시
                if re.match(r'^\|[\s\-]+\|$', line):
                    continue
                
                # 행이 시작되면 현재 행을 완료하고 새 행 시작
                if line.startswith('|') and current_row:
                    complete_row = ' '.join(current_row)
                    if complete_row.strip():
                        rows.append(self._create_table_row(complete_row))
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
                rows.append(self._create_table_row(complete_row))
        
        return rows
    
    def _create_table_row(self, row_text: str) -> TableRow:
        """행 텍스트를 TableRow 객체로 변환"""
        cells = []
        
        # |로 분할하여 셀 추출
        cell_texts = row_text.split('|')
        for i, cell_text in enumerate(cell_texts):
            if i == 0 or i == len(cell_texts) - 1:  # 첫 번째와 마지막은 빈 문자열
                continue
            
            content = cell_text.strip()
            if content:
                cells.append(TableCell(
                    content=content,
                    is_header=(i == 1),  # 첫 번째 셀은 헤더로 간주
                    is_group_header=self._is_group_header(content)
                ))
        
        return TableRow(cells=cells)
    
    def _is_group_header(self, content: str) -> bool:
        """그룹 헤더인지 판단 (개선된 패턴)"""
        group_patterns = [
            # 소득 기준 관련
            r'가구당\s*월평균소득의\s*\d+%',
            r'소득\s*기준',
            r'소득\s*요건',
            
            # 자격/대상 관련
            r'입주대상',
            r'선정기준',
            r'신청자격',
            r'대상\s*\(.*\)',
            r'구분',
            
            # 비용/지원 관련
            r'임대료',
            r'거주기간',
            r'지원\s*내용',
            r'혜택',
            
            # 절차/방법 관련
            r'신청\s*절차',
            r'신청\s*방법',
            r'제출\s*서류',
            r'문의\s*처',
            
            # 일반적인 섹션 헤더
            r'^[가-힣\s]+:$',  # 콜론으로 끝나는 제목
            r'^\d+\.\s*[가-힣\s]+$',  # 번호로 시작하는 제목
        ]
        
        for pattern in group_patterns:
            if re.search(pattern, content):
                return True
        
        # 추가 조건: 빈 셀이거나 매우 짧은 텍스트인 경우
        if not content.strip() or len(content.strip()) <= 2:
            return True
        
        return False
    
    def _determine_table_type(self, rows: List[TableRow]) -> str:
        """표 유형 결정"""
        if not rows:
            return 'simple'
        
        # 그룹 헤더가 있는지 확인
        has_group_headers = any(
            any(cell.is_group_header for cell in row.cells) 
            for row in rows
        )
        
        # 계층적 구조 확인 (첫 번째 열이 그룹, 두 번째 열이 하위 그룹)
        has_hierarchical = len(rows) > 1 and len(rows[0].cells) >= 2
        
        # 복합 구조 확인 (여러 섹션으로 나뉜 표)
        has_complex_structure = any(
            len([cell for cell in row.cells if cell.is_group_header]) > 1
            for row in rows
        )
        
        if has_complex_structure:
            return 'complex'
        elif has_hierarchical:
            return 'hierarchical'
        elif has_group_headers:
            return 'grouped'
        else:
            return 'simple'
    
    def _extract_table_title(self, table_text: str) -> str:
        """표 제목 추출"""
        lines = table_text.strip().split('\n')
        for line in lines:
            if line.startswith('=== 표') and line.endswith('==='):
                return line.replace('===', '').strip()
        return "표"
    
    def _extract_columns(self, header_row: TableRow) -> List[str]:
        """컬럼 추출"""
        return [cell.content for cell in header_row.cells]
    
    def _process_simple_table(self, structure: TableStructure) -> Dict[str, Any]:
        """단순 표 처리"""
        result = {
            "table_type": "simple",
            "title": structure.title,
            "columns": structure.columns,
            "data": []
        }
        
        for row in structure.rows[1:]:  # 헤더 제외
            row_data = {}
            for i, cell in enumerate(row.cells):
                if i < len(structure.columns):
                    row_data[structure.columns[i]] = cell.content
            result["data"].append(row_data)
        
        return result
    
    def _process_grouped_table(self, structure: TableStructure) -> Dict[str, Any]:
        """그룹 헤더가 있는 표 처리"""
        result = {
            "table_type": "grouped",
            "title": structure.title,
            "columns": structure.columns,
            "groups": []
        }
        
        current_group = None
        current_group_data = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            if any(cell.is_group_header for cell in row.cells):
                # 새 그룹 시작
                if current_group:
                    result["groups"].append({
                        "group_name": current_group,
                        "data": current_group_data
                    })
                
                current_group = next(
                    cell.content for cell in row.cells if cell.is_group_header
                )
                current_group_data = []
            else:
                # 데이터 행
                row_data = {}
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        row_data[structure.columns[i]] = cell.content
                current_group_data.append(row_data)
        
        # 마지막 그룹 추가
        if current_group:
            result["groups"].append({
                "group_name": current_group,
                "data": current_group_data
            })
        
        return result
    
    def _process_hierarchical_table(self, structure: TableStructure) -> Dict[str, Any]:
        """계층적 표 처리"""
        result = {
            "table_type": "hierarchical",
            "title": structure.title,
            "columns": structure.columns,
            "categories": []
        }
        
        current_category = None
        current_subcategories = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            if len(row.cells) >= 2:
                first_cell = row.cells[0].content
                second_cell = row.cells[1].content
                
                # 첫 번째 셀이 그룹 헤더인지 확인
                if self._is_group_header(first_cell) and second_cell:
                    # 새 카테고리 시작
                    if current_category:
                        result["categories"].append({
                            "category_name": current_category,
                            "subcategories": current_subcategories
                        })
                    
                    current_category = first_cell
                    current_subcategories = []
                else:
                    # 서브카테고리 데이터
                    subcategory_data = {}
                    for i, cell in enumerate(row.cells):
                        if i < len(structure.columns):
                            subcategory_data[structure.columns[i]] = cell.content
                    current_subcategories.append(subcategory_data)
        
        # 마지막 카테고리 추가
        if current_category:
            result["categories"].append({
                "category_name": current_category,
                "subcategories": current_subcategories
            })
        
        return result
    
    def _process_complex_table(self, structure: TableStructure) -> Dict[str, Any]:
        """복합 구조 표 처리"""
        result = {
            "table_type": "complex",
            "title": structure.title,
            "sections": []
        }
        
        current_section = None
        current_section_data = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            group_headers = [cell for cell in row.cells if cell.is_group_header]
            
            if group_headers:
                # 새 섹션 시작
                if current_section:
                    result["sections"].append({
                        "section_name": current_section,
                        "data": current_section_data
                    })
                
                current_section = group_headers[0].content
                current_section_data = []
            else:
                # 데이터 행
                row_data = {}
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        row_data[structure.columns[i]] = cell.content
                current_section_data.append(row_data)
        
        # 마지막 섹션 추가
        if current_section:
            result["sections"].append({
                "section_name": current_section,
                "data": current_section_data
            })
        
        return result
    
    def convert_to_csv(self, table_text: str) -> str:
        """표를 CSV 형식으로 변환"""
        try:
            structure = self._analyze_table_structure(table_text)
            
            # CSV 헤더 생성
            csv_lines = []
            csv_lines.append(','.join(f'"{col}"' for col in structure.columns))
            
            # 표 유형별 CSV 변환
            if structure.table_type == 'hierarchical':
                csv_lines.extend(self._convert_hierarchical_to_csv(structure))
            elif structure.table_type == 'grouped':
                csv_lines.extend(self._convert_grouped_to_csv(structure))
            elif structure.table_type == 'complex':
                csv_lines.extend(self._convert_complex_to_csv(structure))
            else:
                csv_lines.extend(self._convert_simple_to_csv(structure))
            
            return '\n'.join(csv_lines)
            
        except Exception as e:
            return f"CSV 변환 오류: {str(e)}"
    
    def _convert_simple_to_csv(self, structure: TableStructure) -> List[str]:
        """단순 표를 CSV로 변환"""
        csv_lines = []
        for row in structure.rows[1:]:  # 헤더 제외
            row_data = []
            for i, cell in enumerate(row.cells):
                if i < len(structure.columns):
                    # CSV에서 쉼표와 따옴표 이스케이프
                    content = str(cell.content).replace('"', '""')
                    row_data.append(f'"{content}"')
            csv_lines.append(','.join(row_data))
        return csv_lines
    
    def _convert_grouped_to_csv(self, structure: TableStructure) -> List[str]:
        """그룹 헤더가 있는 표를 CSV로 변환"""
        csv_lines = []
        current_group = None
        
        for row in structure.rows[1:]:  # 헤더 제외
            if any(cell.is_group_header for cell in row.cells):
                # 그룹 헤더 행
                current_group = next(
                    cell.content for cell in row.cells if cell.is_group_header
                )
                # 그룹 헤더를 첫 번째 컬럼에 추가
                row_data = [f'"{current_group}"'] + ['""'] * (len(structure.columns) - 1)
                csv_lines.append(','.join(row_data))
            else:
                # 데이터 행
                row_data = []
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        content = str(cell.content).replace('"', '""')
                        row_data.append(f'"{content}"')
                csv_lines.append(','.join(row_data))
        
        return csv_lines
    
    def _convert_hierarchical_to_csv(self, structure: TableStructure) -> List[str]:
        """계층적 표를 CSV로 변환 (개선된 빈 셀 처리)"""
        csv_lines = []
        current_category = None
        
        for row in structure.rows[1:]:  # 헤더 제외
            if len(row.cells) >= 2:
                first_cell = row.cells[0].content
                second_cell = row.cells[1].content
                
                # 첫 번째 셀이 그룹 헤더인지 확인 (빈 셀도 고려)
                if self._is_group_header(first_cell) and (not second_cell.strip() or self._is_group_header(second_cell)):
                    current_category = first_cell
                    # 카테고리 헤더 행 추가
                    row_data = [f'"{current_category}"'] + ['""'] * (len(structure.columns) - 1)
                    csv_lines.append(','.join(row_data))
                else:
                    # 서브카테고리 데이터 행
                    row_data = []
                    for i, cell in enumerate(row.cells):
                        if i < len(structure.columns):
                            content = str(cell.content).replace('"', '""')
                            # 빈 셀은 빈 문자열로 처리
                            if not content.strip():
                                content = ""
                            row_data.append(f'"{content}"')
                    csv_lines.append(','.join(row_data))
        
        return csv_lines
    
    def _convert_complex_to_csv(self, structure: TableStructure) -> List[str]:
        """복합 구조 표를 CSV로 변환"""
        csv_lines = []
        current_section = None
        
        for row in structure.rows[1:]:  # 헤더 제외
            group_headers = [cell for cell in row.cells if cell.is_group_header]
            
            if group_headers:
                # 섹션 헤더 행
                current_section = group_headers[0].content
                row_data = [f'"{current_section}"'] + ['""'] * (len(structure.columns) - 1)
                csv_lines.append(','.join(row_data))
            else:
                # 데이터 행
                row_data = []
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        content = str(cell.content).replace('"', '""')
                        row_data.append(f'"{content}"')
                csv_lines.append(','.join(row_data))
        
        return csv_lines
    
    def chunk_table_by_width(self, table_text: str, max_width: int = 100) -> List[Dict[str, Any]]:
        """표를 width 최대값 기준으로 덩어리로 나누기"""
        try:
            structure = self._analyze_table_structure(table_text)
            chunks = []
            
            # 표 유형별 청킹
            if structure.table_type == 'hierarchical':
                chunks = self._chunk_hierarchical_table(structure, max_width)
            elif structure.table_type == 'grouped':
                chunks = self._chunk_grouped_table(structure, max_width)
            elif structure.table_type == 'complex':
                chunks = self._chunk_complex_table(structure, max_width)
            else:
                chunks = self._chunk_simple_table(structure, max_width)
            
            return chunks
            
        except Exception as e:
            return [{"error": str(e), "table_text": table_text[:200] + "..."}]
    
    def _chunk_simple_table(self, structure: TableStructure, max_width: int) -> List[Dict[str, Any]]:
        """단순 표를 청킹"""
        chunks = []
        current_chunk = {
            "chunk_type": "table_section",
            "title": structure.title,
            "columns": structure.columns,
            "rows": []
        }
        
        for row in structure.rows[1:]:  # 헤더 제외
            # 행의 총 길이 계산
            row_length = sum(len(str(cell.content)) for cell in row.cells)
            
            if row_length > max_width and current_chunk["rows"]:
                # 현재 청크 저장하고 새 청크 시작
                chunks.append(current_chunk)
                current_chunk = {
                    "chunk_type": "table_section",
                    "title": structure.title,
                    "columns": structure.columns,
                    "rows": []
                }
            
            # 행 데이터 추가
            row_data = {}
            for i, cell in enumerate(row.cells):
                if i < len(structure.columns):
                    row_data[structure.columns[i]] = cell.content
            current_chunk["rows"].append(row_data)
        
        # 마지막 청크 추가
        if current_chunk["rows"]:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_grouped_table(self, structure: TableStructure, max_width: int) -> List[Dict[str, Any]]:
        """그룹 헤더가 있는 표를 청킹"""
        chunks = []
        current_group = None
        current_group_data = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            if any(cell.is_group_header for cell in row.cells):
                # 새 그룹 시작
                if current_group and current_group_data:
                    chunks.append({
                        "chunk_type": "table_group",
                        "title": f"{structure.title} - {current_group}",
                        "group_name": current_group,
                        "columns": structure.columns,
                        "rows": current_group_data
                    })
                
                current_group = next(
                    cell.content for cell in row.cells if cell.is_group_header
                )
                current_group_data = []
            else:
                # 데이터 행
                row_data = {}
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        row_data[structure.columns[i]] = cell.content
                current_group_data.append(row_data)
        
        # 마지막 그룹 추가
        if current_group and current_group_data:
            chunks.append({
                "chunk_type": "table_group",
                "title": f"{structure.title} - {current_group}",
                "group_name": current_group,
                "columns": structure.columns,
                "rows": current_group_data
            })
        
        return chunks
    
    def _chunk_hierarchical_table(self, structure: TableStructure, max_width: int) -> List[Dict[str, Any]]:
        """계층적 표를 청킹"""
        chunks = []
        current_category = None
        current_subcategories = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            if len(row.cells) >= 2:
                first_cell = row.cells[0].content
                second_cell = row.cells[1].content
                
                # 첫 번째 셀이 그룹 헤더인지 확인
                if self._is_group_header(first_cell) and second_cell:
                    # 새 카테고리 시작
                    if current_category and current_subcategories:
                        chunks.append({
                            "chunk_type": "table_category",
                            "title": f"{structure.title} - {current_category}",
                            "category_name": current_category,
                            "columns": structure.columns,
                            "subcategories": current_subcategories
                        })
                    
                    current_category = first_cell
                    current_subcategories = []
                else:
                    # 서브카테고리 데이터
                    subcategory_data = {}
                    for i, cell in enumerate(row.cells):
                        if i < len(structure.columns):
                            subcategory_data[structure.columns[i]] = cell.content
                    current_subcategories.append(subcategory_data)
        
        # 마지막 카테고리 추가
        if current_category and current_subcategories:
            chunks.append({
                "chunk_type": "table_category",
                "title": f"{structure.title} - {current_category}",
                "category_name": current_category,
                "columns": structure.columns,
                "subcategories": current_subcategories
            })
        
        return chunks
    
    def _chunk_complex_table(self, structure: TableStructure, max_width: int) -> List[Dict[str, Any]]:
        """복합 구조 표를 청킹"""
        chunks = []
        current_section = None
        current_section_data = []
        
        for row in structure.rows[1:]:  # 헤더 제외
            group_headers = [cell for cell in row.cells if cell.is_group_header]
            
            if group_headers:
                # 새 섹션 시작
                if current_section and current_section_data:
                    chunks.append({
                        "chunk_type": "table_section",
                        "title": f"{structure.title} - {current_section}",
                        "section_name": current_section,
                        "columns": structure.columns,
                        "rows": current_section_data
                    })
                
                current_section = group_headers[0].content
                current_section_data = []
            else:
                # 데이터 행
                row_data = {}
                for i, cell in enumerate(row.cells):
                    if i < len(structure.columns):
                        row_data[structure.columns[i]] = cell.content
                current_section_data.append(row_data)
        
        # 마지막 섹션 추가
        if current_section and current_section_data:
            chunks.append({
                "chunk_type": "table_section",
                "title": f"{structure.title} - {current_section}",
                "section_name": current_section,
                "columns": structure.columns,
                "rows": current_section_data
            })
        
        return chunks


def test_table_processing():
    """표 처리 테스트 - 4가지 표 유형"""
    processor = TableProcessor()
    
    # 4가지 표 유형 테스트 데이터
    test_tables = [
        # 1. 단순 표 (자산요건 표)
        """=== 표 1 ===
| 구분 | 자산요건 | 자동차 |
| --- | --- | --- |
| 신혼부부 | 총 자산가액 합산기준 3.37억원 | 3,803만원 이하 |
| 청년 | 총 자산가액 합산기준 2.54억원 | 3,803만원 이하 |
| 대학생 | 총 자산가액 합산기준 1.04억원 | 미소유 |""",
        
        # 2. 그룹 헤더 표 (소득 기준 표) - 이미지의 표와 유사한 구조
        """=== 표 1 ===
| 구분 | 1인 | 2인 | 3인 | 4인 | 5인 |
| --- | --- | --- | --- | --- | --- |
| 가구당 월평균소득의 100% | | | | | |
| 대학생 계층(본인 및 부모) | 4,317,797원 | 6,024,703원 | 7,626,973원 | 8,578,088원 | 9,031,048원 |
| 청년 계층 | 4,317,797원 | 6,024,703원 | 7,626,973원 | 8,578,088원 | 9,031,048원 |
| 신혼부부 계층(예비신혼부부 포함) | 4,317,797원 | 6,024,703원 | 7,626,973원 | 8,578,088원 | 9,031,048원 |
| 고령자 | 4,317,797원 | 6,024,703원 | 7,626,973원 | 8,578,088원 | 9,031,048원 |
| 가구당 월평균소득의 120% | | | | | |
| 맞벌이 신혼부부 | 4,317,797원 | 6,572,404원 | 9,152,368원 | 10,293,706원 | 10,837,258원 |""",
        
        # 3. 계층적 표 (신청자격 표)
        """=== 표 1 ===
| 대상 | 정의 | 소득 | 총자산가액 | 자동차가액 | 주택청약종합저축 |
| --- | --- | --- | --- | --- | --- |
| 대학생(미혼) | 대학생 | 대학 재학 중이거나 다음 학기 입학 또는 복학 예정 | 본인, 부모 합계 소득이 평균소득의 100% 이하(1인 120%, 2인 110%) | 10,400 (본인) | 비소유 | - |
| | 취업준비생 | 대학 재학 중이거나 다음 학기 입학 또는 복학 예정 | | | | |
| 청년(미혼) | 청년 | 19세 이상 39세 이하 | 평균소득의 100% 이하(1인 120%, 2인 110%) | 25,400 | 3,803 | 가입사실증명 |
| | 사회 초년생 | 소득 있는 업무 종사 또는 퇴직 후 1년 이내로서 소득 있는 업무 종사기간이 총 5년 이내 | | | | |
| | 예술인 | 예술인복지법 제2조제2호에 따른 예술인 | | | | |
| 신혼부부, 한부모가족 | 신혼부부 | 혼인 중으로 (합산)혼인기간이 7년 이내 | 평균소득의 100% 이하 (2인 110%) 배우자가 소득이 있을 경우 120% 이하 (맞벌이 2인 130%) | 33,700 | 3,803 | 가입사실증명 |
| | 예비신혼부부 | 혼인을 계획 중 (입주 전까지 혼인사실 증명) | | | | |
| | 한부모가족 | 6세 이하 자녀(태아 포함) 부양 | | | | |
| 고령자 | 고령자 | 65세 이상 | 평균소득의 100% 이하(1인 120%, 2인 110%) | 33,700 | 3,803 | - |
| 주거급여수급자 | 주거급여수급자 | 주거급여법 제2조제2호·제3호에 따른 수급권자 또는 수급자 | - | - | - | - |""",
        
        # 4. 복합 구조 표 (입주대상/선정기준 표)
        """=== 표 1 ===
| 입주대상 | 19세 이상 39세 이하 미혼 청년 - 직장 재직여부 무관 - 대학생 및 취업준비생도 청년 지원가능 |
| --- | --- |
| 선정기준 | 구분 | 1순위 | 2순위 | 3순위 |
| | 소득 | 범위 | 생계·의료·주거급여 수급자 가구, 보호대상 한부모 가족, 차상위계층 가구 | 본인과 부모 | 본인 |
| | | 기준 | (1순위 신청자는 순위자격을 입증하는 경우 별도의 소득·자산 심사를 진행하지 않습니다.) | 100% 이하 | 100% 이하 |
| | 총자산 | | | 3억 3,700만원 이하 | 2억 5,400만원 이하 |
| | 자동차가액 | | | 3,803만원 이하 | 3,803만원 이하 |
| 임대료 | 시중 시세의 30~50% 수준의 임대보증금 및 임대료 (1순위: 시중 시세 30%, 2~3순위: 시중 시세 50%) |
| 거주기간 | 2년, 재계약 4회 가능 (입주자격 충족 시 최장 10년 거주) |"""
    ]
    
    table_types = [
        "1. 단순 표 (자산요건)",
        "2. 그룹 헤더 표 (소득 기준)", 
        "3. 계층적 표 (신청자격)",
        "4. 복합 구조 표 (입주대상/선정기준)"
    ]
    
    for i, (table_text, table_type) in enumerate(zip(test_tables, table_types)):
        print(f"=== {table_type} ===")
        
        # 1. 기본 JSON 변환
        result = processor.process_table(table_text)
        print("JSON 변환 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()
        
        # 2. CSV 변환
        csv_result = processor.convert_to_csv(table_text)
        print("CSV 변환 결과:")
        print(csv_result)
        print()
        
        # 3. Width 기준 청킹
        chunks = processor.chunk_table_by_width(table_text, max_width=50)
        print("Width 기준 청킹 결과:")
        print(json.dumps(chunks, ensure_ascii=False, indent=2))
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    test_table_processing()
