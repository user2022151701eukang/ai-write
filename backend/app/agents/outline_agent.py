"""大纲生成 Agent"""

from typing import Any, AsyncIterator, Dict

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.base_agent import BaseAgent
from app.utils.helpers import extract_json

PAPER_TYPE_LABELS = {
    "research": "研究论文",
    "review": "综述论文",
    "application": "应用研究",
    "thesis": "学位论文",
}


class OutlineAgent(BaseAgent):
    """
    大纲生成 Agent

    功能：
    1. 根据选题生成结构化论文大纲
    2. 支持不同论文类型（综述、研究、应用等）
    3. 输出 JSON 格式大纲便于编辑
    """

    def __init__(self):
        super().__init__(
            name="大纲专家",
            description="生成结构化、逻辑清晰的论文大纲",
        )

    def get_system_prompt(self) -> str:
        return """你是一位资深的学术论文结构设计专家，擅长根据选题生成逻辑清晰、层次分明的论文大纲。

你的职责：
1. 根据论文选题和研究内容设计合理的大纲结构
2. 确保大纲符合学术论文规范
3. 为每个章节设计合理的内容要点

输出要求：
- 输出 JSON 格式的大纲结构
- 包含章节标题、内容要点、预估字数
- 层次清晰，逻辑连贯

JSON 格式示例：
{
  "title": "论文标题",
  "sections": [
    {
      "title": "摘要",
      "points": ["研究背景", "研究方法", "主要结论"],
      "word_count": 300
    },
    {
      "title": "引言",
      "points": ["研究背景", "研究意义"],
      "word_count": 800
    }
  ]
}"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行大纲生成"""
        title = input_data.get("title", "")
        paper_type = input_data.get("paper_type", "research")
        word_limit = input_data.get("word_limit", 10000)
        topic = input_data.get("topic", "")

        prompt = ChatPromptTemplate.from_messages([
            # 系统提示词中含 JSON 示例（花括号），故以 SystemMessage 传入，避免被当作模板变量解析
            SystemMessage(content=self.get_system_prompt()),
            ("user", """请为以下论文生成详细大纲：

论文标题：{title}
选题方向：{topic}
论文类型：{paper_type}
字数限制：{word_limit} 字

请输出 JSON 格式的完整大纲结构。只输出 JSON，不要其他内容。"""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        result = await chain.ainvoke({
            "title": title,
            "topic": topic or title,
            "paper_type": PAPER_TYPE_LABELS.get(paper_type, paper_type),
            "word_limit": word_limit,
        })

        outline_dict = extract_json(result) or {"title": title, "sections": []}

        return {
            "outline": result,
            "outline_dict": outline_dict,
        }

    async def stream_execute(self, input_data: Dict[str, Any]) -> AsyncIterator[str]:
        """流式输出大纲生成过程"""
        title = input_data.get("title", "")
        paper_type = input_data.get("paper_type", "research")
        word_limit = input_data.get("word_limit", 10000)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.get_system_prompt()),
            ("user", (
                f"请为论文「{title}」生成详细大纲。\n"
                f"论文类型：{PAPER_TYPE_LABELS.get(paper_type, paper_type)}\n"
                f"字数限制：{word_limit} 字\n"
                "请输出 JSON 格式，只输出 JSON。"
            )),
        ])

        chain = prompt | self.llm | StrOutputParser()

        async for chunk in chain.astream({}):
            yield chunk