"""IMAP账户模型"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ImapAccountBase(BaseModel):
    """IMAP账户基础模型"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="邮箱密码或授权码")
    nickname: Optional[str] = Field(None, max_length=100, description="账户昵称")
    platform: str = Field(..., max_length=50, description="邮箱平台")
    imap_host: str = Field(..., max_length=255, description="IMAP服务器地址")
    imap_port: int = Field(993, description="IMAP端口号")
    use_ssl: bool = Field(True, description="是否使用SSL")
    status: bool = Field(True, description="账户状态")
    auto_sync: bool = Field(True, description="是否自动同步")
    folder: str = Field("INBOX", max_length=100, description="默认同步的邮件文件夹")
    max_fetch: int = Field(50, description="每次最多获取邮件数")
    remark: Optional[str] = Field(None, description="备注说明")


class ImapAccountCreate(ImapAccountBase):
    """创建IMAP账户请求模型"""
    user_id: Optional[int] = Field(None, description="关联的用户ID")


class ImapAccountUpdate(BaseModel):
    """更新IMAP账户请求模型"""
    password: Optional[str] = Field(None, description="邮箱密码或授权码")
    nickname: Optional[str] = Field(None, max_length=100, description="账户昵称")
    imap_host: Optional[str] = Field(None, max_length=255, description="IMAP服务器地址")
    imap_port: Optional[int] = Field(None, description="IMAP端口号")
    use_ssl: Optional[bool] = Field(None, description="是否使用SSL")
    status: Optional[bool] = Field(None, description="账户状态")
    auto_sync: Optional[bool] = Field(None, description="是否自动同步")
    folder: Optional[str] = Field(None, max_length=100, description="默认同步的邮件文件夹")
    max_fetch: Optional[int] = Field(None, description="每次最多获取邮件数")
    remark: Optional[str] = Field(None, description="备注说明")


class ImapAccountResponse(BaseModel):
    """IMAP账户响应模型"""
    id: int
    email: str
    nickname: Optional[str] = None
    user_id: Optional[int] = None
    platform: str
    imap_host: str
    imap_port: int
    use_ssl: bool
    status: bool
    auto_sync: bool
    last_sync_time: Optional[datetime] = None
    folder: str
    max_fetch: int
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImapAccountListResponse(BaseModel):
    """IMAP账户列表响应模型"""
    success: bool
    message: str
    data: list[ImapAccountResponse]
    total: int


class ImapAccountDetailResponse(BaseModel):
    """IMAP账户详情响应模型"""
    success: bool
    message: str
    data: Optional[ImapAccountResponse] = None
