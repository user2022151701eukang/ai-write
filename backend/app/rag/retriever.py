"""检索器 - 面向文献的相似度检索"""

from typing import Dict, List, Optional

from app.rag.vector_store import vector_store


class ReferenceRetriever:
    """文献检索器"""

    def __init__(self, top_k: int = 5):
        self.vector_store = vector_store
        self.top_k = top_k

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """检索相关文献"""
        k = top_k or self.top_k

        results = self.vector_store.search(query, top_k=k)

        # 应用过滤条件
        if filters:
            filtered_results = []
            for doc in results:
                metadata = doc.get("metadata", {})
                match = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_results.append(doc)
            results = filtered_results

        return results

    async def search_by_topic(
        self,
        topic: str,
        year_range: Optional[tuple] = None,
    ) -> List[Dict]:
        """按主题检索文献"""
        results = await self.search(topic)

        if year_range:
            start_year, end_year = year_range
            filtered = []
            for doc in results:
                year = doc.get("metadata", {}).get("year")
                if year and start_year <= year <= end_year:
                    filtered.append(doc)
            results = filtered

        return results

    async def batch_search(self, queries: List[str]) -> Dict[str, List[Dict]]:
        """批量检索"""
        results = {}
        for query in queries:
            results[query] = await self.search(query)
        return results


# 创建默认检索器实例
retriever = ReferenceRetriever()