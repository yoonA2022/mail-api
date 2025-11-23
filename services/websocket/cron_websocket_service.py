"""
定时任务 WebSocket 服务
负责：定时任务日志的实时推送
"""

from fastapi import WebSocket
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid
import asyncio


def json_serial(obj):
    """JSON序列化辅助函数，处理datetime等特殊类型"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class CronWebSocketService:
    """定时任务 WebSocket 服务"""
    
    # 存储任务连接: {task_id: [websocket1, websocket2, ...]}
    _connections: Dict[int, List[WebSocket]] = {}
    
    @classmethod
    async def connect(cls, websocket: WebSocket, task_id: int) -> str:
        """建立 WebSocket 连接"""
        await websocket.accept()
        
        # 添加到连接列表
        if task_id not in cls._connections:
            cls._connections[task_id] = []
        cls._connections[task_id].append(websocket)
        
        # 发送连接成功消息
        await websocket.send_json({
            'type': 'connected',
            'task_id': task_id,
            'message': f'已连接到任务 {task_id} 日志服务',
            'timestamp': datetime.now().isoformat()
        })
        
        return str(uuid.uuid4())
    
    @classmethod
    async def disconnect(cls, websocket: WebSocket, task_id: int):
        """断开 WebSocket 连接"""
        if task_id in cls._connections:
            if websocket in cls._connections[task_id]:
                cls._connections[task_id].remove(websocket)
            
            # 如果没有连接了，删除键
            if not cls._connections[task_id]:
                del cls._connections[task_id]
    
    @classmethod
    async def push_history_logs(cls, task_id: int, log_file_path: str, websocket: WebSocket):
        """
        读取历史日志文件并推送到前端
        
        Args:
            task_id: 任务ID
            log_file_path: 日志文件路径（相对于项目根目录）
            websocket: WebSocket 连接
        """
        try:
            # 构建完整路径
            project_root = Path(__file__).parent.parent.parent
            full_path = project_root / log_file_path
            
            print(f"📂 准备读取日志文件: {full_path}")
            print(f"   项目根目录: {project_root}")
            print(f"   相对路径: {log_file_path}")
            print(f"   文件是否存在: {full_path.exists()}")
            
            if not full_path.exists():
                # 文件不存在，发送提示
                print(f"⚠️ 日志文件不存在: {full_path}")
                await websocket.send_json({
                    'type': 'log_line',
                    'task_id': task_id,
                    'execution_id': 'history',
                    'line': f'[系统] 日志文件不存在: {log_file_path}',
                    'is_error': False,
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # 读取文件内容（最后 1000 行）
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # 只取最后 1000 行
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                print(f"📄 读取到 {len(lines)} 行日志，准备推送最后 {len(recent_lines)} 行")
                
                # 逐行推送
                for idx, line in enumerate(recent_lines):
                    line = line.rstrip()
                    if line:  # 跳过空行
                        await websocket.send_json({
                            'type': 'log_line',
                            'task_id': task_id,
                            'execution_id': 'history',
                            'line': line,
                            'is_error': False,
                            'timestamp': datetime.now().isoformat()
                        })
                        await asyncio.sleep(0.001)  # 避免推送过快
                
                print(f"✅ 历史日志推送完成: {len(recent_lines)} 行")
                
        except Exception as e:
            # 发送错误消息
            await websocket.send_json({
                'type': 'log_line',
                'task_id': task_id,
                'execution_id': 'history',
                'line': f'[错误] 读取日志文件失败: {str(e)}',
                'is_error': True,
                'timestamp': datetime.now().isoformat()
            })
