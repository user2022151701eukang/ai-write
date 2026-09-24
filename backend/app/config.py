"""配置管理 - 从环境变量 / .env 文件加载"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类 - 从环境变量加载"""

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./paper_writer.db"

    # LLM 配置（支持多种模型）
    LLM_PROVIDER: str = "qwen"  # qwen, openai, deepseek, zhipu

    # 千问（阿里云百炼 DashScope）配置
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4"

    # DeepSeek 配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 智谱 AI 配置
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-4"

    # LLM 通用参数
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 300

    # 向量数据库配置
    EMBEDDING_PROVIDER: str = "qwen"  # qwen, openai
    VECTOR_DB_PATH: str = "./data/chroma"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_BATCH_SIZE: int = 10

    # JWT 配置
    SECRET_KEY: str = "your_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 应用配置
    APP_NAME: str = "AI 论文写作系统"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# 创建全局配置实例
settings = Settings()