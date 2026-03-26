"""
模板導入功能測試腳本
"""

import sys
import json
sys.path.insert(0, 'c:/AI-Nursing-Summary-Clean/AI-Nursing-Summary-Clean')

from db.template_service import import_templates_from_json, get_all_templates

# 測試 JSON 導入
test_json = {
    "測試模板1": "這是測試模板1的內容",
    "測試模板2": "這是測試模板2的內容"
}

json_str = json.dumps(test_json, ensure_ascii=False)
print("=" * 50)
print("測試：導入 JSON 格式的模板")
print("=" * 50)
print(f"JSON 內容：{json_str}")

success_count, failed_list, error = import_templates_from_json(json_str)

if error:
    print(f"❌ 錯誤：{error}")
else:
    print(f"✅ 成功導入 {success_count} 個模板")
    if failed_list:
        print(f"⚠️ 失敗的模板：{failed_list}")

print("\n" + "=" * 50)
print("驗證：查看所有模板")
print("=" * 50)
all_templates = get_all_templates()
for name, content in all_templates.items():
    preview = content[:50] + "..." if len(content) > 50 else content
    print(f"- {name}: {preview}")
