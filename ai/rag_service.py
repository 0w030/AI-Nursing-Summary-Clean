import os
import chromadb
import requests
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    def __init__(self, db_path="./local_data/chroma_db"):
        # 確保儲存向量資料庫的目錄存在
        os.makedirs(db_path, exist_ok=True)
        # 初始化本地向量庫
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="nursing_summaries")
        
        # 取得 Ollama URL
        self.ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        self.embed_url = f"{self.ollama_url}/api/embeddings"
        
    def _get_embedding(self, text: str) -> list:
        """呼叫 Ollama 將文字轉為向量"""
        try:
            response = requests.post(self.embed_url, json={
                "model": "nomic-embed-text",
                "prompt": text
            }, timeout=60)
            if response.status_code == 200:
                return response.json().get("embedding", [])
            else:
                print(f"⚠️ Ollama Embedding 錯誤: {response.text}")
                return []
        except Exception as e:
            print(f"⚠️ 無法取得 Embedding: {e}")
            return []

    def add_memory(self, encounter_id: str, raw_data: str, final_summary: str):
        """將護理師確認後的「完美摘要」存入記憶"""
        vector = self._get_embedding(raw_data)
        if not vector:
            print("⚠️ 無法產生向量，記憶未儲存。")
            return

        self.collection.add(
            embeddings=[vector],
            documents=[final_summary], # 這是 AI 要參考的標準答案
            metadatas=[{"raw_data": raw_data, "encounter_id": encounter_id}],
            ids=[f"summary_{encounter_id}"]
        )
        print(f"✅ 已將就醫序號 {encounter_id} 的摘要存入 RAG 記憶庫。")

    def retrieve_similar_cases(self, current_raw_data: str, top_k: int = 2) -> str:
        """找出最相似的過去案例"""
        if self.collection.count() == 0:
            return "" # 還沒有記憶
            
        vector = self._get_embedding(current_raw_data)
        if not vector:
            return ""

        results = self.collection.query(
            query_embeddings=[vector],
            n_results=min(top_k, self.collection.count())
        )
        
        if not results['documents'] or not results['documents'][0]:
            return ""
            
        # 組裝成範例字串
        examples_text = "【以下是過去類似病歷的優良摘要範例，請參考其專業用語與重點提取方式】\n"
        for i, doc in enumerate(results['documents'][0]):
            examples_text += f"範例 {i+1}:\n{doc}\n---\n"
            
        return examples_text
