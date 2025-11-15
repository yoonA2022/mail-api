"""
定时任务服务层
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException
from config.database import DatabaseConnection
from models.cron.cron_task import (
    CronTask, CronTaskCreate, CronTaskUpdate, CronTaskOverview, 
    CronTaskLog, CronTaskListResponse, CronTaskStatsResponse,
    TaskStatus, ExecutionStatus
)


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
        # TODO: 实现获取单个任务详情
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
    def create_task(self, task_data: CronTaskCreate, created_by: int) -> CronTask:
        """创建定时任务"""
        # TODO: 实现创建任务
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
    def update_task(self, task_id: int, task_data: CronTaskUpdate, updated_by: int) -> Optional[CronTask]:
        """更新定时任务"""
        # TODO: 实现更新任务
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
    def delete_task(self, task_id: int) -> bool:
        """删除定时任务（软删除）"""
        # TODO: 实现删除任务
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
    def toggle_task_status(self, task_id: int, enabled: bool) -> Optional[CronTask]:
        """切换任务状态"""
        # TODO: 实现切换任务状态
        raise HTTPException(status_code=501, detail="功能暂未实现")
    
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
