#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
按照SQL文件编号顺序执行，初始化数据库表结构和示例数据
"""

import pymysql
import sys
from pathlib import Path
from config.database import get_database_settings
from datetime import datetime


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self):
        self.settings = get_database_settings()
        self.sql_dir = Path(__file__).parent / "sql"
        self.connection = None
        
    def connect_without_db(self):
        """连接MySQL服务器（不指定数据库）"""
        try:
            self.connection = pymysql.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                charset=self.settings.db_charset,
                connect_timeout=self.settings.db_connect_timeout
            )
            print(f"✅ 成功连接到MySQL服务器: {self.settings.db_host}:{self.settings.db_port}")
            return True
        except Exception as e:
            print(f"❌ 连接MySQL服务器失败: {e}")
            return False
    
    def create_database(self):
        """创建数据库（如果不存在）"""
        try:
            with self.connection.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute(f"SHOW DATABASES LIKE '{self.settings.db_name}'")
                result = cursor.fetchone()
                
                if result:
                    print(f"ℹ️  数据库 '{self.settings.db_name}' 已存在")
                else:
                    # 创建数据库
                    cursor.execute(
                        f"CREATE DATABASE `{self.settings.db_name}` "
                        f"CHARACTER SET {self.settings.db_charset} "
                        f"COLLATE {self.settings.db_charset}_unicode_ci"
                    )
                    print(f"✅ 成功创建数据库: {self.settings.db_name}")
                
                # 选择数据库
                cursor.execute(f"USE `{self.settings.db_name}`")
                self.connection.commit()
                return True
        except Exception as e:
            print(f"❌ 创建数据库失败: {e}")
            return False
    
    def get_sql_files(self):
        """获取SQL文件列表（按编号排序）"""
        if not self.sql_dir.exists():
            print(f"❌ SQL目录不存在: {self.sql_dir}")
            return []
        
        # 获取所有.sql文件
        sql_files = list(self.sql_dir.glob("*.sql"))
        
        # 按文件名排序（文件名以数字开头，如 1-xxx.sql, 2-xxx.sql）
        sql_files.sort(key=lambda x: x.name)
        
        return sql_files
    
    def execute_sql_file(self, sql_file: Path):
        """执行单个SQL文件"""
        try:
            print(f"\n📄 执行SQL文件: {sql_file.name}")
            
            # 读取SQL文件内容
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 清理SQL内容：移除注释
            sql_lines = []
            for line in sql_content.split('\n'):
                # 移除单行注释
                line = line.strip()
                if line.startswith('--') or not line:
                    continue
                sql_lines.append(line)
            
            # 重新组合SQL内容
            cleaned_sql = ' '.join(sql_lines)
            
            # 分割SQL语句（按分号分割）
            sql_statements = [stmt.strip() for stmt in cleaned_sql.split(';') if stmt.strip()]
            
            print(f"   📝 共找到 {len(sql_statements)} 条SQL语句")
            
            with self.connection.cursor() as cursor:
                for i, statement in enumerate(sql_statements, 1):
                    if not statement:
                        continue
                    
                    try:
                        cursor.execute(statement)
                        # 如果是INSERT语句，显示影响的行数
                        if statement.upper().startswith('INSERT'):
                            print(f"   ✓ 插入数据成功 (影响 {cursor.rowcount} 行)")
                        elif statement.upper().startswith('CREATE'):
                            # 提取表名
                            table_name = self._extract_table_name(statement)
                            print(f"   ✓ 创建表成功: {table_name}")
                        else:
                            print(f"   ✓ 执行语句 {i} 成功")
                    except Exception as e:
                        # 如果是表已存在的错误，忽略
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            print(f"   ⚠️  表已存在，跳过创建")
                        else:
                            print(f"   ❌ 执行语句 {i} 失败: {e}")
                            print(f"   语句: {statement[:200]}...")
                            # 不要因为一个语句失败就停止，继续执行
                
                self.connection.commit()
            
            print(f"✅ 文件 {sql_file.name} 执行完成")
            return True
            
        except Exception as e:
            print(f"❌ 执行SQL文件失败 {sql_file.name}: {e}")
            self.connection.rollback()
            return False
    
    def _extract_table_name(self, sql: str) -> str:
        """从CREATE TABLE语句中提取表名"""
        try:
            # 简单的表名提取
            sql_upper = sql.upper()
            if 'CREATE TABLE' in sql_upper:
                start = sql_upper.find('TABLE') + 5
                end = sql.find('(', start)
                table_name = sql[start:end].strip()
                # 移除IF NOT EXISTS
                table_name = table_name.replace('IF NOT EXISTS', '').strip()
                # 移除反引号
                table_name = table_name.replace('`', '').strip()
                return table_name
        except:
            pass
        return "unknown"
    
    def initialize(self):
        """执行完整的数据库初始化流程"""
        print("\n" + "="*70)
        print("🚀 开始初始化数据库")
        print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        try:
            # 1. 连接MySQL服务器
            if not self.connect_without_db():
                return False
            
            # 2. 创建数据库
            if not self.create_database():
                return False
            
            # 3. 获取SQL文件列表
            sql_files = self.get_sql_files()
            if not sql_files:
                print("⚠️  没有找到SQL文件")
                return False
            
            print(f"\n📋 找到 {len(sql_files)} 个SQL文件，按顺序执行:")
            for sql_file in sql_files:
                print(f"   - {sql_file.name}")
            
            # 4. 按顺序执行SQL文件
            success_count = 0
            for sql_file in sql_files:
                if self.execute_sql_file(sql_file):
                    success_count += 1
            
            # 5. 显示结果
            print("\n" + "="*70)
            print(f"✅ 数据库初始化完成！")
            print(f"📊 成功执行: {success_count}/{len(sql_files)} 个SQL文件")
            print(f"🗄️  数据库名称: {self.settings.db_name}")
            print(f"🌐 数据库地址: {self.settings.db_host}:{self.settings.db_port}")
            print("="*70 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ 初始化过程出错: {e}")
            return False
        
        finally:
            # 关闭连接
            if self.connection:
                self.connection.close()
                print("🔌 数据库连接已关闭")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("📦 MySQL 数据库初始化工具")
    print("="*70)
    
    # 检查配置
    settings = get_database_settings()
    print(f"\n📋 当前配置:")
    print(f"   数据库主机: {settings.db_host}:{settings.db_port}")
    print(f"   数据库名称: {settings.db_name}")
    print(f"   数据库用户: {settings.db_user}")
    print(f"   字符集: {settings.db_charset}")
    
    # 确认执行
    print("\n⚠️  注意: 此操作将创建数据库并执行SQL文件")
    confirm = input("是否继续? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 操作已取消")
        return
    
    # 执行初始化
    initializer = DatabaseInitializer()
    success = initializer.initialize()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
