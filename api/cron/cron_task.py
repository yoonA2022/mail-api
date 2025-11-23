"""
定时任务API路由
"""
import logging
import traceback
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from config.database import get_db, DatabaseConnection
from models.cron.cron_task import (
    CronTask, CronTaskCreate, CronTaskUpdate, CronTaskListResponse, 
    CronTaskStatsResponse, TaskStatus
)
from services.cron.cron_task_service import CronTaskService
from services.cron.scheduler.integration import get_scheduler
from services.cron.scheduler.dynamic_task_manager import DynamicTaskManager

# 配置日志
logger = logging.getLogger(__name__)

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


@router.get("/tasks/deleted")
async def get_deleted_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: CronTaskService = Depends(get_cron_service)
):
    """
    获取已删除的任务列表（回收站）
    """
    try:
        logger.info(f"🗑️ 获取回收站任务列表: page={page}, page_size={page_size}")
        result = service.get_deleted_tasks(page=page, page_size=page_size)
        logger.info(f"✅ 回收站任务列表获取成功: 共{result['total']}条")
        return result
    except Exception as e:
        logger.error(f"❌ 获取回收站任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回收站任务失败: {str(e)}"
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
        logger.info(f"📝 开始创建定时任务: {task_data.name}")
        logger.debug(f"任务数据: {task_data.model_dump()}")
        
        # TODO: 从认证中获取当前用户ID
        created_by = 1  # 临时使用管理员ID
        
        result = service.create_task(task_data, created_by)
        logger.info(f"✅ 任务创建成功: ID={result.id}, Name={result.name}")
        return result
    except HTTPException as he:
        logger.error(f"❌ HTTP异常: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ 创建定时任务失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
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
    删除定时任务（软删除）
    """
    try:
        logger.info(f"🗑️ 请求删除任务: task_id={task_id}")
        
        # 先获取任务信息用于日志
        task = service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        # 执行删除
        success = service.delete_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        logger.info(f"✅ 任务删除成功: ID={task_id}, Name={task.name}")
        return {"message": f"定时任务 '{task.name}' 删除成功", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除定时任务失败: {str(e)}")
        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
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


@router.patch("/tasks/{task_id}/activate")
async def toggle_task_activation(
    task_id: int,
    is_active: bool,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    切换任务激活状态
    - is_active = True: 激活任务，status自动设为enabled，并添加到调度器
    - is_active = False: 取消激活，status自动设为disabled，并从调度器移除
    """
    try:
        logger.info(f"🔄 切换任务激活状态: task_id={task_id}, is_active={is_active}")
        
        # 1. 更新数据库中的激活状态
        result = service.toggle_activation(task_id, is_active)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        logger.info(f"✅ 数据库激活状态更新成功: {result.name}")
        
        # 2. 动态管理调度器中的任务
        scheduler = get_scheduler()
        if scheduler:
            task_manager = DynamicTaskManager(scheduler)
            
            if is_active:
                # 激活：添加到调度器
                logger.info(f"📥 添加任务到调度器: task_id={task_id}")
                scheduler_result = await task_manager.activate_task(task_id)
                
                if scheduler_result['success']:
                    logger.info(f"✅ 任务已添加到调度器: {scheduler_result.get('task_name')}")
                    logger.info(f"⏰ 下次执行时间: {scheduler_result.get('next_run_time')}")
                else:
                    logger.warning(f"⚠️ 添加到调度器失败: {scheduler_result.get('message')}")
            else:
                # 取消激活：从调度器移除
                logger.info(f"📤 从调度器移除任务: task_id={task_id}")
                scheduler_result = await task_manager.deactivate_task(task_id)
                
                if scheduler_result['success']:
                    logger.info(f"✅ 任务已从调度器移除")
                else:
                    logger.warning(f"⚠️ 从调度器移除失败: {scheduler_result.get('message')}")
        else:
            logger.warning("⚠️ 调度器未初始化，跳过调度器操作")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 切换激活状态失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换激活状态失败: {str(e)}"
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
        logger.info(f"▶️ 请求立即执行任务: task_id={task_id}")
        
        # 检查任务是否存在
        task = service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="定时任务不存在"
            )
        
        # 获取调度器实例
        from services.cron.scheduler.scheduler_manager import CronSchedulerManager
        scheduler = await CronSchedulerManager.get_instance()
        
        if not scheduler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="任务调度器未启动"
            )
        
        # 立即执行任务
        logger.info(f"🚀 开始执行任务: {task.name}")
        result = await scheduler.execute_task_now(
            task_id=task.id,
            command=task.command,
            parameters=task.parameters,
            working_directory=task.working_directory,
            environment_vars=task.environment_vars,
            timeout_seconds=task.timeout_seconds,
            max_retries=task.max_retries,
            retry_interval=task.retry_interval
        )
        
        if result.get('success'):
            logger.info(f"✅ 任务执行成功: {task.name}")
            return {
                "message": f"任务 '{task.name}' 执行成功",
                "success": True,
                "result": result
            }
        else:
            logger.warning(f"⚠️ 任务执行失败: {task.name}, 错误: {result.get('error')}")
            return {
                "message": f"任务 '{task.name}' 执行失败: {result.get('error')}",
                "success": False,
                "result": result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 执行任务失败: {str(e)}")
        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行任务失败: {str(e)}"
        )


@router.post("/tasks/{task_id}/restore")
async def restore_deleted_task(
    task_id: int,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    恢复已删除的任务
    """
    try:
        logger.info(f"♻️ 请求恢复任务: task_id={task_id}")
        
        task = service.restore_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在或未被删除"
            )
        
        logger.info(f"✅ 任务恢复成功: ID={task_id}, Name={task.name}")
        return {"message": f"任务 '{task.name}' 已恢复", "success": True, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 恢复任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复任务失败: {str(e)}"
        )


@router.delete("/tasks/{task_id}/permanent")
async def permanent_delete_task(
    task_id: int,
    service: CronTaskService = Depends(get_cron_service)
):
    """
    彻底删除任务（物理删除，不可恢复）
    """
    try:
        logger.info(f"💀 请求彻底删除任务: task_id={task_id}")
        
        success = service.permanent_delete_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在或未被软删除"
            )
        
        logger.info(f"✅ 任务彻底删除成功: ID={task_id}")
        return {"message": "任务已彻底删除", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 彻底删除任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"彻底删除任务失败: {str(e)}"
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
