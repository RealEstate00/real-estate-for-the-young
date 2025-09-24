import json
from pathlib import Path

# JSON 파일 읽기
json_file = Path('backend/data/normalized/test_infra_10_samples/public_facilities.json')
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1층엔약국 개수 확인
pharmacy_entries = [item for item in data if item.get('name') == '1층엔약국']
print(f'1층엔약국 개수: {len(pharmacy_entries)}')

# facility_id 확인
if pharmacy_entries:
    print('1층엔약국의 facility_id들:')
    for i, entry in enumerate(pharmacy_entries[:10]):
        print(f'  {i+1}: {entry.get("facility_id")}')

# 전체 약국 개수 확인
all_pharmacy = [item for item in data if item.get('facility_id', '').startswith('pha')]
print(f'\n전체 약국 개수: {len(all_pharmacy)}')

# facility_id 패턴 확인
pha_ids = [item.get('facility_id') for item in all_pharmacy]
if pha_ids:
    print(f'약국 facility_id 범위: {min(pha_ids)} ~ {max(pha_ids)}')

# 각 데이터셋별 개수 확인
dataset_counts = {}
for item in data:
    facility_id = item.get('facility_id', '')
    if facility_id:
        prefix = facility_id[:3]  # 첫 3글자 (예: pha, chi, etc.)
        dataset_counts[prefix] = dataset_counts.get(prefix, 0) + 1

print(f'\n데이터셋별 개수:')
for prefix, count in sorted(dataset_counts.items()):
    print(f'  {prefix}: {count}개')

