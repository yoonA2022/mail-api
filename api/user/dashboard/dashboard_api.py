"""
用户仪表板 API
提供用户统计数据和概览信息
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any, Optional
from services.dashboard.dashboard_service import DashboardService
from services.user.verification_service import VerificationService

router = APIRouter(prefix="/api/user/dashboard", tags=["用户仪表板"])


@router.get("/stats")
async def get_dashboard_stats(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    获取用户仪表板统计数据
    
    Returns:
        包含用户信息、IMAP账户统计、邮件统计、订单统计和最近活动的字典
    """
    # 验证token
    if not authorization or not authorization.startswith("Bearer "):
        print(f"[Dashboard] Authorization header 无效: {authorization}")
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    # 使用 VerificationService 验证 token（会检查 JWT 和 session）
    verification_service = VerificationService()
    payload = verification_service.verify_token(token)
    
    if not payload:
        print(f"[Dashboard] Token 验证失败")
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的认证信息")
    
    # 调用服务层获取数据
    try:
        dashboard_service = DashboardService()
        stats = dashboard_service.get_user_stats(user_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"获取仪表板统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")
