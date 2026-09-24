"""用户相关 Pydantic 模式"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模式"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., max_length=100, description="邮箱")


class UserCreate(UserBase):
    """创建用户模式"""

    password: str = Field(..., min_length=6, max_length=64, description="密码")


class UserLogin(BaseModel):
    """用户登录模式"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    """用户响应模式"""

    id: int
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """令牌响应模式"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse