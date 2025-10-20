"""
WebSocket服务 - 简洁版
负责：WebSocket连接管理、消息推送
"""

from fastapi import WebSocket
from typing import Dict, List, Set
from datetime import datetime
import json
import uuid


def json_serial(obj):
    """JSON序列化辅助函数，处理datetime等特殊类型"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class WebSocketService:
    """WebSocket服务 - 管理所有WebSocket连接"""
    
    # 存储所有连接: {account_id: [websocket1, websocket2, ...]}
    _connections: Dict[int, List[WebSocket]] = {}
    
    # 存储连接信息: {websocket_id: {websocket, account_id, connected_at}}
    _connection_info: Dict[str, dict] = {}
    
    @classmethod
    async def connect(cls, websocket: WebSocket, account_id: int) -> str:
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket对象
            account_id: 账户ID
            
        Returns:
            connection_id: 连接ID
        """
        # 接受连接
        await websocket.accept()
        
        # 生成连接ID
        connection_id = str(uuid.uuid4())
        
        # 保存连接信息
        cls._connection_info[connection_id] = {
            'websocket': websocket,
            'account_id': account_id,
            'connected_at': datetime.now().isoformat()
        }
        
        # 添加到账户连接列表
        if account_id not in cls._connections:
            cls._connections[account_id] = []
        
        cls._connections[account_id].append(websocket)
        
        print(f"✅ WebSocket连接建立: {connection_id} | 账户: {account_id} | 总连接数: {cls.get_total_connections()}")
        
        # 发送连接成功消息
        await websocket.send_json({
            'type': 'connected',
            'connection_id': connection_id,
            'account_id': account_id,
            'message': '连接成功',
            'timestamp': datetime.now().isoformat()
        })
        
        return connection_id
    
    @classmethod
    async def disconnect(cls, websocket: WebSocket, account_id: int):
        """
        断开WebSocket连接
        
        Args:
            websocket: WebSocket对象
            account_id: 账户ID
        """
        # 从账户连接列表移除
        if account_id in cls._connections:
            if websocket in cls._connections[account_id]:
                cls._connections[account_id].remove(websocket)
            
            # 如果该账户没有连接了，删除键
            if not cls._connections[account_id]:
                del cls._connections[account_id]
        
        # 从连接信息中移除
        connection_id = None
        for conn_id, info in list(cls._connection_info.items()):
            if info['websocket'] == websocket:
                connection_id = conn_id
                del cls._connection_info[conn_id]
                break
        
        print(f"❌ WebSocket连接断开: {connection_id} | 账户: {account_id} | 剩余连接数: {cls.get_total_connections()}")
    
    @classmethod
    async def push_to_account(cls, account_id: int, message: dict):
        """
        向指定账户的所有连接推送消息
        
        Args:
            account_id: 账户ID
            message: 消息内容
        """
        if account_id not in cls._connections:
            print(f"⚠️ 账户 {account_id} 没有活跃连接")
            return
        
        # 向该账户的所有连接推送
        disconnected = []
        for websocket in cls._connections[account_id]:
            try:
                # 手动序列化，处理datetime等特殊类型
                json_str = json.dumps(message, default=json_serial, ensure_ascii=False)
                await websocket.send_text(json_str)
            except Exception as e:
                print(f"⚠️ 推送消息失败: {e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            if ws in cls._connections[account_id]:
                cls._connections[account_id].remove(ws)
    
    @classmethod
    async def push_new_mail(cls, account_id: int, emails: list):
        """
        推送新邮件到前端
        
        Args:
            account_id: 账户ID
            emails: 新邮件列表
        """
        message = {
            'type': 'new_mail',
            'data': emails,
            'count': len(emails),
            'timestamp': datetime.now().isoformat()
        }
        
        await cls.push_to_account(account_id, message)
        print(f"📬 已推送 {len(emails)} 封新邮件到账户 {account_id}")
    
    @classmethod
    def get_online_accounts(cls) -> Set[int]:
        """
        获取所有在线账户ID
        
        Returns:
            Set[int]: 账户ID集合
        """
        return set(cls._connections.keys())
    
    @classmethod
    def get_total_connections(cls) -> int:
        """
        获取总连接数
        
        Returns:
            int: 连接数
        """
        return sum(len(conns) for conns in cls._connections.values())
    
    @classmethod
    def get_account_connections(cls, account_id: int) -> int:
        """
        获取指定账户的连接数
        
        Args:
            account_id: 账户ID
            
        Returns:
            int: 连接数
        """
        return len(cls._connections.get(account_id, []))
