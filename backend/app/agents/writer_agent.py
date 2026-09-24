"""内容撰写 Agent"""

from typing import Any, AsyncIterator, Dict, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.base_agent import BaseAgent
from app.utils.helpers import strip_ai_meta


class WriterAgent(BaseAgent):
    """
    内容撰写 Agent

    功能：
    1. 根据大纲撰写具体章节内容
    2. 支持学术写作风格控制
    3. 支持引用文献的融入
    """

    def __init__(self):
        super().__init__(
            name="写作专家",
            description="撰写高质量学术论文内容",
        )

    def get_system_prompt(self) -> str:
        return """你是一位资深的学术论文写作专家，擅长撰写高质量、逻辑严谨的学术论文内容。

写作要求：
1. 语言规范，表达准确，符合学术写作规范
2. 论点清晰，论据充分，逻辑严密
3. 合理引用参考文献，使用标准引用格式
4. 数据准确，图表规范
5. 专业术语使用恰当

写作风格：
- 客观中立，避免主观判断
- 数据驱动，有理有据
- 层次清晰，结构合理
- 语言精练，避免冗余

输出要求（必须严格遵守）：
1. 只输出该章节的正文内容（Markdown 格式），不要重复章节标题；
2. 禁止输出任何非正文内容：不要写「说明」「注」「提示」「格式说明」「写作思路」等附加段落；
3. 严禁输出「如需扩展为…」「我可以为您…」「希望以上内容…」「如需进一步调整请告知」等后续服务建议或客套话；
4. 不要用 ``` 代码块包裹正文；
5. 正文写完后立即结束，不要追加任何总结、致谢或补充说明。"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行章节内容撰写"""
        section_title = input_data.get("section_title", "")
        outline_points: List[str] = input_data.get("outline_points", []) or []
        references: List[str] = input_data.get("references", []) or []
        style = input_data.get("style", "formal")
        word_count = input_data.get("word_count", 1000)
        context = input_data.get("context", "")

        points_text = "\n".join([f"- {p}" for p in outline_points]) or "（无具体要求，请自行组织）"
        refs_text = "\n".join([f"[{i + 1}] {ref}" for i, ref in enumerate(references)]) if references else "暂无参考文献"

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("user", """请撰写以下章节内容：

## 章节标题：{section_title}

### 内容要点：
{points}

### 相关文献：
{references}

### 已撰写内容摘要（用于保持上下文连贯）：
{context}

### 要求：
- 写作风格：{style}
- 预估字数：{word_count} 字左右
- 请完整撰写该章节内容，确保学术性和专业性

请开始撰写："""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        result = await chain.ainvoke({
            "section_title": section_title,
            "points": points_text,
            "references": refs_text,
            "context": context or "（本章节为第一部分）",
            "style": style,
            "word_count": word_count,
        })

        return {"content": strip_ai_meta(result)}

    async def stream_execute(self, input_data: Dict[str, Any]) -> AsyncIterator[str]:
        """流式输出内容撰写"""
        section_title = input_data.get("section_title", "")
        outline_points: List[str] = input_data.get("outline_points", []) or []
        references: List[str] = input_data.get("references", []) or []
        word_count = input_data.get("word_count", 1000)
        context = input_data.get("context", "")

        points_text = "\n".join([f"- {p}" for p in outline_points]) or "（无具体要求，请自行组织）"
        refs_text = "\n".join([f"[{i + 1}] {ref}" for i, ref in enumerate(references)]) if references else "暂无参考文献"

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("user", f"""章节标题：{section_title}
内容要点：
{points_text}

相关文献：
{refs_text}

已撰写内容摘要：
{context or "（本章节为第一部分）"}

预估字数：{word_count} 字左右。

请开始撰写（直接输出正文）："""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        async for chunk in chain.astream({}):
            yield chunk