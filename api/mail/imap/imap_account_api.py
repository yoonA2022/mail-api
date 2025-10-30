"""IMAP账户API路由"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from models.mail.imap.imap_account import (
    ImapAccountCreate,
    ImapAccountUpdate,
    ImapAccountListResponse,
    ImapAccountDetailResponse
)
from services.mail.imap.imap_account_service import ImapAccountService
from typing import Optional

router = APIRouter(prefix="/api/imap", tags=["IMAP账户管理"])


@router.get("/accounts", response_model=ImapAccountListResponse)
async def get_imap_accounts(
    user_id: Optional[int] = None,
    authorization: Optional[str] = Header(None)
):
    """
    获取IMAP账户列表
    
    Args:
        user_id: 可选，用户ID，如果提供则只返回该用户的账户
        authorization: Authorization header中的token
        
    Returns:
        IMAP账户列表
    """
    try:
        service = ImapAccountService()
        accounts = service.get_all_accounts(user_id=user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "获取账户列表成功",
                "data": [account.model_dump(mode='json') for account in accounts],
                "total": len(accounts)
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取账户列表失败: {str(e)}",
                "data": [],
                "total": 0
            }
        )


@router.get("/accounts/{account_id}", response_model=ImapAccountDetailResponse)
async def get_imap_account(
    account_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    获取IMAP账户详情
    
    Args:
        account_id: 账户ID
        authorization: Authorization header中的token
        
    Returns:
        IMAP账户详情
    """
    try:
        service = ImapAccountService()
        account = service.get_account_by_id(account_id)
        
        if not account:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "账户不存在",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "获取账户详情成功",
                "data": account.model_dump(mode='json')
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取账户详情失败: {str(e)}",
                "data": None
            }
        )


@router.post("/accounts", response_model=ImapAccountDetailResponse)
async def create_imap_account(
    account_data: ImapAccountCreate,
    authorization: Optional[str] = Header(None)
):
    """
    创建IMAP账户
    
    Args:
        account_data: 账户数据
        authorization: Authorization header中的token
        
    Returns:
        创建的账户信息
    """
    try:
        service = ImapAccountService()
        account = service.create_account(account_data)
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": "创建账户成功",
                "data": account.model_dump(mode='json')
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"创建账户失败: {str(e)}",
                "data": None
            }
        )


@router.put("/accounts/{account_id}", response_model=ImapAccountDetailResponse)
async def update_imap_account(
    account_id: int,
    account_data: ImapAccountUpdate,
    authorization: Optional[str] = Header(None)
):
    """
    更新IMAP账户
    
    Args:
        account_id: 账户ID
        account_data: 更新的账户数据
        authorization: Authorization header中的token
        
    Returns:
        更新后的账户信息
    """
    try:
        service = ImapAccountService()
        account = service.update_account(account_id, account_data)
        
        if not account:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "账户不存在",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "更新账户成功",
                "data": account.model_dump(mode='json')
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"更新账户失败: {str(e)}",
                "data": None
            }
        )


@router.delete("/accounts/{account_id}")
async def delete_imap_account(
    account_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    删除IMAP账户
    
    Args:
        account_id: 账户ID
        authorization: Authorization header中的token
        
    Returns:
        删除结果
    """
    try:
        service = ImapAccountService()
        success = service.delete_account(account_id)
        
        if not success:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "账户不存在或删除失败"
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "删除账户成功"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"删除账户失败: {str(e)}"
            }
        )


@router.post("/accounts/{account_id}/sync")
async def sync_imap_account(
    account_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    立即同步IMAP账户
    
    Args:
        account_id: 账户ID
        authorization: Authorization header中的token
        
    Returns:
        同步结果
    """
    try:
        service = ImapAccountService()
        
        # 检查账户是否存在
        account = service.get_account_by_id(account_id)
        if not account:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "账户不存在"
                }
            )
        
        # 更新最后同步时间
        service.update_last_sync_time(account_id)
        
        # TODO: 这里应该触发实际的邮件同步逻辑
        # 目前只是更新同步时间作为演示
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "同步请求已提交"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"同步失败: {str(e)}"
            }
        )
