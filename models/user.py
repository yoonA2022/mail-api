"""用户模型"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserLogin(BaseModel):
    """用户登录请求模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, description="用户密码")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    status: int
    is_verified: int
    last_login_at: Optional[datetime] = None
    created_at: datetime


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[UserResponse] = None


class UserRegister(BaseModel):
    """用户注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, description="用户密码")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")


class RegisterResponse(BaseModel):
    """注册响应模型"""
    success: bool
    message: str
    user: Optional[UserResponse] = None
    refresh_token: Optional[str] = None
    user: Optional[UserResponse] = None
