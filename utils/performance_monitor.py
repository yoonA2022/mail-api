"""
性能监控工具
用于监控API响应时间和系统性能
"""

import time
from functools import wraps
from typing import Callable
import asyncio


class PerformanceMonitor:
    """性能监控器"""
    
    # 存储性能指标
    _metrics = {
        'api_calls': {},      # API调用次数
        'total_time': {},     # 总耗时
        'avg_time': {},       # 平均耗时
        'max_time': {},       # 最大耗时
        'min_time': {},       # 最小耗时
    }
    
    @classmethod
    def log_timing(cls, operation: str, duration: float):
        """
        记录操作耗时
        
        Args:
            operation: 操作名称
            duration: 耗时（秒）
        """
        if operation not in cls._metrics['api_calls']:
            cls._metrics['api_calls'][operation] = 0
            cls._metrics['total_time'][operation] = 0
            cls._metrics['max_time'][operation] = 0
            cls._metrics['min_time'][operation] = float('inf')
        
        cls._metrics['api_calls'][operation] += 1
        cls._metrics['total_time'][operation] += duration
        cls._metrics['max_time'][operation] = max(cls._metrics['max_time'][operation], duration)
        cls._metrics['min_time'][operation] = min(cls._metrics['min_time'][operation], duration)
        cls._metrics['avg_time'][operation] = (
            cls._metrics['total_time'][operation] / cls._metrics['api_calls'][operation]
        )
        
        # 如果耗时超过1秒，打印警告
        if duration > 1.0:
            print(f"⚠️ 慢操作警告: {operation} 耗时 {duration:.2f}秒")
        else:
            print(f"⏱️ {operation} 耗时: {duration:.2f}秒")
    
    @classmethod
    def get_stats(cls):
        """获取性能统计"""
        stats = {}
        for operation in cls._metrics['api_calls'].keys():
            stats[operation] = {
                'calls': cls._metrics['api_calls'][operation],
                'avg_time': round(cls._metrics['avg_time'][operation], 3),
                'max_time': round(cls._metrics['max_time'][operation], 3),
                'min_time': round(cls._metrics['min_time'][operation], 3),
                'total_time': round(cls._metrics['total_time'][operation], 3),
            }
        return stats
    
    @classmethod
    def reset_stats(cls):
        """重置统计数据"""
        cls._metrics = {
            'api_calls': {},
            'total_time': {},
            'avg_time': {},
            'max_time': {},
            'min_time': {},
        }


def async_timer(operation_name: str):
    """
    异步函数性能计时装饰器
    
    用法:
    @async_timer("获取邮件列表")
    async def get_mail_list(...):
        ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                PerformanceMonitor.log_timing(operation_name, duration)
        return wrapper
    return decorator


def sync_timer(operation_name: str):
    """
    同步函数性能计时装饰器
    
    用法:
    @sync_timer("数据库查询")
    def query_database(...):
        ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                PerformanceMonitor.log_timing(operation_name, duration)
        return wrapper
    return decorator

