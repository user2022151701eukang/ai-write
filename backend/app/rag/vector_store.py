"""向量存储 - 基于 ChromaDB 的文献向量库"""

import logging
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

COLLECTION_NAME = "academic_references"


class VectorStore:
    """向量数据库管理类（单例）"""

    _instance: Optional["VectorStore"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=settings.VECTOR_DB_PATH,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # 创建或获取集合（向量由 EmbeddingService 显式提供）
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "学术论文参考文献向量库"},
        )

        self._initialized = True

    @classmethod
    def initialize(cls) -> None:
        """初始化向量数据库"""
        try:
            cls()
        except Exception as exc:  # 向量库不可用时不应阻塞应用启动
            logger.warning("向量数据库初始化失败：%s", exc)

    def add_documents(self, documents: List[Dict]) -> None:
        """
        添加文档到向量库

        Args:
            documents: [{"id": "1", "text": "...", "metadata": {...}}]
        """
        if not documents:
            return

        ids = [str(doc["id"]) for doc in documents]
        texts = [doc["text"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]

        embeddings = EmbeddingService.embed_documents(texts)

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """相似度检索"""
        if self.get_document_count() == 0:
            return []

        query_embedding = EmbeddingService.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.get_document_count()),
            include=["documents", "metadatas", "distances"],
        )

        documents: List[Dict] = []
        ids = results.get("ids") or [[]]
        for i in range(len(ids[0])):
            documents.append({
                "id": ids[0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "score": 1 - results["distances"][0][i] if results.get("distances") else 0.0,
            })

        return documents

    def delete_document(self, doc_id: str) -> None:
        """删除文档"""
        self.collection.delete(ids=[str(doc_id)])

    def get_document_count(self) -> int:
        """获取文档数量"""
        return self.collection.count()

    def clear(self) -> None:
        """清空向量库"""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "学术论文参考文献向量库"},
        )


# 创建全局实例
vector_store = VectorStore()