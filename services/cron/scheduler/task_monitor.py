"""
任务监控器
负责记录任务执行状态、统计信息、日志管理
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Optional, Any
from collections import defaultdict
import uuid

from config.database import DatabaseConnection

logger = logging.getLogger(__name__)


class TaskMonitor:
    """
    任务监控器
    
    特性：
    1. 记录任务执行日志到数据库
    2. 统计任务执行情况
    3. 实时监控任务状态
    4. 性能指标收集
    """
    
    def __init__(self):
        """初始化监控器"""
        # 内存中的统计数据（用于快速查询）
        self.stats = defaultdict(lambda: {
            'total_executions': 0,
            'success_count': 0,
            'error_count': 0,
            'missed_count': 0,
            'total_duration_ms': 0,
            'avg_duration_ms': 0,
            'last_execution_time': None,
            'last_status': None
        })
        
        logger.info("📊 任务监控器初始化完成")
    
    async def record_start(self, task_id: int, execution_id: str):
        """
        记录任务开始执行
        
        Args:
            task_id: 任务ID
            execution_id: 执行ID
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                # 获取任务名称
                task_query = "SELECT name FROM cron_tasks WHERE id = %s"
                cursor.execute(task_query, (task_id,))
                task_row = cursor.fetchone()
                task_name = task_row['name'] if task_row else f"Task_{task_id}"
                
                # 插入执行日志
                insert_query = """
                    INSERT INTO cron_task_logs (
                        task_id, task_name, execution_id, status, 
                        trigger_type, started_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(
                    insert_query,
                    (task_id, task_name, execution_id, 'running', 
                     'scheduled', datetime.now())
                )
                
                logger.info(f"📝 记录任务开始: task_id={task_id}, execution_id={execution_id}")
                
        except Exception as e:
            logger.error(f"❌ 记录任务开始失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def record_finish(
        self,
        task_id: int,
        execution_id: str,
        success: bool,
        duration_ms: int,
        output: Optional[str] = None,
        error: Optional[str] = None,
        exit_code: int = 0
    ):
        """
        记录任务执行完成
        
        Args:
            task_id: 任务ID
            execution_id: 执行ID
            success: 是否成功
            duration_ms: 执行时长（毫秒）
            output: 标准输出
            error: 错误输出
            exit_code: 退出码
        """
        try:
            status = 'success' if success else 'error'
            finished_at = datetime.now()
            
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                # 更新执行日志
                update_query = """
                    UPDATE cron_task_logs SET
                        status = %s,
                        finished_at = %s,
                        duration_ms = %s,
                        exit_code = %s,
                        output = %s,
                        error_output = %s,
                        error_message = %s
                    WHERE execution_id = %s
                """
                
                cursor.execute(
                    update_query,
                    (status, finished_at, duration_ms, exit_code,
                     output, error if not success else None,
                     error if not success else None, execution_id)
                )
                
                # 更新任务统计
                if success:
                    stats_query = """
                        UPDATE cron_tasks SET
                            run_count = run_count + 1,
                            success_count = success_count + 1,
                            last_run_at = %s,
                            last_success_at = %s
                        WHERE id = %s
                    """
                    cursor.execute(stats_query, (finished_at, finished_at, task_id))
                else:
                    stats_query = """
                        UPDATE cron_tasks SET
                            run_count = run_count + 1,
                            error_count = error_count + 1,
                            last_run_at = %s,
                            last_error_at = %s
                        WHERE id = %s
                    """
                    cursor.execute(stats_query, (finished_at, finished_at, task_id))
                
                # 更新内存统计
                self._update_memory_stats(task_id, success, duration_ms)
                
                logger.info(
                    f"📝 记录任务完成: task_id={task_id}, "
                    f"status={status}, duration={duration_ms}ms"
                )
                    
        except Exception as e:
            logger.error(f"❌ 记录任务完成失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    def record_success(self, job_id: str):
        """
        记录任务执行成功（APScheduler 事件回调）
        
        Args:
            job_id: APScheduler 任务ID
        """
        logger.debug(f"✅ 任务执行成功回调: job_id={job_id}")
    
    def record_error(self, job_id: str, error: str):
        """
        记录任务执行失败（APScheduler 事件回调）
        
        Args:
            job_id: APScheduler 任务ID
            error: 错误信息
        """
        logger.debug(f"❌ 任务执行失败回调: job_id={job_id}, error={error}")
    
    def record_missed(self, job_id: str):
        """
        记录任务错过执行（APScheduler 事件回调）
        
        Args:
            job_id: APScheduler 任务ID
        """
        logger.warning(f"⚠️ 任务错过执行回调: job_id={job_id}")
        
        # 尝试从 job_id 提取 task_id
        try:
            # job_id 格式: cron_task_{task_id}_{uuid}
            parts = job_id.split('_')
            if len(parts) >= 3 and parts[0] == 'cron' and parts[1] == 'task':
                task_id = int(parts[2])
                self.stats[task_id]['missed_count'] += 1
        except Exception:
            pass
    
    def _update_memory_stats(self, task_id: int, success: bool, duration_ms: int):
        """
        更新内存中的统计数据
        
        Args:
            task_id: 任务ID
            success: 是否成功
            duration_ms: 执行时长
        """
        stats = self.stats[task_id]
        
        stats['total_executions'] += 1
        if success:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1
        
        stats['total_duration_ms'] += duration_ms
        stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['total_executions']
        stats['last_execution_time'] = datetime.now()
        stats['last_status'] = 'success' if success else 'error'
    
    def get_task_stats(self, task_id: int) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            统计信息字典
        """
        return dict(self.stats[task_id])
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取所有任务的统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_tasks': len(self.stats),
            'tasks': {task_id: dict(stats) for task_id, stats in self.stats.items()}
        }
    
    async def get_task_logs(
        self,
        task_id: int,
        limit: int = 50,
        status: Optional[str] = None
    ) -> list:
        """
        获取任务执行日志
        
        Args:
            task_id: 任务ID
            limit: 返回数量限制
            status: 状态筛选
            
        Returns:
            日志列表
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                # 构建查询
                query = """
                    SELECT id, execution_id, status, trigger_type,
                           started_at, finished_at, duration_ms,
                           exit_code, output, error_output, error_message
                    FROM cron_task_logs
                    WHERE task_id = %s
                """
                params = [task_id]
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                query += " ORDER BY started_at DESC LIMIT %s"
                params.append(limit)
                
                cursor = db.execute_query(query, tuple(params))
                rows = cursor.fetchall()
                
                # 转换为字典列表
                logs = []
                for row in rows:
                    logs.append({
                        'id': row[0],
                        'execution_id': row[1],
                        'status': row[2],
                        'trigger_type': row[3],
                        'started_at': row[4].isoformat() if row[4] else None,
                        'finished_at': row[5].isoformat() if row[5] else None,
                        'duration_ms': row[6],
                        'exit_code': row[7],
                        'output': row[8],
                        'error_output': row[9],
                        'error_message': row[10]
                    })
                
                return logs
                
        except Exception as e:
            logger.error(f"❌ 获取任务日志失败: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def record_start(self, task_id: int, execution_id: str):
        """
        记录任务开始执行
        
        Args:
            task_id: 任务ID
            execution_id: 执行ID（UUID）
        """
        try:
            # 获取任务名称
            task_name = self._get_task_name(task_id)
            
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                query = """
                    INSERT INTO cron_task_logs (
                        task_id, task_name, execution_id, status, started_at
                    ) VALUES (%s, %s, %s, 'running', NOW())
                """
                cursor.execute(query, (task_id, task_name, execution_id))
                
            logger.info(f"📝 记录任务开始: task_id={task_id}, execution_id={execution_id}")
            
                
        except Exception as e:
            logger.error(f"❌ 记录任务开始失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _get_task_name(self, task_id: int) -> str:
        """
        获取任务名称
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务名称
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                cursor.execute("SELECT name FROM cron_tasks WHERE id = %s", (task_id,))
                row = cursor.fetchone()
                return row['name'] if row else f"Task_{task_id}"
        except Exception:
            return f"Task_{task_id}"
    
    async def cleanup_old_logs(self, days: int = 30):
        """
        清理旧日志
        
        Args:
            days: 保留天数
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                query = """
                    DELETE FROM cron_task_logs
                    WHERE started_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """
                
                result = db.execute_update(query, (days,))
                logger.info(f"🗑️ 清理了 {days} 天前的日志")
                
        except Exception as e:
            logger.error(f"❌ 清理日志失败: {str(e)}")
            logger.error(traceback.format_exc())
