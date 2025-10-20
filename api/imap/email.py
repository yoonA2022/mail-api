"""IMAP 邮件 API 路由"""
from fastapi import APIRouter, HTTPException
from services.imap.email import ImapEmailService
from services.imap.account import ImapAccountService
from typing import Optional

router = APIRouter(
    prefix="/api/imap",
    tags=["IMAP邮件"]
)


@router.get("/accounts")
async def get_accounts():
    """获取所有IMAP账户列表"""
    accounts = ImapAccountService.get_all_accounts()
    return {
        "success": True,
        "data": accounts,
        "count": len(accounts)
    }


@router.get("/emails/count/{account_id}")
async def get_email_count(account_id: int):
    """获取指定账户的邮件总数"""
    result = ImapEmailService.get_email_count(account_id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.get("/emails/latest/{account_id}")
async def get_latest_emails(account_id: int, limit: Optional[int] = 10):
    """获取指定账户的最新邮件"""
    result = ImapEmailService.get_latest_emails(account_id, limit)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


@router.get("/account/{account_id}")
async def get_account_detail(account_id: int):
    """获取指定账户的详细配置信息（不含密码）"""
    account = ImapAccountService.get_account_by_id(account_id, include_password=False)
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    # 移除密码字段
    account_info = dict(account)
    account_info['password'] = '******'  # 隐藏密码
    
    return {
        "success": True,
        "data": account_info
    }
