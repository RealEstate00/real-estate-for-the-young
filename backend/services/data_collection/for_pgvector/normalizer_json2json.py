"""
JSON 파일의 content 필드에서 제어 문자들을 정리하는 후처리 스크립트

목적:
- \u0001 같은 제어 문자들을 공백으로 변환
- 연속된 공백들을 하나로 정리
- 텍스트 가독성 향상
"""

import json
import re
import os

def clean_content(text):
    """텍스트에서 제어 문자 및 불필요한 공백 정리"""
    if not text:
        return text
    
    # 1️⃣ 제어 문자들을 공백으로 변환
    control_chars = [
        '\u0001',  # SOH (Start of Heading)
        '\u0002',  # STX (Start of Text)  
        '\u0003',  # ETX (End of Text)
        '\u0004',  # EOT (End of Transmission)
        '\u0005',  # ENQ (Enquiry)
        '\u0006',  # ACK (Acknowledge)
        '\u0007',  # BEL (Bell)
        '\u0008',  # BS (Backspace)
        '\u000B',  # VT (Vertical Tab)
        '\u000C',  # FF (Form Feed)
        '\u000E',  # SO (Shift Out)
        '\u000F',  # SI (Shift In)
        '\u0010',  # DLE (Data Link Escape)
        '\u0011',  # DC1 (Device Control 1)
        '\u0012',  # DC2 (Device Control 2)
        '\u0013',  # DC3 (Device Control 3)
        '\u0014',  # DC4 (Device Control 4)
        '\u0015',  # NAK (Negative Acknowledge)
        '\u0016',  # SYN (Synchronous Idle)
        '\u0017',  # ETB (End of Transmission Block)
        '\u0018',  # CAN (Cancel)
        '\u0019',  # EM (End of Medium)
        '\u001A',  # SUB (Substitute)
        '\u001B',  # ESC (Escape)
        '\u001C',  # FS (File Separator)
        '\u001D',  # GS (Group Separator)
        '\u001E',  # RS (Record Separator)
        '\u001F',  # US (Unit Separator)
        '\u007F',  # DEL (Delete)
    ]
    
    for char in control_chars:
        text = text.replace(char, ' ')
    
    # 2️⃣ 줄바꿈 문자를 공백으로 변환
    text = text.replace('\n', ' ')
    
    # 3️⃣ 연속된 공백들을 하나로 정리
    text = re.sub(r'\s+', ' ', text)
    
    # 4️⃣ 앞뒤 공백 제거
    text = text.strip()
    
    return text

def normalize_json_file(input_path, output_path=None):
    """JSON 파일의 content 필드들을 정규화"""
    
    # 출력 경로가 없으면 _cleaned 접미사 추가
    if output_path is None:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_cleaned{ext}"
    
    print(f"📖 읽는 중: {input_path}")
    
    # JSON 파일 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📝 총 {len(data)}개 레코드 발견")
    
    # 각 레코드의 content 정리
    cleaned_count = 0
    for record in data:
        if 'content' in record:
            original = record['content']
            cleaned = clean_content(original)
            
            if original != cleaned:
                record['content'] = cleaned
                cleaned_count += 1
    
    print(f"🧹 {cleaned_count}개 레코드 정리 완료")
    
    # 정리된 JSON 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 저장 완료: {output_path}")
    
    return output_path

def main():
    """메인 실행 함수"""
    input_file = "backend/data/raw/finance_support/pre_normalize/allPDF.json"
    output_file = "backend/data/normalized/finance_support/allPDF_cleaned.json"
    
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return
    
    normalize_json_file(input_file, output_file)
    
    print("\n🎉 JSON 정규화 완료!")

if __name__ == "__main__":
    main()
