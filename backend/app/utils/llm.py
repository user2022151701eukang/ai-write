"""LLM 工具 - 统一创建对话模型 / 向量化模型实例"""

from typing import Optional, Tuple

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings

# 未配置 Key 时使用的占位 Key，保证应用可以正常启动，
# 真正调用模型时会由服务端返回鉴权错误，前端可据此提示用户配置 API Key。
PLACEHOLDER_API_KEY = "sk-not-configured"

# 各模型提供商配置：provider -> (API Key, Base URL, Model)
PROVIDER_SETTINGS = {
    "qwen": (lambda: settings.QWEN_API_KEY, lambda: settings.QWEN_BASE_URL, lambda: settings.QWEN_MODEL),
    "openai": (lambda: settings.OPENAI_API_KEY, lambda: settings.OPENAI_BASE_URL, lambda: settings.OPENAI_MODEL),
    "deepseek": (lambda: settings.DEEPSEEK_API_KEY, lambda: settings.DEEPSEEK_BASE_URL, lambda: settings.DEEPSEEK_MODEL),
    "zhipu": (lambda: settings.ZHIPU_API_KEY, lambda: settings.ZHIPU_BASE_URL, lambda: settings.ZHIPU_MODEL),
}


def get_provider_config(provider: str) -> Tuple[str, Optional[str], str]:
    """获取指定提供商的配置，返回 (api_key, base_url, model)"""
    if provider not in PROVIDER_SETTINGS:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")

    key_getter, url_getter, model_getter = PROVIDER_SETTINGS[provider]
    api_key = key_getter()
    if not api_key:
        api_key = PLACEHOLDER_API_KEY
    return api_key, url_getter(), model_getter()


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    获取 LLM 实例（千问 / OpenAI / DeepSeek / 智谱均走 OpenAI 兼容协议）

    Args:
        provider: 模型提供商（qwen/openai/deepseek/zhipu）
        model: 模型名称
        temperature: 温度参数
        streaming: 是否启用流式输出
    """
    provider = provider or settings.LLM_PROVIDER
    api_key, base_url, default_model = get_provider_config(provider)

    return ChatOpenAI(
        model=model or default_model,
        api_key=api_key,
        base_url=base_url,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        streaming=streaming,
        timeout=settings.LLM_TIMEOUT,
        max_retries=2,
    )


def get_embedding_model() -> OpenAIEmbeddings:
    """获取 Embedding 模型实例"""
    provider = settings.EMBEDDING_PROVIDER

    if provider == "qwen":
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.QWEN_API_KEY or PLACEHOLDER_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            # 千问 Embedding 不支持 tiktoken 分词，直接按原文提交
            check_embedding_ctx_length=False,
        )

    if provider == "openai":
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY or PLACEHOLDER_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            check_embedding_ctx_length=False,
        )

    raise ValueError(f"不支持的 Embedding 提供商: {provider}")


def is_llm_configured() -> bool:
    """检查当前 LLM 提供商是否已配置 API Key"""
    provider = settings.LLM_PROVIDER
    if provider not in PROVIDER_SETTINGS:
        return False
    return bool(PROVIDER_SETTINGS[provider][0]())


def is_embedding_configured() -> bool:
    """检查向量化模型是否已配置 API Key"""
    if settings.EMBEDDING_PROVIDER == "qwen":
        return bool(settings.QWEN_API_KEY)
    if settings.EMBEDDING_PROVIDER == "openai":
        return bool(settings.OPENAI_API_KEY)
    return False