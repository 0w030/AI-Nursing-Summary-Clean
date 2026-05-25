from ai.rag_service import RAGService

def test_rag():
    print("初始化 RAG 服務...")
    rag = RAGService()
    
    # 檢查目前資料庫筆數
    count = rag.collection.count()
    print(f"目前資料庫中共有 {count} 筆記憶。")
    
    if count == 0:
        print("資料庫為空，寫入一筆測試資料...")
        rag.add_memory(
            encounter_id="TEST_001",
            raw_data="病患主訴頭痛，血壓 140/90，體溫 38度。有咳嗽症狀。",
            final_summary="病患因頭痛及發燒(38度)就診，伴隨咳嗽，血壓偏高(140/90)。建議持續觀察體溫變化並給予退燒藥物。",
            model_source="groq"
        )
        print(f"寫入後資料庫共有 {rag.collection.count()} 筆記憶。")
    
    print("\n測試檢索功能...")
    query_data = "病患表示頭很痛，而且發燒到38.5度，有輕微咳嗽。血壓 135/85。"
    print(f"查詢內容: {query_data}")
    result = rag.retrieve_similar_cases(query_data)
    
    if result:
        print("\n✅ 成功找到相似案例：")
        print(result)
    else:
        print("\n❌ 未找到相似案例 (可能是 Ollama 未啟動或 embedding 失敗)")

if __name__ == "__main__":
    test_rag()
