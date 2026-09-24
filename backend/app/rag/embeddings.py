"""向量化 - 统一封装 Embedding 模型调用"""

from typing import List

from app.config import settings
from app.utils.llm import get_embedding_model, is_embedding_configured


class EmbeddingService:
    """向量化服务：将文本批量转换为向量"""

    _model = None

    @classmethod
    def get_model(cls):
        """获取（懒加载）Embedding 模型实例"""
        if cls._model is None:
            cls._model = get_embedding_model()
        return cls._model

    @classmethod
    def embed_documents(cls, texts: List[str]) -> List[List[float]]:
        """批量向量化文档，自动按批次提交"""
        if not texts:
            return []

        if not is_embedding_configured():
            raise RuntimeError(
                f"未配置 {settings.EMBEDDING_PROVIDER} 的 API Key，无法进行向量化，"
                "请在 backend/.env 中填写对应的 API Key"
            )

        model = cls.get_model()
        batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)

        vectors: List[List[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            vectors.extend(model.embed_documents(batch))
        return vectors

    @classmethod
    def embed_query(cls, text: str) -> List[float]:
        """向量化单条查询文本"""
        if not is_embedding_configured():
            raise RuntimeError(
                f"未配置 {settings.EMBEDDING_PROVIDER} 的 API Key，无法进行向量检索，"
                "请在 backend/.env 中填写对应的 API Key"
            )
        return cls.get_model().embed_query(text)