"""
定时任务调度器集成模块
用于在 FastAPI 应用中集成调度器
"""

import logging
from typing import Optional
from .scheduler_manager import CronSchedulerManager

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler_instance: Optional[CronSchedulerManager] = None


async def init_scheduler(max_workers: int = 20) -> CronSchedulerManager:
    """
    初始化并启动调度器
    
    Args:
        max_workers: 最大工作线程数
        
    Returns:
        调度器实例
    """
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        logger.warning("⚠️ 调度器已初始化")
        return _scheduler_instance
    
    try:
        print("🚀 正在初始化定时任务调度器...")
        print(f"   最大工作线程数: {max_workers}")
        
        # 获取调度器实例
        _scheduler_instance = await CronSchedulerManager.get_instance(max_workers)
        
        # 启动调度器（会自动加载数据库中的任务）
        await _scheduler_instance.start()
        
        # 获取已加载的任务数量
        task_count = len(_scheduler_instance.task_registry)
        
        if task_count > 0:
            print(f"✅ 定时任务调度器启动成功")
            print(f"📊 检测到 {task_count} 个已开启的自动任务")
            print(f"📋 已将这些任务添加到自动运行列表")
            print(f"⏰ 到达指定时间后将自动执行")
            
            # 显示每个任务的下次执行时间
            print("\n📅 任务执行计划:")
            for task_id, job_id in _scheduler_instance.task_registry.items():
                task_info = _scheduler_instance.get_task_info(task_id)
                if task_info and task_info.get('next_run_time'):
                    print(f"   • {task_info['name']}: {task_info['next_run_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"📭 未检测到已开启的自动任务")
            print(f"💡 提示: 在前端管理界面启用任务后，重启后端即可自动加载")
        
        return _scheduler_instance
        
    except Exception as e:
        logger.error(f"❌ 调度器初始化失败: {str(e)}")
        raise


async def shutdown_scheduler():
    """关闭调度器"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        logger.warning("⚠️ 调度器未初始化")
        return
    
    try:
        logger.info("⏹️ 正在关闭定时任务调度器...")
        await _scheduler_instance.stop()
        _scheduler_instance = None
        logger.info("✅ 定时任务调度器已关闭")
        
    except Exception as e:
        logger.error(f"❌ 调度器关闭失败: {str(e)}")


def get_scheduler() -> Optional[CronSchedulerManager]:
    """
    获取调度器实例
    
    Returns:
        调度器实例，如果未初始化则返回 None
    """
    return _scheduler_instance


async def reload_scheduler():
    """
    重新加载调度器（重启）
    """
    try:
        logger.info("🔄 正在重新加载调度器...")
        
        # 关闭现有调度器
        await shutdown_scheduler()
        
        # 重新初始化
        await init_scheduler()
        
        logger.info("✅ 调度器重新加载完成")
        
    except Exception as e:
        logger.error(f"❌ 调度器重新加载失败: {str(e)}")
        raise
