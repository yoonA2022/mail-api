"""用户注册API路由"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from models.user import UserRegister, RegisterResponse
from services.user.register_service import RegisterService

router = APIRouter(prefix="/api/user", tags=["用户注册"])


@router.post("/register", response_model=RegisterResponse)
async def register(user_register: UserRegister, request: Request):
    """
    用户注册接口
    
    Args:
        user_register: 注册信息（用户名、邮箱、密码）
        request: 请求对象
        
    Returns:
        注册结果，包含用户信息
    """
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    
    # 调用注册服务
    register_service = RegisterService()
    result = register_service.register(
        username=user_register.username,
        email=user_register.email,
        password=user_register.password,
        nickname=user_register.nickname,
        ip_address=client_ip
    )
    
    if result["success"]:
        return JSONResponse(
            status_code=201,
            content=result
        )
    else:
        return JSONResponse(
            status_code=400,
            content=result
        )


@router.get("/check-username/{username}")
async def check_username(username: str):
    """
    检查用户名是否可用
    
    Args:
        username: 用户名
        
    Returns:
        可用性结果
    """
    register_service = RegisterService()
    available = register_service.check_username_available(username)
    
    return {
        "available": available,
        "message": "用户名可用" if available else "用户名已被使用"
    }


@router.get("/check-email/{email}")
async def check_email(email: str):
    """
    检查邮箱是否可用
    
    Args:
        email: 邮箱地址
        
    Returns:
        可用性结果
    """
    register_service = RegisterService()
    available = register_service.check_email_available(email)
    
    return {
        "available": available,
        "message": "邮箱可用" if available else "邮箱已被注册"
    }
