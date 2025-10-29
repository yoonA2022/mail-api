"""用户登录API路由"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from models.user import UserLogin, LoginResponse
from services.user.login_service import LoginService
from typing import Optional

router = APIRouter(prefix="/api/user", tags=["用户登录"])


@router.post("/login", response_model=LoginResponse)
async def login(user_login: UserLogin, request: Request):
    """
    用户登录接口
    
    Args:
        user_login: 登录信息（邮箱和密码）
        request: 请求对象
        
    Returns:
        登录结果，包含token和用户信息
    """
    # 获取客户端IP和User-Agent
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 调用登录服务
    login_service = LoginService()
    result = login_service.login(
        email=user_login.email,
        password=user_login.password,
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
async def logout(authorization: Optional[str] = Header(None)):
    """
    用户登出接口
    
    Args:
        authorization: Authorization header中的token
        
    Returns:
        登出结果
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    login_service = LoginService()
    success = login_service.logout(token)
    
    if success:
        return {"success": True, "message": "登出成功"}
    else:
        return {"success": False, "message": "登出失败"}
