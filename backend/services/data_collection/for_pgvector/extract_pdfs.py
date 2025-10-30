#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주거지원정책 PDF 텍스트 추출 스크립트

입력: backend/data/raw/finance_support/*.pdf
출력: backend/data/raw/finance_support/모든_주거지원_정책.txt
"""

import os
import sys
from pathlib import Path
from pypdf import PdfReader

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 경로 설정
script_dir = Path(__file__).parent  # for_pgvector
backend_dir = script_dir.parent.parent.parent  # backend
pdf_dir = backend_dir / "data" / "raw" / "finance_support"
output_file = pdf_dir / "모든_주거지원_정책.txt"

# PDF 파일 목록
pdf_files = [
    "1인가구 주택관리서비스 _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "긴급복지주거지원제도 _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "대출안내 _ 버팀목전세자금 _ 주택전세자금대출 _ 개인상품 _ 주택도시기금.pdf",
    "상품개요 _ 전세보증금반환보증 _ 개인보증 _ 주택도시보증공사.pdf",
    "서울형 주택바우처 (일반바우처) _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "서울형 주택바우처(반지하 거주가구 이주 지원) _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "서울형 주택바우처(아동바우처) _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "전세보증금 반환보증 보증료 지원 _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "주거급여 수급자 지원(임차급여) _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "주거취약계층 주거상향지원 _ 주거복지 사업 _ 주거 정책 _ 서울주거포털.pdf",
    "청년안심주택.pdf",
    "청년전세임대주택.pdf",
    "행복기숙사.pdf",
    "행복주택.pdf",
    "희망히우징.pdf"
]

# 결과를 저장할 리스트
all_text = []

print("PDF 텍스트 추출 시작...")

# 각 PDF 파일 처리
for pdf_filename in pdf_files:
    pdf_path = pdf_dir / pdf_filename

    if not pdf_path.exists():
        print(f"⚠️  파일을 찾을 수 없습니다: {pdf_filename}")
        continue

    try:
        print(f"처리 중: {pdf_filename}")

        # PDF 파일명을 구분자로 추가
        all_text.append("=" * 80)
        all_text.append(f"파일명: {pdf_filename}")
        all_text.append("=" * 80)
        all_text.append("")

        # PDF 읽기
        reader = PdfReader(str(pdf_path))

        # 모든 페이지의 텍스트 추출
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                all_text.append(f"[페이지 {page_num}]")
                all_text.append(text)
                all_text.append("")

        all_text.append("\n")
        print(f"✓ 완료: {pdf_filename} ({len(reader.pages)} 페이지)")

    except Exception as e:
        print(f"❌ 오류 발생 ({pdf_filename}): {str(e)}")
        all_text.append(f"[오류: 텍스트 추출 실패 - {str(e)}]")
        all_text.append("\n")

# 결과를 하나의 텍스트 파일로 저장
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(all_text))

print(f"\n✓ 모든 PDF 텍스트가 추출되었습니다: {output_file}")
print(f"총 {len(pdf_files)}개 파일 처리 완료")


if __name__ == '__main__':
    pass  # 스크립트 실행 시 자동으로 위 코드가 실행됨
