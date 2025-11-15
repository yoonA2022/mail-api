"""数据库配置文件"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Generator
from dbutils.pooled_db import PooledDB


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    
    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "mail_system"
    db_user: str = "root"
    db_password: str = "your_password"
    db_pool_size: int = 10
    db_connect_timeout: int = 10
    db_charset: str = "utf8mb4"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_database_settings() -> DatabaseSettings:
    """获取数据库配置单例"""
    return DatabaseSettings()


# 全局连接池（单例）
_connection_pool = None


def get_connection_pool() -> PooledDB:
    """获取数据库连接池单例"""
    global _connection_pool
    
    if _connection_pool is None:
        settings = get_database_settings()
        _connection_pool = PooledDB(
            creator=pymysql,
            maxconnections=20,  # 最大连接数
            mincached=2,        # 最小空闲连接数
            maxcached=10,       # 最大空闲连接数
            maxshared=0,        # 最大共享连接数（0表示不共享）
            blocking=True,      # 连接池满时是否阻塞等待
            maxusage=None,      # 单个连接最大使用次数（None表示无限制）
            setsession=[],      # 连接前执行的SQL命令
            ping=1,             # 检查连接是否可用（1=默认检查）
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset=settings.db_charset,
            cursorclass=DictCursor,
            autocommit=False
        )
        print(f"✅ 数据库连接池已创建: 最大连接数={20}, 最小空闲={2}")
    
    return _connection_pool


class DatabaseConnection:
    """数据库连接管理类（使用连接池）"""
    
    def __init__(self):
        self.pool = get_connection_pool()
    
    @contextmanager
    def get_cursor(self) -> Generator:
        """获取数据库游标（上下文管理器，从连接池获取连接）"""
        # 从连接池获取连接
        connection = self.pool.connection()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            # 连接自动归还到连接池
            connection.close()


def get_db_connection() -> DatabaseConnection:
    """获取数据库连接实例"""
    return DatabaseConnection()


def get_db():
    """FastAPI 依赖函数：获取数据库连接"""
    db_connection = get_db_connection()
    try:
        yield db_connection
    finally:
        # 连接会在上下文管理器中自动关闭
        pass
