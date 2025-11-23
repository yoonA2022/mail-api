"""
任务执行器
负责实际执行定时任务命令，支持超时控制、重试机制、资源监控
"""

import asyncio
import subprocess
import logging
import traceback
import os
import psutil
import json
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    任务执行器
    
    特性：
    1. 异步执行命令（不阻塞）
    2. 超时控制
    3. 自动重试机制
    4. 资源使用监控（CPU、内存）
    5. 输出日志收集
    6. 环境变量隔离
    """
    
    def __init__(self):
        """初始化执行器"""
        self.running_tasks: Dict[str, asyncio.Task] = {}
        logger.info("🔧 任务执行器初始化完成")
    
    async def execute(
        self,
        task_id: int,
        execution_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_interval: int = 60
    ) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task_id: 任务ID
            execution_id: 执行ID
            command: 执行命令
            parameters: 任务参数
            working_directory: 工作目录
            environment_vars: 环境变量
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            
        Returns:
            执行结果字典
        """
        logger.info(f"🚀 执行任务: task_id={task_id}, execution_id={execution_id}")
        logger.info(f"   命令: {command}")
        
        # 构建完整命令
        full_command = self._build_command(command, parameters)
        
        # 准备环境变量
        env = self._prepare_environment(environment_vars)
        
        # 验证工作目录
        work_dir = self._validate_working_directory(working_directory)
        
        # 执行任务（带重试）
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"📝 执行尝试 {attempt + 1}/{max_retries + 1}")
                
                result = await self._execute_command(
                    command=full_command,
                    working_directory=work_dir,
                    environment=env,
                    timeout_seconds=timeout_seconds,
                    task_id=task_id,
                    execution_id=execution_id
                )
                
                # 执行成功，返回结果
                if result['success']:
                    logger.info(f"✅ 任务执行成功: task_id={task_id}")
                    return result
                
                # 执行失败，判断是否需要重试
                if attempt < max_retries:
                    logger.warning(f"⚠️ 任务执行失败，{retry_interval}秒后重试...")
                    await asyncio.sleep(retry_interval)
                    continue
                
                # 达到最大重试次数
                logger.error(f"❌ 任务执行失败，已达最大重试次数: task_id={task_id}")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"⏱️ 任务执行超时: task_id={task_id}, timeout={timeout_seconds}s")
                
                if attempt < max_retries:
                    logger.warning(f"⚠️ 超时后重试...")
                    await asyncio.sleep(retry_interval)
                    continue
                
                return {
                    'success': False,
                    'error': f'任务执行超时（{timeout_seconds}秒）',
                    'exit_code': -1,
                    'execution_id': execution_id
                }
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"❌ 任务执行异常: {error_msg}")
                logger.error(traceback.format_exc())
                
                if attempt < max_retries:
                    logger.warning(f"⚠️ 异常后重试...")
                    await asyncio.sleep(retry_interval)
                    continue
                
                return {
                    'success': False,
                    'error': error_msg,
                    'exit_code': -1,
                    'execution_id': execution_id
                }
        
        # 不应该到达这里
        return {
            'success': False,
            'error': '未知错误',
            'exit_code': -1,
            'execution_id': execution_id
        }
    
    async def _execute_command(
        self,
        command: str,
        working_directory: Optional[str],
        environment: Dict[str, str],
        timeout_seconds: int,
        task_id: int,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        执行命令（核心方法）
        
        Args:
            command: 命令字符串
            working_directory: 工作目录
            environment: 环境变量
            timeout_seconds: 超时时间
            task_id: 任务ID
            execution_id: 执行ID
            
        Returns:
            执行结果
        """
        start_time = datetime.now()
        process = None
        
        try:
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory,
                env=environment
            )
            
            # 记录进程ID
            pid = process.pid
            logger.info(f"📌 进程已启动: PID={pid}")
            
            # 启动资源监控
            monitor_task = asyncio.create_task(
                self._monitor_process(pid, task_id, execution_id)
            )
            
            # 等待进程完成（带超时）
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # 超时，杀死进程
                logger.warning(f"⏱️ 进程超时，正在终止: PID={pid}")
                process.kill()
                await process.wait()
                monitor_task.cancel()
                raise
            
            # 取消监控任务
            monitor_task.cancel()
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 解码输出
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ''
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ''
            
            # 判断执行是否成功
            exit_code = process.returncode
            success = exit_code == 0
            
            result = {
                'success': success,
                'exit_code': exit_code,
                'output': stdout_text,
                'error': stderr_text,
                'duration_ms': duration_ms,
                'pid': pid,
                'execution_id': execution_id
            }
            
            if success:
                logger.info(f"✅ 命令执行成功: exit_code={exit_code}, duration={duration_ms}ms")
                if stdout_text:
                    logger.info(f"   标准输出: {stdout_text[:1000]}")
            else:
                logger.error(f"❌ 命令执行失败: exit_code={exit_code}")
                if stderr_text:
                    logger.error(f"   错误输出: {stderr_text[:2000]}")
                if stdout_text:
                    logger.error(f"   标准输出: {stdout_text[:2000]}")
            
            return result
            
        except Exception as e:
            # 确保进程被清理
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
            
            raise
    
    async def _monitor_process(self, pid: int, task_id: int, execution_id: str):
        """
        监控进程资源使用
        
        Args:
            pid: 进程ID
            task_id: 任务ID
            execution_id: 执行ID
        """
        try:
            process = psutil.Process(pid)
            
            while True:
                try:
                    # 获取CPU和内存使用率
                    cpu_percent = process.cpu_percent(interval=1)
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    logger.debug(
                        f"📊 进程资源: PID={pid}, "
                        f"CPU={cpu_percent:.1f}%, "
                        f"内存={memory_mb:.1f}MB"
                    )
                    
                    # 检查资源使用是否过高
                    if cpu_percent > 90:
                        logger.warning(f"⚠️ CPU使用率过高: {cpu_percent:.1f}%")
                    
                    if memory_mb > 1024:  # 超过1GB
                        logger.warning(f"⚠️ 内存使用过高: {memory_mb:.1f}MB")
                    
                    await asyncio.sleep(5)  # 每5秒监控一次
                    
                except psutil.NoSuchProcess:
                    # 进程已结束
                    break
                    
        except asyncio.CancelledError:
            # 监控被取消
            pass
        except Exception as e:
            logger.error(f"❌ 进程监控异常: {str(e)}")
    
    def _build_command(self, command: str, parameters: Optional[Dict[str, Any]]) -> str:
        """
        构建完整命令
        
        Args:
            command: 基础命令
            parameters: 参数字典
            
        Returns:
            完整命令字符串
        """
        if not parameters:
            return command
        
        # 将参数转换为命令行参数
        param_parts = []
        for key, value in parameters.items():
            if isinstance(value, bool):
                if value:
                    param_parts.append(f"--{key}")
            elif isinstance(value, (list, dict)):
                # JSON格式参数
                json_value = json.dumps(value)
                param_parts.append(f'--{key}=\'{json_value}\'')
            else:
                param_parts.append(f"--{key}={value}")
        
        if param_parts:
            return f"{command} {' '.join(param_parts)}"
        
        return command
    
    def _prepare_environment(self, environment_vars: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        准备环境变量
        
        Args:
            environment_vars: 自定义环境变量
            
        Returns:
            完整的环境变量字典
        """
        # 复制当前环境变量
        env = os.environ.copy()
        
        # 设置 UTF-8 编码，解决 Windows 控制台 emoji 显示问题
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 添加自定义环境变量
        if environment_vars:
            env.update(environment_vars)
        
        # 添加任务执行标识
        env['CRON_TASK_EXECUTION'] = 'true'
        
        return env
    
    def _validate_working_directory(self, working_directory: Optional[str]) -> Optional[str]:
        """
        验证工作目录
        
        Args:
            working_directory: 工作目录路径
            
        Returns:
            验证后的工作目录路径
        """
        if not working_directory:
            return None
        
        path = Path(working_directory)
        
        # 检查目录是否存在
        if not path.exists():
            logger.warning(f"⚠️ 工作目录不存在: {working_directory}")
            return None
        
        # 检查是否为目录
        if not path.is_dir():
            logger.warning(f"⚠️ 工作目录不是有效目录: {working_directory}")
            return None
        
        return str(path.absolute())
    
    def cancel_task(self, execution_id: str) -> bool:
        """
        取消正在执行的任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功取消
        """
        task = self.running_tasks.get(execution_id)
        if not task:
            logger.warning(f"⚠️ 任务不存在或已完成: execution_id={execution_id}")
            return False
        
        try:
            task.cancel()
            del self.running_tasks[execution_id]
            logger.info(f"✅ 任务已取消: execution_id={execution_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 取消任务失败: {str(e)}")
            return False
    
    def get_running_tasks(self) -> list:
        """
        获取正在运行的任务列表
        
        Returns:
            执行ID列表
        """
        return list(self.running_tasks.keys())
