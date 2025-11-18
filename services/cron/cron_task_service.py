"""
定时任务服务层
"""
import json
import logging
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException
from config.database import DatabaseConnection
from models.cron.cron_task import (
    CronTask, CronTaskCreate, CronTaskUpdate, CronTaskOverview, 
    CronTaskLog, CronTaskListResponse, CronTaskStatsResponse,
    TaskStatus, ExecutionStatus
)

# 配置日志
logger = logging.getLogger(__name__)


class CronTaskService:
    """定时任务服务类"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def get_tasks(
        self, 
        page: int = 1, 
        page_size: int = 10,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> CronTaskListResponse:
        """获取定时任务列表"""
        
        # 构建查询条件
        where_conditions = ["t.deleted_at IS NULL"]
        params = []
        
        if status:
            where_conditions.append("t.status = %s")
            params.append(status)
            
        if task_type:
            where_conditions.append("t.type = %s")
            params.append(task_type)
            
        if search:
            where_conditions.append("(t.name LIKE %s OR t.description LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_clause = " AND ".join(where_conditions)
        
        # 排序
        order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        order_clause = f"t.{sort_by} {order_direction}"
        
        # 分页
        offset = (page - 1) * page_size
        
        # 查询总数
        count_sql = f"""
        SELECT COUNT(*) as total
        FROM cron_tasks t
        WHERE {where_clause}
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(count_sql, params)
            count_result = cursor.fetchone()
            total = count_result['total'] if count_result else 0
        
        # 查询数据
        query_sql = f"""
        SELECT 
            t.id,
            t.name,
            t.description,
            t.type,
            t.cron_expression,
            t.status,
            t.is_active,
            t.run_count,
            t.success_count,
            t.error_count,
            CASE 
                WHEN t.run_count > 0 THEN ROUND((t.success_count / t.run_count) * 100, 2)
                ELSE 0
            END AS success_rate_percent,
            t.last_run_at,
            t.last_success_at,
            t.last_error_at,
            t.next_run_at,
            t.priority,
            t.created_at,
            a.username AS created_by_username,
            (SELECT l.status FROM cron_task_logs l WHERE l.task_id = t.id ORDER BY l.started_at DESC LIMIT 1) AS last_execution_status,
            (SELECT l.duration_ms FROM cron_task_logs l WHERE l.task_id = t.id ORDER BY l.started_at DESC LIMIT 1) AS last_execution_duration_ms
        FROM cron_tasks t
        LEFT JOIN admins a ON t.created_by = a.id
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
        """
        
        # 添加分页参数
        query_params = params + [page_size, offset]
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query_sql, query_params)
            results = cursor.fetchall()
        
        # 转换为模型
        tasks = []
        for row in results:
            task_data = {
                "id": row['id'],
                "name": row['name'],
                "description": row['description'],
                "type": row['type'],
                "cron_expression": row['cron_expression'],
                "status": row['status'],
                "is_active": bool(row['is_active']),
                "run_count": row['run_count'],
                "success_count": row['success_count'],
                "error_count": row['error_count'],
                "success_rate_percent": float(row['success_rate_percent'] or 0),
                "last_run_at": row['last_run_at'],
                "last_success_at": row['last_success_at'],
                "last_error_at": row['last_error_at'],
                "next_run_at": row['next_run_at'],
                "priority": row['priority'],
                "created_at": row['created_at'],
                "created_by_username": row['created_by_username'],
                "last_execution_status": row['last_execution_status'],
                "last_execution_duration_ms": row['last_execution_duration_ms']
            }
            tasks.append(CronTaskOverview(**task_data))
        
        total_pages = (total + page_size - 1) // page_size
        
        return CronTaskListResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def get_task_by_id(self, task_id: int) -> Optional[CronTask]:
        """根据ID获取定时任务"""
        try:
            logger.info(f"🔍 查询任务ID: {task_id}")
            
            query_sql = """
            SELECT 
                id, name, description, type, cron_expression, timezone,
                command, parameters, working_directory, environment_vars,
                status, is_active, run_count, success_count, error_count,
                last_run_at, last_success_at, last_error_at, next_run_at,
                timeout_seconds, max_retries, retry_interval,
                notify_on_success, notify_on_failure, notification_emails,
                created_by, updated_by, priority, tags, remark,
                created_at, updated_at, deleted_at
            FROM cron_tasks
            WHERE id = %s AND deleted_at IS NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query_sql, (task_id,))
                row = cursor.fetchone()
            
            if not row:
                logger.warning(f"⚠️ 任务不存在: ID={task_id}")
                return None
            
            # 解析JSON字段
            task_data = dict(row)
            if task_data.get('parameters'):
                task_data['parameters'] = json.loads(task_data['parameters'])
            if task_data.get('environment_vars'):
                task_data['environment_vars'] = json.loads(task_data['environment_vars'])
            if task_data.get('notification_emails'):
                task_data['notification_emails'] = json.loads(task_data['notification_emails'])
            if task_data.get('tags'):
                task_data['tags'] = json.loads(task_data['tags'])
            
            logger.info(f"✅ 任务查询成功: {task_data['name']}")
            return CronTask(**task_data)
            
        except Exception as e:
            logger.error(f"❌ 查询任务失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def create_task(self, task_data: CronTaskCreate, created_by: int) -> CronTask:
        """创建定时任务"""
        try:
            logger.info(f"📝 开始创建任务: {task_data.name}")
            logger.debug(f"任务数据: {task_data.model_dump()}")
            
            # 准备JSON字段
            parameters_json = json.dumps(task_data.parameters) if task_data.parameters else None
            environment_vars_json = json.dumps(task_data.environment_vars) if task_data.environment_vars else None
            notification_emails_json = json.dumps(task_data.notification_emails) if task_data.notification_emails else None
            tags_json = json.dumps(task_data.tags) if task_data.tags else None
            
            logger.debug(f"JSON字段准备完成")
            
            # 根据is_active自动设置status
            # is_active = 0 (未激活) → status = 'disabled' (草稿状态)
            # is_active = 1 (已激活) → status = 'enabled' (正式启用)
            initial_status = TaskStatus.ENABLED.value if task_data.is_active else TaskStatus.DISABLED.value
            logger.debug(f"is_active={task_data.is_active}, 自动设置status={initial_status}")
            
            insert_sql = """
            INSERT INTO cron_tasks (
                name, description, type, cron_expression, timezone,
                command, parameters, working_directory, environment_vars,
                status, is_active, timeout_seconds, max_retries, retry_interval,
                notify_on_success, notify_on_failure, notification_emails,
                created_by, updated_by, priority, tags, remark,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                NOW(), NOW()
            )
            """
            
            params = (
                task_data.name,
                task_data.description,
                task_data.type.value,
                task_data.cron_expression,
                task_data.timezone,
                task_data.command,
                parameters_json,
                task_data.working_directory,
                environment_vars_json,
                initial_status,  # 根据is_active自动设置
                task_data.is_active,  # 使用前端传入的激活状态
                task_data.timeout_seconds,
                task_data.max_retries,
                task_data.retry_interval,
                task_data.notify_on_success,
                task_data.notify_on_failure,
                notification_emails_json,
                created_by,
                created_by,
                task_data.priority,
                tags_json,
                task_data.remark
            )
            
            logger.debug(f"执行SQL插入...")
            
            with self.db.get_cursor() as cursor:
                cursor.execute(insert_sql, params)
                task_id = cursor.lastrowid
                # 上下文管理器会自动commit
            
            logger.info(f"✅ 任务插入成功: ID={task_id}")
            
            # 查询并返回创建的任务
            created_task = self.get_task_by_id(task_id)
            if not created_task:
                raise Exception("任务创建后查询失败")
            
            logger.info(f"🎉 任务创建完成: ID={task_id}, Name={created_task.name}")
            return created_task
            
        except Exception as e:
            logger.error(f"❌ 创建任务失败: {str(e)}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            # 上下文管理器会自动rollback
            raise
    
    def update_task(self, task_id: int, task_data: CronTaskUpdate, updated_by: int) -> Optional[CronTask]:
        """更新定时任务"""
        try:
            logger.info(f"📝 开始更新任务: task_id={task_id}")
            logger.debug(f"更新数据: {task_data.model_dump(exclude_unset=True)}")
            
            # 检查任务是否存在
            existing_task = self.get_task_by_id(task_id)
            if not existing_task:
                logger.warning(f"⚠️ 任务不存在: ID={task_id}")
                return None
            
            # 构建动态更新SQL
            update_fields = []
            params = []
            
            # 只更新提供的字段
            if task_data.name is not None:
                update_fields.append("name = %s")
                params.append(task_data.name)
            
            if task_data.description is not None:
                update_fields.append("description = %s")
                params.append(task_data.description)
            
            if task_data.type is not None:
                update_fields.append("type = %s")
                params.append(task_data.type.value)
            
            if task_data.cron_expression is not None:
                update_fields.append("cron_expression = %s")
                params.append(task_data.cron_expression)
            
            if task_data.timezone is not None:
                update_fields.append("timezone = %s")
                params.append(task_data.timezone)
            
            if task_data.command is not None:
                update_fields.append("command = %s")
                params.append(task_data.command)
            
            if task_data.parameters is not None:
                update_fields.append("parameters = %s")
                params.append(json.dumps(task_data.parameters))
            
            if task_data.working_directory is not None:
                update_fields.append("working_directory = %s")
                params.append(task_data.working_directory)
            
            if task_data.environment_vars is not None:
                update_fields.append("environment_vars = %s")
                params.append(json.dumps(task_data.environment_vars))
            
            if task_data.status is not None:
                update_fields.append("status = %s")
                params.append(task_data.status.value)
            
            if task_data.is_active is not None:
                update_fields.append("is_active = %s")
                params.append(task_data.is_active)
                # 如果更新is_active，同时更新status
                if task_data.status is None:  # 只在status未被明确设置时自动更新
                    new_status = TaskStatus.ENABLED.value if task_data.is_active else TaskStatus.DISABLED.value
                    update_fields.append("status = %s")
                    params.append(new_status)
            
            if task_data.timeout_seconds is not None:
                update_fields.append("timeout_seconds = %s")
                params.append(task_data.timeout_seconds)
            
            if task_data.max_retries is not None:
                update_fields.append("max_retries = %s")
                params.append(task_data.max_retries)
            
            if task_data.retry_interval is not None:
                update_fields.append("retry_interval = %s")
                params.append(task_data.retry_interval)
            
            if task_data.notify_on_success is not None:
                update_fields.append("notify_on_success = %s")
                params.append(task_data.notify_on_success)
            
            if task_data.notify_on_failure is not None:
                update_fields.append("notify_on_failure = %s")
                params.append(task_data.notify_on_failure)
            
            if task_data.notification_emails is not None:
                update_fields.append("notification_emails = %s")
                params.append(json.dumps(task_data.notification_emails))
            
            if task_data.priority is not None:
                update_fields.append("priority = %s")
                params.append(task_data.priority)
            
            if task_data.tags is not None:
                update_fields.append("tags = %s")
                params.append(json.dumps(task_data.tags))
            
            if task_data.remark is not None:
                update_fields.append("remark = %s")
                params.append(task_data.remark)
            
            # 总是更新updated_by和updated_at
            update_fields.append("updated_by = %s")
            params.append(updated_by)
            update_fields.append("updated_at = NOW()")
            
            # 如果没有要更新的字段，直接返回原任务
            if len(update_fields) <= 2:  # 只有updated_by和updated_at
                logger.info(f"⚠️ 没有需要更新的字段")
                return existing_task
            
            # 构建并执行更新SQL
            update_sql = f"""
            UPDATE cron_tasks
            SET {', '.join(update_fields)}
            WHERE id = %s AND deleted_at IS NULL
            """
            params.append(task_id)
            
            logger.debug(f"执行SQL更新...")
            
            with self.db.get_cursor() as cursor:
                cursor.execute(update_sql, params)
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 更新失败，任务可能不存在: ID={task_id}")
                return None
            
            logger.info(f"✅ 任务更新成功: ID={task_id}")
            
            # 查询并返回更新后的任务
            updated_task = self.get_task_by_id(task_id)
            if updated_task:
                logger.info(f"🎉 任务更新完成: ID={task_id}, Name={updated_task.name}")
            
            return updated_task
            
        except Exception as e:
            logger.error(f"❌ 更新任务失败: {str(e)}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def delete_task(self, task_id: int) -> bool:
        """删除定时任务（软删除）"""
        try:
            logger.info(f"🗑️ 删除任务: task_id={task_id}")
            
            # 软删除：设置deleted_at时间戳
            delete_sql = """
            UPDATE cron_tasks
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(delete_sql, (task_id,))
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 任务不存在或已删除: ID={task_id}")
                return False
            
            logger.info(f"✅ 任务删除成功: ID={task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除任务失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def toggle_activation(self, task_id: int, is_active: bool) -> Optional[CronTask]:
        """
        切换任务激活状态
        - is_active = True: 激活任务，status自动设为enabled
        - is_active = False: 取消激活，status自动设为disabled（草稿状态）
        """
        try:
            logger.info(f"🔄 切换任务激活状态: task_id={task_id}, is_active={is_active}")
            
            # 根据is_active自动设置status
            new_status = TaskStatus.ENABLED.value if is_active else TaskStatus.DISABLED.value
            
            update_sql = """
            UPDATE cron_tasks
            SET is_active = %s, status = %s, updated_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(update_sql, (is_active, new_status, task_id))
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 任务不存在或已删除: ID={task_id}")
                return None
            
            logger.info(f"✅ 激活状态切换成功: is_active={is_active}, status={new_status}")
            
            # 返回更新后的任务
            return self.get_task_by_id(task_id)
            
        except Exception as e:
            logger.error(f"❌ 切换激活状态失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def toggle_task_status(self, task_id: int, enabled: bool) -> Optional[CronTask]:
        """
        切换任务运行状态（仅切换status，不影响is_active）
        - enabled = True: status设为enabled
        - enabled = False: status设为disabled
        注意：只有is_active=1的任务才能被调度执行
        """
        try:
            logger.info(f"🔄 切换任务运行状态: task_id={task_id}, enabled={enabled}")
            
            new_status = TaskStatus.ENABLED.value if enabled else TaskStatus.DISABLED.value
            
            update_sql = """
            UPDATE cron_tasks
            SET status = %s, updated_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(update_sql, (new_status, task_id))
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 任务不存在或已删除: ID={task_id}")
                return None
            
            logger.info(f"✅ 运行状态切换成功: status={new_status}")
            
            # 返回更新后的任务
            return self.get_task_by_id(task_id)
            
        except Exception as e:
            logger.error(f"❌ 切换运行状态失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def get_deleted_tasks(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取已删除的任务列表（回收站）"""
        try:
            logger.info(f"🗑️ 获取已删除任务列表: page={page}, page_size={page_size}")
            
            offset = (page - 1) * page_size
            
            # 查询已删除的任务
            query_sql = """
            SELECT * FROM cron_tasks
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            LIMIT %s OFFSET %s
            """
            
            # 统计总数
            count_sql = """
            SELECT COUNT(*) as total FROM cron_tasks
            WHERE deleted_at IS NOT NULL
            """
            
            with self.db.get_cursor() as cursor:
                # 获取任务列表
                cursor.execute(query_sql, (page_size, offset))
                tasks = cursor.fetchall()
                
                # 获取总数
                cursor.execute(count_sql)
                total = cursor.fetchone()['total']
            
            logger.info(f"✅ 已删除任务查询成功: 共{total}条, 当前页{len(tasks)}条")
            
            # 转换为CronTaskOverview格式
            task_list = []
            for task in tasks:
                # 计算成功率
                success_rate = 0
                if task['run_count'] > 0:
                    success_rate = (task['success_count'] / task['run_count']) * 100
                
                task_overview = {
                    'id': task['id'],
                    'name': task['name'],
                    'description': task.get('description'),
                    'type': task['type'],
                    'cron_expression': task['cron_expression'],
                    'status': task['status'],
                    'is_active': bool(task['is_active']),
                    'run_count': task['run_count'],
                    'success_count': task['success_count'],
                    'error_count': task['error_count'],
                    'success_rate_percent': round(success_rate, 2),
                    'last_run_at': task.get('last_run_at'),
                    'last_success_at': task.get('last_success_at'),
                    'last_error_at': task.get('last_error_at'),
                    'next_run_at': task.get('next_run_at'),
                    'priority': task['priority'],
                    'created_at': task['created_at'],
                    'deleted_at': task.get('deleted_at')
                }
                task_list.append(task_overview)
            
            return {
                "tasks": task_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"❌ 获取已删除任务失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def restore_task(self, task_id: int) -> Optional[CronTask]:
        """恢复已删除的任务"""
        try:
            logger.info(f"♻️ 恢复任务: task_id={task_id}")
            
            # 恢复任务：清除deleted_at
            restore_sql = """
            UPDATE cron_tasks
            SET deleted_at = NULL, updated_at = NOW()
            WHERE id = %s AND deleted_at IS NOT NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(restore_sql, (task_id,))
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 任务不存在或未被删除: ID={task_id}")
                return None
            
            logger.info(f"✅ 任务恢复成功: ID={task_id}")
            
            # 返回恢复后的任务
            return self.get_task_by_id(task_id)
            
        except Exception as e:
            logger.error(f"❌ 恢复任务失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def permanent_delete_task(self, task_id: int) -> bool:
        """彻底删除任务（物理删除）"""
        try:
            logger.info(f"💀 彻底删除任务: task_id={task_id}")
            
            # 物理删除：从数据库中移除记录
            delete_sql = """
            DELETE FROM cron_tasks
            WHERE id = %s AND deleted_at IS NOT NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(delete_sql, (task_id,))
                affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"⚠️ 任务不存在或未被软删除: ID={task_id}")
                return False
            
            logger.info(f"✅ 任务彻底删除成功: ID={task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 彻底删除任务失败: {str(e)}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise
    
    def get_task_logs(
        self, 
        task_id: int, 
        page: int = 1, 
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务执行日志"""
        # TODO: 实现获取任务日志
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
    def get_stats(self) -> CronTaskStatsResponse:
        """获取定时任务统计信息"""
        # TODO: 实现获取统计信息
        raise HTTPException(status_code=501, detail="功能暂未实现")
