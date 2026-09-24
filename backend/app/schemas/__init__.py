"""Pydantic 模式包"""

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.schemas.paper import (
    PaperCreate,
    PaperUpdate,
    PaperResponse,
    PaperDetail,
    PaperGenerateRequest,
)
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterGenerateRequest,
    ChapterPolishRequest,
)
from app.schemas.version import (
    VersionCreateRequest,
    VersionSummary,
    VersionDetail,
    VersionDiffResponse,
    RollbackResponse,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "PaperCreate",
    "PaperUpdate",
    "PaperResponse",
    "PaperDetail",
    "PaperGenerateRequest",
    "ChapterCreate",
    "ChapterUpdate",
    "ChapterResponse",
    "ChapterGenerateRequest",
    "ChapterPolishRequest",
    "VersionCreateRequest",
    "VersionSummary",
    "VersionDetail",
    "VersionDiffResponse",
    "RollbackResponse",
]