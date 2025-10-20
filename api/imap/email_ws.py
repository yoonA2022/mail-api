"""WebSocket 邮件连接 API 路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.websocket.websocket import connection_manager, WebSocketService
from services.websocket.imap.email_monitor_v2 import EmailMonitorV2
from typing import Optional
import json
import asyncio

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


@router.websocket("/email/{account_id}")
async def websocket_email_endpoint(
    websocket: WebSocket,
    account_id: int,
    device_name: Optional[str] = Query(None, description="设备名称"),
    device_type: Optional[str] = Query(None, description="设备类型")
):
    """
    WebSocket邮件连接端点
    
    Args:
        websocket: WebSocket连接对象
        account_id: 账户ID
        device_name: 设备名称（可选）
        device_type: 设备类型（可选，如：web/mobile/desktop）
    
    使用示例：
        ws://localhost:8000/ws/email/1?device_name=Chrome&device_type=web
    """
    # 设备信息
    device_info = {
        "device_name": device_name or "Unknown",
        "device_type": device_type or "web"
    }
    
    # 建立连接
    connection_id = await connection_manager.connect(websocket, account_id, device_info)
    
    try:
        # 添加账户到全局监控列表（非阻塞，不影响连接速度）
        await EmailMonitorV2.add_account(account_id)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                # 解析JSON消息
                message = json.loads(data)
                
                # 处理消息
                await WebSocketService.handle_client_message(connection_id, message)
            
            except json.JSONDecodeError:
                # JSON解析失败
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "无效的JSON格式"
                })
            
            except Exception as e:
                # 其他错误
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": f"处理消息时发生错误: {str(e)}"
                })
    
    except WebSocketDisconnect:
        # 客户端断开连接
        connection_manager.disconnect(connection_id)
        
        # 如果该账户没有其他连接了，从监控列表移除
        connections = connection_manager.get_account_connections(account_id)
        if not connections:
            await EmailMonitorV2.remove_account(account_id)
    
    except Exception as e:
        # 其他异常
        print(f"WebSocket连接异常: {e}")
        connection_manager.disconnect(connection_id)
        
        # 如果该账户没有其他连接了，从监控列表移除
        connections = connection_manager.get_account_connections(account_id)
        if not connections:
            await EmailMonitorV2.remove_account(account_id)


@router.get("/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息"""
    stats = connection_manager.get_statistics()
    return {
        "success": True,
        "data": stats
    }


@router.get("/connections/{account_id}")
async def get_account_connections(account_id: int):
    """获取指定账户的所有连接"""
    connection_ids = connection_manager.get_account_connections(account_id)
    
    connections = []
    for conn_id in connection_ids:
        info = connection_manager.get_connection_info(conn_id)
        if info:
            connections.append({
                "connection_id": conn_id,
                "device_info": info["device_info"],
                "connected_at": info["connected_at"],
                "last_heartbeat": info["last_heartbeat"]
            })
    
    return {
        "success": True,
        "account_id": account_id,
        "total_connections": len(connections),
        "connections": connections
    }


@router.post("/check-new-emails/{account_id}")
async def check_new_emails(account_id: int, folder: str = Query('INBOX')):
    """
    手动触发检查新邮件（已废弃，使用全局监控服务）
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
    
    注意：此API已废弃，全局监控服务会自动检测新邮件
    """
    return {
        "success": False,
        "error": "此API已废弃，请使用全局监控服务（EmailMonitorV2）",
        "message": "全局监控服务会自动检测新邮件，无需手动触发"
    }


@router.post("/sync-now/{account_id}")
async def sync_now(account_id: int, folder: str = Query('INBOX')):
    """
    手动触发同步并通知（已废弃，使用全局监控服务）
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
    
    注意：此API已废弃，全局监控服务会自动同步新邮件
    """
    return {
        "success": False,
        "error": "此API已废弃，请使用全局监控服务（EmailMonitorV2）",
        "message": "全局监控服务会自动同步新邮件，无需手动触发"
    }


@router.get("/monitor-status/{account_id}")
async def get_monitor_status(account_id: int):
    """
    获取监控状态（V1，已废弃）
    
    Args:
        account_id: 账户ID
    
    注意：此API已废弃，请使用 /ws/monitor-status-v2
    """
    return {
        "success": False,
        "error": "此API已废弃，请使用 /ws/monitor-status-v2",
        "message": "V1监控服务已停用，请使用全局监控服务（V2）"
    }


@router.get("/monitor-status-v2")
async def get_monitor_status_v2():
    """
    获取全局监控状态（V2）
    
    返回所有正在监控的账户信息
    """
    status = EmailMonitorV2.get_monitor_status()
    return {
        "success": True,
        "data": status
    }


@router.post("/start-monitor/{account_id}")
async def start_monitor(account_id: int, folder: str = Query('INBOX'), interval: int = Query(60)):
    """
    手动启动监控（已废弃，使用全局监控服务）
    
    Args:
        account_id: 账户ID
        folder: 文件夹名称，默认INBOX
        interval: 检查间隔（秒），默认60秒
    
    注意：此API已废弃，全局监控服务在应用启动时自动启动
    """
    return {
        "success": False,
        "error": "此API已废弃，请使用全局监控服务（EmailMonitorV2）",
        "message": "全局监控服务在应用启动时自动启动，WebSocket连接时自动添加账户到监控列表"
    }


@router.post("/stop-monitor/{account_id}")
async def stop_monitor(account_id: int):
    """
    手动停止监控（已废弃，使用全局监控服务）
    
    Args:
        account_id: 账户ID
    
    注意：此API已废弃，全局监控服务由应用生命周期管理
    """
    return {
        "success": False,
        "error": "此API已废弃，请使用全局监控服务（EmailMonitorV2）",
        "message": "全局监控服务由应用生命周期管理，WebSocket断开时自动从监控列表移除账户"
    }
