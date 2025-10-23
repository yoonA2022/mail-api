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


@router.post("/refresh-status/{account_id}")
async def refresh_mail_status(account_id: int, folder: Optional[str] = 'INBOX'):
    """
    刷新邮件状态（已读、星标等）
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认 INBOX
        
    Returns:
        刷新结果
    """
    from services.imap.mail_service_async import AsyncMailService
    
    # 使用异步方法刷新邮件状态
    result = await AsyncMailService.refresh_mail_status(account_id, folder)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result


@router.get("/email/{account_id}/{email_id}")
async def get_email_detail(account_id: int, email_id: int):
    """
    获取邮件详情（包括完整正文）
    
    Args:
        account_id: 账户ID
        email_id: 邮件ID（数据库ID）
        
    Returns:
        邮件详情，包含完整的文本和HTML内容
    """
    from services.imap.mail_service import MailService
    
    # 获取邮件详情
    result = MailService.get_email_detail(account_id, email_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', '邮件不存在'))
    
    return result


@router.post("/email/{account_id}/{email_id}/mark-read")
async def mark_email_as_read(account_id: int, email_id: int):
    """
    标记邮件为已读
    
    Args:
        account_id: 账户ID
        email_id: 邮件ID（数据库ID）
        
    Returns:
        标记结果
    """
    from services.imap.mail_service import MailService
    
    # 标记邮件为已读
    result = MailService.mark_as_read(account_id, email_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', '标记失败'))
    
    return result