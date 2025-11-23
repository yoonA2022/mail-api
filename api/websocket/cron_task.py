"""
定时任务 WebSocket API
提供实时日志推送功能
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.websocket.cron_websocket_service import CronWebSocketService
from config.database import DatabaseConnection
from datetime import datetime

router = APIRouter(
    prefix="/api/cron/ws",
    tags=["定时任务WebSocket"]
)


@router.websocket("/logs")
async def websocket_task_logs(
    websocket: WebSocket,
    task_id: int = Query(..., description="任务ID")
):
    """
    WebSocket连接 - 实时接收定时任务日志
    
    流程:
    1. 建立 WebSocket 连接
    2. 从数据库获取任务的日志文件路径
    3. 推送历史日志（如果文件存在）
    4. 保持连接，接收实时日志
    
    Args:
        websocket: WebSocket对象
        task_id: 任务ID
    """
    # 建立连接
    connection_id = await CronWebSocketService.connect(websocket, task_id)
    
    try:
        # 从数据库获取日志文件路径
        db = DatabaseConnection()
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT log_file_path FROM cron_tasks WHERE id = %s",
                (task_id,)
            )
            result = cursor.fetchone()
            log_file_path = result['log_file_path'] if result and result.get('log_file_path') else None
            
            print(f"📋 查询任务 {task_id} 的日志路径: {log_file_path}")
        
        # 如果有日志文件路径，推送历史日志
        if log_file_path:
            await CronWebSocketService.push_history_logs(task_id, log_file_path, websocket)
        
        # 保持连接，处理客户端消息
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            # 可以在这里处理客户端发来的消息
            # 例如：心跳、订阅特定任务等
            
    except WebSocketDisconnect:
        # 客户端断开连接
        print(f"ℹ️ WebSocket客户端断开连接: task_id={task_id}")
        await CronWebSocketService.disconnect(websocket, task_id)
    
    except Exception as e:
        # 其他异常
        import traceback
        print(f"❌ WebSocket异常: task_id={task_id}, error={str(e)}")
        print(f"异常类型: {type(e).__name__}")
        print(f"异常详情:\n{traceback.format_exc()}")
        await CronWebSocketService.disconnect(websocket, task_id)


@router.get("/status")
async def get_websocket_status():
    """
    获取WebSocket服务状态
    
    Returns:
        {
            "total_connections": 5,
            "timestamp": "2025-11-20T15:00:00"
        }
    """
    total = sum(len(conns) for conns in CronWebSocketService._connections.values())
    return {
        "total_connections": total,
        "timestamp": datetime.now().isoformat()
    }
