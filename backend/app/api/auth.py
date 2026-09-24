"""认证接口 - 注册 / 登录 / 当前用户，以及鉴权依赖"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ----------------------------------------------------------------------
# 密码与令牌工具
# ----------------------------------------------------------------------
def hash_password(password: str) -> str:
    """对密码进行哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_minutes: Optional[int] = None) -> tuple:
    """创建 JWT 访问令牌，返回 (token, 有效期秒数)"""
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "exp": expire}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, minutes * 60


def decode_token(token: str) -> Optional[int]:
    """解析 JWT，返回用户 ID"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        return int(subject) if subject else None
    except (JWTError, ValueError):
        return None


async def _load_user_by_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    if not token:
        return None

    user_id = decode_token(token)
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token", description="SSE 场景下的令牌"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选鉴权：未登录时返回 None（用于允许匿名使用的接口）"""
    user = await _load_user_by_token(token or token_query, db)
    if user is not None and not user.is_active:
        return None
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_optional_user),
) -> User:
    """强制鉴权：未登录时返回 401"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_llm_config() -> None:
    """AI 接口依赖：校验大模型 API Key 是否已配置"""
    from app.utils.llm import is_llm_configured

    if not is_llm_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="尚未配置大模型 API Key，请在 backend/.env 中填写 QWEN_API_KEY 后重启后端服务",
        )


# ----------------------------------------------------------------------
# 接口
# ----------------------------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == login_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    token, expires_in = create_access_token(user.id)
    return Token(access_token=token, token_type="bearer", expires_in=expires_in, user=user)


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user