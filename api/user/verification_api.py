"""用户验证API路由"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from services.user.verification_service import VerificationService
from typing import Optional

router = APIRouter(prefix="/api/user", tags=["用户验证"])


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    验证token接口
    
    Args:
        authorization: Authorization header中的token
        
    Returns:
        验证结果和用户信息
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    verification_service = VerificationService()
    payload = verification_service.verify_token(token)
    
    if payload:
        return {
            "success": True,
            "message": "令牌有效",
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role")
        }
    else:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    获取当前用户信息
    
    Args:
        authorization: Authorization header中的token
        
    Returns:
        当前用户信息
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    verification_service = VerificationService()
    user = verification_service.get_user_by_token(token)
    
    if user:
        return {
            "success": True,
            "user": user
        }
    else:
        raise HTTPException(status_code=401, detail="令牌无效或用户不存在")


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    刷新访问令牌
    
    Args:
        refresh_token: 刷新令牌
        
    Returns:
        新的访问令牌
    """
    verification_service = VerificationService()
    result = verification_service.refresh_session(refresh_token)
    
    if result:
        return JSONResponse(
            status_code=200,
            content=result
        )
    else:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")
