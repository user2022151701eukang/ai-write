"""文献检索 Agent"""

from typing import Any, Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.base_agent import BaseAgent
from app.rag.retriever import ReferenceRetriever
from app.utils.helpers import format_reference

FORMAT_LABELS = {
    "gbt": "GB/T 7714",
    "apa": "APA",
    "mla": "MLA",
}


class ReferenceAgent(BaseAgent):
    """
    文献检索 Agent

    功能：
    1. 基于向量相似度检索相关文献
    2. 生成标准格式的引用文本
    3. 分析文献与研究主题的关联性
    """

    def __init__(self):
        super().__init__(
            name="文献专家",
            description="检索和推荐相关学术文献",
        )
        self.retriever = ReferenceRetriever()

    def get_system_prompt(self) -> str:
        return """你是一位资深的学术文献专家，擅长检索、分析和整理学术文献。

你的职责：
1. 根据研究主题推荐相关文献
2. 生成标准格式的引用文本（GB/T 7714、APA、MLA等）
3. 分析文献的核心观点和参考价值

引用格式示例（GB/T 7714）：
[序号] 作者. 题名[J]. 刊名, 出版年, 卷(期): 起止页码.

请确保：
- 引用信息完整准确
- 格式符合学术规范
- 文献与研究主题相关"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行文献检索"""
        query = input_data.get("query", "")
        top_k = input_data.get("top_k", 5)
        format_style = input_data.get("format", "gbt")

        # 使用 RAG 检索相关文献
        try:
            retrieved_docs = await self.retriever.search(query, top_k=top_k)
        except Exception as exc:
            return {
                "references": [],
                "formatted": "",
                "error": f"文献检索失败：{exc}",
            }

        if not retrieved_docs:
            return {
                "references": [],
                "formatted": "文献库中暂未检索到相关文献，可先在「文献管理」中导入文献。",
                "error": None,
            }

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("user", """请将以下文献信息整理为标准引用格式：

检索主题：{query}
引用格式：{format_style}

文献信息：
{documents}

请输出编号的引用列表。"""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        docs_text = "\n\n".join([
            f"文献 {i + 1}:\n标题: {doc.get('metadata', {}).get('title', doc.get('text', 'N/A'))}\n"
            f"作者: {doc.get('metadata', {}).get('authors', 'N/A')}\n"
            f"期刊: {doc.get('metadata', {}).get('journal', 'N/A')}\n"
            f"年份: {doc.get('metadata', {}).get('year', 'N/A')}\n"
            f"标准引用: {format_reference(doc.get('metadata', {}), format_style)}"
            for i, doc in enumerate(retrieved_docs)
        ])

        try:
            formatted_refs = await chain.ainvoke({
                "query": query,
                "format_style": FORMAT_LABELS.get(format_style, format_style),
                "documents": docs_text,
            })
        except Exception:
            # 模型不可用时退化为本地格式化结果
            formatted_refs = "\n".join([
                f"[{i + 1}] {format_reference(doc.get('metadata', {}), format_style)}"
                for i, doc in enumerate(retrieved_docs)
            ])

        return {
            "references": retrieved_docs,
            "formatted": formatted_refs,
        }