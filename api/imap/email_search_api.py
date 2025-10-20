"""邮件搜索 API 路由"""
from fastapi import APIRouter, HTTPException, Query
from services.imap.email_search import EmailSearchService
from typing import Optional

router = APIRouter(
    prefix="/api/imap/search",
    tags=["邮件搜索"]
)


@router.get("/emails/{account_id}")
async def search_emails(
    account_id: int,
    keyword: str = Query(..., description="搜索关键词"),
    folder: str = Query('INBOX', description="文件夹名称"),
    fields: Optional[str] = Query(None, description="搜索字段，逗号分隔，如: subject,from_name,from_email"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    搜索邮件（通用搜索）
    
    Args:
        account_id: 账户ID
        keyword: 搜索关键词
        folder: 文件夹名称，默认INBOX
        fields: 搜索字段，逗号分隔（可选），默认搜索主题、发件人、正文
        limit: 返回数量，默认100
        offset: 偏移量，默认0
    
    Returns:
        搜索结果
    """
    try:
        # 解析搜索字段
        search_fields = None
        if fields:
            search_fields = [f.strip() for f in fields.split(',')]
        
        # 执行搜索
        result = EmailSearchService.search_emails(
            account_id=account_id,
            keyword=keyword,
            folder=folder,
            search_fields=search_fields,
            limit=limit,
            offset=offset
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/by-sender/{account_id}")
async def search_by_sender(
    account_id: int,
    sender: str = Query(..., description="发件人（邮箱或名称）"),
    folder: str = Query('INBOX', description="文件夹名称"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    按发件人搜索
    
    Args:
        account_id: 账户ID
        sender: 发件人（邮箱或名称）
        folder: 文件夹名称
        limit: 返回数量
        offset: 偏移量
    """
    try:
        result = EmailSearchService.search_by_sender(
            account_id=account_id,
            sender=sender,
            folder=folder,
            limit=limit,
            offset=offset
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/by-subject/{account_id}")
async def search_by_subject(
    account_id: int,
    subject: str = Query(..., description="主题关键词"),
    folder: str = Query('INBOX', description="文件夹名称"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    按主题搜索
    
    Args:
        account_id: 账户ID
        subject: 主题关键词
        folder: 文件夹名称
        limit: 返回数量
        offset: 偏移量
    """
    try:
        result = EmailSearchService.search_by_subject(
            account_id=account_id,
            subject=subject,
            folder=folder,
            limit=limit,
            offset=offset
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/with-attachments/{account_id}")
async def search_with_attachments(
    account_id: int,
    keyword: Optional[str] = Query(None, description="可选的搜索关键词"),
    folder: str = Query('INBOX', description="文件夹名称"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    搜索有附件的邮件
    
    Args:
        account_id: 账户ID
        keyword: 可选的搜索关键词
        folder: 文件夹名称
        limit: 返回数量
        offset: 偏移量
    """
    try:
        result = EmailSearchService.search_with_attachments(
            account_id=account_id,
            keyword=keyword,
            folder=folder,
            limit=limit,
            offset=offset
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

