import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.config_manager import config_manager

def test_schema_import():
    print("\n" + "=" * 60)
    print("Schema Import Test")
    print("=" * 60)
    
    discovered_schema = {
        'discovered_at': '2026-04-20T10:00:00',
        'database': 'TEST_DB',
        'db_type': 'oracle',
        'tables': {
            'PATIENT': {
                'table_info': {
                    'name': 'PATIENT',
                    'row_count': 1000,
                    'comment': 'Patient Info'
                },
                'columns': [
                    {'name': 'PT_ID', 'data_type': 'VARCHAR2(16)', 'nullable': False, 'max_length': 16, 'comment': 'ID'},
                    {'name': 'PT_NAME', 'data_type': 'VARCHAR2(100)', 'nullable': True, 'max_length': 100, 'comment': 'Name'},
                ]
            }
        }
    }
    
    try:
        imported_tables, imported_fields = config_manager.import_discovered_schema(
            discovered_schema,
            connection_name='test_oracle',
            username='admin',
            auto_type_map=True
        )
        
        print(f"Success: {imported_tables} tables, {imported_fields} fields imported")
        all_mappings = config_manager.get_all_mappings()
        print(f"Total mappings: {sum(len(m) for m in all_mappings.values())}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    test_schema_import()
