#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSONL 파일을 JSON 파일로 변환하는 스크립트
"""

import json
from pathlib import Path
from datetime import datetime

def convert_jsonl_to_json(jsonl_file_path: Path, output_json_path: Path):
    """JSONL 파일을 JSON 파일로 변환"""
    
    if not jsonl_file_path.exists():
        print(f"파일이 존재하지 않습니다: {jsonl_file_path}")
        return
    
    data_list = []
    
    # JSONL 파일 읽기
    with open(jsonl_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    data = json.loads(line.strip())
                    data_list.append(data)
                except json.JSONDecodeError as e:
                    print(f"라인 {line_num} JSON 파싱 오류: {e}")
                    continue
    
    # JSON 파일로 저장
    json_data = {
        "failed_test_results": data_list,
        "metadata": {
            "converted_at": datetime.now().isoformat(),
            "total_count": len(data_list),
            "source_file": str(jsonl_file_path),
            "description": "실패한 주소 정규화 테스트 결과"
        }
    }
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"변환 완료!")
    print(f"   - 입력: {jsonl_file_path} ({len(data_list)}개 데이터)")
    print(f"   - 출력: {output_json_path}")

def main():
    """메인 실행 함수"""
    # 현재 스크립트 위치에서 상대 경로로 계산
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[5]  # backend/services/data_collection/infra/normalized/들고올 자료 -> backend
    
    # 파일 경로 설정
    test_fail_dir = project_root / "backend" / "data" / "normalized" / "infra" / "test_fail"
    
    # 실패한_test.jsonl → 실패한_test.json
    failed_jsonl_path = test_fail_dir / "실패한_test.jsonl"
    failed_json_path = test_fail_dir / "실패한_test.json"
    
    print("JSONL -> JSON 변환 시작...")
    print(f"작업 디렉토리: {test_fail_dir}")
    
    # 실패한 테스트 결과 변환
    if failed_jsonl_path.exists():
        print(f"\n실패한_test.jsonl 변환 중...")
        convert_jsonl_to_json(failed_jsonl_path, failed_json_path)
    else:
        print(f"실패한_test.jsonl 파일이 존재하지 않습니다: {failed_jsonl_path}")
    
    # 성공한 테스트 결과도 변환 (선택사항)
    success_jsonl_path = test_fail_dir / "성공한_test.jsonl"
    success_json_path = test_fail_dir / "성공한_test.json"
    
    if success_jsonl_path.exists():
        print(f"\n성공한_test.jsonl 변환 중...")
        convert_jsonl_to_json(success_jsonl_path, success_json_path)
    else:
        print(f"성공한_test.jsonl 파일이 존재하지 않습니다: {success_jsonl_path}")
    
    print(f"\n변환 작업 완료!")

if __name__ == "__main__":
    main()
