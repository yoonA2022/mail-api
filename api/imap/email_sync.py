"""IMAP 邮件同步 API 路由"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from services.imap.email_sync import EmailSyncService
from typing import Optional

router = APIRouter(
    prefix="/api/imap/sync",
    tags=["IMAP邮件同步"]
)


@router.post("/email-list/{account_id}")
async def sync_email_list(account_id: int, folder: Optional[str] = 'INBOX', background_tasks: BackgroundTasks = None):
    """
    同步邮件列表到数据库（只同步元数据）
    
    Args:
        account_id: IMAP账户ID
        folder: 邮件文件夹，默认INBOX
        background_tasks: 后台任务（可选，用于异步同步）
    
    Returns:
        同步结果
    """
    try:
        # 同步邮件列表
        result = EmailSyncService.sync_email_list(account_id, folder)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/status/{account_id}")
async def get_sync_status(account_id: int, limit: Optional[int] = 10):
    """
    获取账户的同步历史记录
    
    Args:
        account_id: IMAP账户ID
        limit: 返回记录数量，默认10条
    
    Returns:
        同步历史记录
    """
    try:
        from config.database import get_db_connection
        
        db = get_db_connection()
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, account_id, folder, status, 
                    total_emails, new_emails, updated_emails, deleted_emails,
                    start_time, end_time, duration, error_message
                FROM email_sync_log
                WHERE account_id = %s
                ORDER BY start_time DESC
                LIMIT %s
            """, (account_id, limit))
            
            logs = cursor.fetchall()
            
            return {
                "success": True,
                "data": logs,
                "count": len(logs)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.get("/emails/{account_id}")
async def get_email_list_from_db(
    account_id: int, 
    folder: Optional[str] = 'INBOX',
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
):
    """
    获取邮件列表（智能模式）
    
    逻辑：
    1. 先检查数据库是否有邮件
    2. 如果有，直接返回数据库中的邮件
    3. 如果没有，先同步邮件到数据库，再返回
    
    Args:
        account_id: IMAP账户ID
        folder: 邮件文件夹，默认INBOX
        limit: 返回记录数量，默认100条
        offset: 偏移量，默认0
    
    Returns:
        邮件列表
    """
    try:
        from config.database import get_db_connection
        
        # 1. 先检查数据库中是否有邮件
        db = get_db_connection()
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM email_list
                WHERE account_id = %s AND folder = %s
            """, (account_id, folder))
            
            total = cursor.fetchone()['total']
        
        # 2. 如果数据库为空，先同步邮件
        if total == 0:
            print(f"📥 数据库为空，开始同步账户 {account_id} 的邮件...")
            sync_result = EmailSyncService.sync_email_list(account_id, folder)
            
            if not sync_result.get('success'):
                raise HTTPException(status_code=400, detail=sync_result.get('error'))
        
        # 3. 同步后，使用新的连接查询数据（避免事务隔离问题）
        db = get_db_connection()
        with db.get_cursor() as cursor:
            # 重新查询总数
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM email_list
                WHERE account_id = %s AND folder = %s
            """, (account_id, folder))
            total = cursor.fetchone()['total']
            
            # 查询邮件列表
            print(f"📊 查询邮件列表: account_id={account_id}, folder={folder}, total={total}, limit={limit}, offset={offset}")
            cursor.execute("""
                SELECT 
                    id, uid, message_id, subject, from_email, from_name,
                    to_emails, date, size, flags, has_attachments, 
                    attachment_count, attachment_names, text_preview, 
                    is_html, folder, synced_at
                FROM email_list
                WHERE account_id = %s AND folder = %s
                ORDER BY date DESC
                LIMIT %s OFFSET %s
            """, (account_id, folder, limit, offset))
            
            emails = cursor.fetchall()
            print(f"✅ 查询结果: 返回 {len(emails)} 封邮件")
            
            return {
                "success": True,
                "data": emails,
                "count": len(emails),
                "total": total,
                "limit": limit,
                "offset": offset
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取邮件列表失败: {str(e)}")
