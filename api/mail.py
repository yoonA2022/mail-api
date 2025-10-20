"""
邮件API - 简洁版
提供：邮件列表查询、WebSocket连接
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.mail_service import MailService
from services.websocket_service import WebSocketService
from typing import Optional


router = APIRouter(
    prefix="/api/mail",
    tags=["邮件"]
)


@router.get("/list")
async def get_mail_list(
    account_id: int = Query(..., description="账户ID"),
    folder: str = Query('INBOX', description="文件夹名称"),
    limit: int = Query(100, description="返回数量"),
    offset: int = Query(0, description="偏移量")
):
    """
    获取邮件列表（智能模式）
    
    逻辑：
    1. 先查询数据库
    2. 如果数据库为空，从IMAP同步
    3. 返回邮件列表
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
        limit: 返回数量，默认100
        offset: 偏移量，默认0
    
    Returns:
        {
            "success": true,
            "data": [...],
            "count": 22,
            "total": 22
        }
    """
    result = MailService.get_mail_list(account_id, folder, limit, offset)
    return result


@router.post("/sync")
async def sync_mail(
    account_id: int = Query(..., description="账户ID"),
    folder: str = Query('INBOX', description="文件夹名称")
):
    """
    手动同步邮件
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
    
    Returns:
        {
            "success": true,
            "count": 22,
            "message": "同步完成"
        }
    """
    result = MailService.sync_from_imap(account_id, folder)
    return result


@router.get("/check")
async def check_new_mail(
    account_id: int = Query(..., description="账户ID"),
    folder: str = Query('INBOX', description="文件夹名称")
):
    """
    检测是否有新邮件
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
    
    Returns:
        {
            "has_new": true,
            "server_count": 25,
            "db_count": 22,
            "new_count": 3
        }
    """
    result = MailService.check_new_mail(account_id, folder)
    return result


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    account_id: int = Query(..., description="账户ID")
):
    """
    WebSocket连接
    
    用于实时推送新邮件
    
    Args:
        websocket: WebSocket对象
        account_id: 账户ID
    """
    # 建立连接
    connection_id = await WebSocketService.connect(websocket, account_id)
    
    try:
        # 保持连接，处理客户端消息
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            # 可以在这里处理客户端发来的消息
            # 例如：心跳、手动刷新等
            
    except WebSocketDisconnect:
        # 客户端断开连接
        await WebSocketService.disconnect(websocket, account_id)
    
    except Exception as e:
        # 其他异常
        print(f"❌ WebSocket异常: {e}")
        await WebSocketService.disconnect(websocket, account_id)


@router.get("/status")
async def get_status():
    """
    获取服务状态
    
    Returns:
        {
            "online_accounts": [1, 2, 3],
            "total_connections": 5,
            "timestamp": "2025-10-20T17:00:00"
        }
    """
    from datetime import datetime
    
    return {
        "online_accounts": list(WebSocketService.get_online_accounts()),
        "total_connections": WebSocketService.get_total_connections(),
        "timestamp": datetime.now().isoformat()
    }
