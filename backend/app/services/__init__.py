"""业务服务包"""

from app.services.paper_service import PaperService, paper_service
from app.services.chapter_service import ChapterService, chapter_service
from app.services.reference_service import ReferenceService, reference_service

__all__ = [
    "PaperService",
    "paper_service",
    "ChapterService",
    "chapter_service",
    "ReferenceService",
    "reference_service",
]