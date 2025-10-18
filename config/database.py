"""数据库配置文件"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Generator


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


class DatabaseConnection:
    """数据库连接管理类"""
    
    def __init__(self, settings: DatabaseSettings = None):
        self.settings = settings or get_database_settings()
        self._connection = None
    
    def get_connection_params(self) -> dict:
        """获取数据库连接参数"""
        return {
            'host': self.settings.db_host,
            'port': self.settings.db_port,
            'user': self.settings.db_user,
            'password': self.settings.db_password,
            'database': self.settings.db_name,
            'charset': self.settings.db_charset,
            'cursorclass': DictCursor,
            'connect_timeout': self.settings.db_connect_timeout,
            'autocommit': False
        }
    
    def connect(self):
        """创建数据库连接"""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(**self.get_connection_params())
        return self._connection
    
    def close(self):
        """关闭数据库连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None
    
    @contextmanager
    def get_cursor(self) -> Generator:
        """获取数据库游标（上下文管理器）"""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()


def get_db_connection() -> DatabaseConnection:
    """获取数据库连接实例"""
    return DatabaseConnection()
