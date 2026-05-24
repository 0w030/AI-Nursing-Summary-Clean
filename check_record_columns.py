import json
with open('config/management/schema_mappings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for mapping in data.get('mappings', {}).get('oracle_from_env', {}).get('RECORD', []):
    print(f"- {mapping['db_column_name']} ({mapping['original_type']})")
