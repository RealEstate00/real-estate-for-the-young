import os, re, glob
import pdfplumber  # 항상 필요 (fallback용)

# UnstructuredPDFLoader 시도 (pi_heif 의존성 문제로 일단 비활성화)
UNSTRUCTURED_AVAILABLE = False
# try:
#     from langchain_community.document_loaders import UnstructuredPDFLoader
#     UNSTRUCTURED_AVAILABLE = True
# except ImportError:
#     UNSTRUCTURED_AVAILABLE = False

# 📁 PDF 폴더
pdf_dir = "backend/data/raw/finance_support"
pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))

# 📦 저장 폴더
save_dir = os.path.join(pdf_dir, "pre_normalize")
os.makedirs(save_dir, exist_ok=True)

# ==========================
# 🔹 텍스트 추출 함수
# ==========================
def extract_text_from_pdf_with_pdfplumber(pdf_path):
    """pdfplumber를 사용한 PDF 텍스트 추출 (표 포함)"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # 일반 텍스트 추출 (표 내용도 함께 추출됨)
            page_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            lines = [ln for ln in page_text.split("\n")]
            # "- 1 -" 같은 페이지 번호 제거
            lines = [ln.rstrip() for ln in lines if not re.match(r"^\s*-\s*\d+\s*-\s*$", ln)]
            text += "\n".join(lines) + "\n"
    return text.strip()


def extract_text_from_pdf(pdf_path):
    """
    PDF에서 텍스트 추출
    UnstructuredPDFLoader 사용 가능하면 표 구조 인식, 아니면 pdfplumber 사용
    """
    if UNSTRUCTURED_AVAILABLE:
        try:
            loader = UnstructuredPDFLoader(
                pdf_path,
                mode="elements",  # 요소별로 분리하여 표 구조 인식
                strategy="hi_res"  # 고해상도 분석으로 표 정확도 향상
            )
            documents = loader.load()

            # 모든 요소를 텍스트로 결합
            text = ""
            for doc in documents:
                content = doc.page_content
                metadata = doc.metadata

                # 표 데이터 포맷팅 개선
                if metadata.get("category") == "Table":
                    # 표 형식 데이터 처리
                    lines = content.split("\n")
                    formatted_lines = []
                    for line in lines:
                        # 페이지 번호 제거
                        if not re.match(r"^\s*-\s*\d+\s*-\s*$", line):
                            formatted_lines.append(line.rstrip())
                    text += "\n".join(formatted_lines) + "\n\n"
                else:
                    # 일반 텍스트 처리
                    lines = [ln.rstrip() for ln in content.split("\n")
                            if not re.match(r"^\s*-\s*\d+\s*-\s*$", ln)]
                    text += "\n".join(lines) + "\n"

            return text.strip()

        except Exception as e:
            print(f"   ⚠️ UnstructuredPDFLoader 오류: {e}")
            print(f"   → pdfplumber fallback 사용...")
            return extract_text_from_pdf_with_pdfplumber(pdf_path)
    else:
        # UnstructuredPDFLoader 없으면 pdfplumber 사용
        return extract_text_from_pdf_with_pdfplumber(pdf_path)

# ==========================
# 🔹 텍스트 클리닝
# ==========================
def clean_text(raw_text):
    patterns = [
        r"javascript:[^\s]+", r"http[^\s]+",
        r"개인정보처리방침", r"저작권 정책", r"©Seoul",
        r"서울특별시", r"대표전화",  r"로그인", 
        r"홈페이지 바로가기"
    ]

    text = raw_text
    for p in patterns:
        text = re.sub(p, "", text)
    return text.strip()

# ==========================
# 🔹 PDF 전체 처리
# ==========================
all_text = ""

print(f"총 {len(pdf_files)}개 PDF를 처리 중...\n")

for pdf_path in pdf_files:
    file_name = os.path.basename(pdf_path).replace(".pdf", "")
    try:
        # 텍스트 추출
        text = extract_text_from_pdf(pdf_path)
        cleaned = clean_text(text)

        # 문서 구분선 추가
        all_text += f"\n\n==============================\n[문서] {file_name}\n==============================\n\n"
        all_text += cleaned + "\n"

        print(f"[OK] {file_name} 처리 완료")

    except Exception as e:
        print(f"[ERROR] {file_name} 처리 중 오류: {e}")

# ==========================
# 🔹 통합 TXT 저장
# ==========================
txt_path = os.path.join(save_dir, "allPDF.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write(all_text.strip())

print(f"\n[완료] 변환 완료! 결과 파일:")
print(f"TXT : {txt_path}")
print(f"총 {len(pdf_files)}개 문서 처리 완료")
