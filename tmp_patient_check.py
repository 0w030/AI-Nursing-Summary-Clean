from db.patient_service import get_all_patients_overview

items = get_all_patients_overview()
print('loaded', len(items))
print('exact', sum(1 for p in items if str(p.get('病歷號','')).strip() == '0006633498'))
print('contains', sum(1 for p in items if '0006633498' in str(p.get('病歷號',''))))
for p in items:
    if str(p.get('病歷號','')).strip() == '0006633498':
        print('MATCH', p)
        break
