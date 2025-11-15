"""
定时任务API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from config.database import get_db, DatabaseConnection
from models.cron.cron_task import (
    CronTask, CronTaskCreate, CronTaskUpdate, CronTaskListResponse, 
    CronTaskStatsResponse, TaskStatus
)
from services.cron.cron_task_service import CronTaskService


router = APIRouter(prefix="/api/admin/cron", tags=["定时任务管理"])


def get_cron_service(db: DatabaseConnection = Depends(get_db)) -> CronTaskService:
    """获取定时任务服务实例"""
    return CronTaskService(db)


@router.get("/tasks", response_model=CronTaskListResponse)
async def get_cron_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="任务状态筛选"),
    task_type: Optional[str] = Query(None, description="任务类型筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    service: CronTaskService = Depends(get_cron_service)
):
    """
    获取定时任务列表
    
    支持分页、筛选、搜索和排序功能
    """
    try:
        return service.get_tasks(
            page=page,
            page_size=page_size,
            status=status,
            task_type=task_type,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取定时任务列表失败: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=CronTask)
async def get_cron_task(
    task_id: int,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    根据ID获取定时任务详情
    """
    task = service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    return task


@router.post("/tasks", response_model=CronTask)
async def create_cron_task(
    task_data: CronTaskCreate,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    创建新的定时任务
    """
    try:
        # TODO: 从认证中获取当前用户ID
        created_by = 1  # 临时使用管理员ID
        
        return service.create_task(task_data, created_by)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建定时任务失败: {str(e)}"
        )


@router.put("/tasks/{task_id}", response_model=CronTask)
async def update_cron_task(
    task_id: int,
    task_data: CronTaskUpdate,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    更新定时任务
    """
    try:
        # TODO: 从认证中获取当前用户ID
        updated_by = 1  # 临时使用管理员ID
        
        task = service.update_task(task_id, task_data, updated_by)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新定时任务失败: {str(e)}"
        )


@router.delete("/tasks/{task_id}")
async def delete_cron_task(
    task_id: int,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    删除定时任务
    """
    try:
        success = service.delete_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        return {"message": "定时任务删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除定时任务失败: {str(e)}"
        )


@router.patch("/tasks/{task_id}/toggle", response_model=CronTask)
async def toggle_cron_task_status(
    task_id: int,
    enabled: bool = Query(..., description="是否启用任务"),
    service: CronTaskService = Depends(get_cron_service)
):
    """
    切换定时任务启用/禁用状态
    """
    try:
        task = service.toggle_task_status(task_id, enabled)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换任务状态失败: {str(e)}"
        )


@router.post("/tasks/{task_id}/run")
async def run_cron_task_now(
    task_id: int,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    立即执行定时任务
    """
    try:
        # 检查任务是否存在
        task = service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        # TODO: 实现立即执行逻辑
        # 这里应该调用任务调度器来立即执行任务
        
        return {"message": f"任务 '{task.name}' 已加入执行队列"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行任务失败: {str(e)}"
        )


@router.get("/tasks/{task_id}/logs")
async def get_cron_task_logs(
    task_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="执行状态筛选"),
    service: CronTaskService = Depends(get_cron_service)
):
    """
    获取定时任务执行日志
    """
    try:
        # 检查任务是否存在
        task = service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        return service.get_task_logs(
            task_id=task_id,
            page=page,
            page_size=page_size,
            status=status
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务日志失败: {str(e)}"
        )


@router.get("/stats", response_model=CronTaskStatsResponse)
async def get_cron_task_stats(
    service: CronTaskService = Depends(get_cron_service)
):
    """
    获取定时任务统计信息
    """
    try:
        return service.get_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )
