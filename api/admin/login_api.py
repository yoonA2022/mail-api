"""管理员登录API路由"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.admin.login_service import AdminLoginService
from typing import Optional


class AdminLoginRequest(BaseModel):
    """管理员登录请求模型"""
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """管理员登录响应模型"""
    success: bool
    message: str
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    admin: Optional[dict] = None
    requires_two_factor: Optional[bool] = False


router = APIRouter(prefix="/api/admin", tags=["管理员登录"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_request: AdminLoginRequest, request: Request):
    """
    管理员登录接口
    
    Args:
        login_request: 登录信息（用户名和密码）
        request: 请求对象
        
    Returns:
        登录结果，包含token和管理员信息
    """
    # 获取客户端IP和User-Agent
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 调用登录服务
    login_service = AdminLoginService()
    result = login_service.login(
        username=login_request.username,
        password=login_request.password,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    if result["success"]:
        return JSONResponse(
            status_code=200,
            content=result
        )
    else:
        return JSONResponse(
            status_code=401,
            content=result
        )


@router.post("/logout")
async def admin_logout(authorization: Optional[str] = Header(None)):
    """
    管理员登出接口
    
    Args:
        authorization: Authorization header中的token
        
    Returns:
        登出结果
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    login_service = AdminLoginService()
    success = login_service.logout(token)
    
    if success:
        return {"success": True, "message": "登出成功"}
    else:
        return {"success": False, "message": "登出失败"}


@router.get("/verify")
async def verify_admin_token(authorization: Optional[str] = Header(None)):
    """
    验证管理员token是否有效
    
    Args:
        authorization: Authorization header中的token
        
    Returns:
        验证结果
    """
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "未提供有效的认证令牌"}
        )
    
    token = authorization.replace("Bearer ", "")
    
    # 这里可以添加token验证逻辑
    # 暂时返回成功
    return {"success": True, "message": "Token有效"}
