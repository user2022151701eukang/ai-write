"""润色优化 Agent"""

from typing import Any, AsyncIterator, Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.base_agent import BaseAgent
from app.utils.helpers import count_words, strip_ai_meta


class PolishAgent(BaseAgent):
    """
    论文润色 Agent

    功能：
    1. 语言表达优化
    2. 逻辑结构优化
    3. 学术规范检查
    """

    def __init__(self):
        super().__init__(
            name="润色专家",
            description="优化论文语言表达和逻辑结构",
        )

    def get_system_prompt(self) -> str:
        return """你是一位资深的学术论文润色专家，擅长优化论文的语言表达和逻辑结构。

润色要点：
1. **语言优化**
   - 消除冗余表达
   - 提升表达准确性
   - 统一术语使用
   - 优化句式结构

2. **逻辑优化**
   - 强化论证链条
   - 完善段落衔接
   - 提升论述连贯性
   - 优化结构层次

3. **规范检查**
   - 学术用语规范
   - 格式排版规范
   - 引用格式规范

请保持原文学术观点，仅做表达和结构优化。

输出要求（必须严格遵守）：
1. 直接输出润色后的完整正文（Markdown 格式），保持原有标题层级与结构；
2. 禁止输出任何非正文内容：不要写修改说明、润色说明、变更清单、格式说明；
3. 严禁输出「如需扩展为…」「我可以为您…」「希望以上内容…」等后续服务建议或客套话；
4. 不要用 ``` 代码块包裹正文；
5. 正文结束后立即停止，不要追加任何总结或补充。"""

    @staticmethod
    def _focus_instruction(focus: str) -> str:
        focus_instructions = {
            "language": "请重点优化语言表达，提升表达的准确性和简洁性。",
            "logic": "请重点优化逻辑结构，强化论证链条和段落衔接。",
            "format": "请重点检查格式规范，确保符合学术写作规范。",
            "all": "请全面优化语言表达、逻辑结构和格式规范。",
        }
        return focus_instructions.get(focus, focus_instructions["all"])

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行论文润色"""
        content = input_data.get("content", "")
        focus = input_data.get("focus", "all")

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("user", """请润色以下论文内容：

{focus_instruction}

## 原文内容：

{content}

## 输出要求：

1. 输出润色后的完整内容
2. 保持 Markdown 结构与标题层级不变

请开始润色："""),
        ])

        chain = prompt | self.llm | StrOutputParser()

        result = await chain.ainvoke({
            "content": content,
            "focus_instruction": self._focus_instruction(focus),
        })

        result = strip_ai_meta(result)

        return {
            "polished": result,
            "original_length": count_words(content),
            "polished_length": count_words(result),
        }

    async def stream_execute(self, input_data: Dict[str, Any]) -> AsyncIterator[str]:
        """流式输出润色结果"""
        content = input_data.get("content", "")
        focus = input_data.get("focus", "all")

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("user", f"{self._focus_instruction(focus)}\n\n请润色以下论文内容：\n\n{content}"),
        ])

        chain = prompt | self.llm | StrOutputParser()

        async for chunk in chain.astream({}):
            yield chunk