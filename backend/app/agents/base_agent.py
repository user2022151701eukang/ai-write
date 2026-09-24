"""Agent 基类"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.utils.llm import get_llm


class BaseAgent(ABC):
    """Agent 基类 - 所有 Agent 继承此类"""

    def __init__(
        self,
        name: str,
        description: str,
        llm: Optional[BaseLanguageModel] = None,
    ):
        self.name = name
        self.description = description
        self.llm = llm or get_llm()
        self.memory: list = []  # 对话记忆

    def add_message(self, role: str, content: str) -> None:
        """添加消息到记忆"""
        message_map = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage,
        }
        message_class = message_map.get(role, HumanMessage)
        self.memory.append(message_class(content=content))

    def clear_memory(self) -> None:
        """清空记忆"""
        self.memory = []

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent 任务 - 子类必须实现"""
        raise NotImplementedError

    async def stream_execute(self, input_data: Dict[str, Any]) -> AsyncIterator[str]:
        """流式执行 - 子类可选实现"""
        result = await self.execute(input_data)
        yield result.get("output", "")

    def get_system_prompt(self) -> str:
        """获取系统提示词 - 子类可重写"""
        return f"你是{self.name}，{self.description}。请根据用户需求完成任务。"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"