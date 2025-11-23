"""
定时任务工具函数
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from croniter import croniter

logger = logging.getLogger(__name__)


def validate_cron_expression(cron_expression: str) -> bool:
    """
    验证 Cron 表达式是否有效
    
    Args:
        cron_expression: Cron 表达式
        
    Returns:
        是否有效
    """
    try:
        croniter(cron_expression)
        return True
    except Exception as e:
        logger.error(f"❌ 无效的 Cron 表达式: {cron_expression}, error={str(e)}")
        return False


def get_next_run_time(
    cron_expression: str,
    base_time: Optional[datetime] = None,
    timezone: str = 'Asia/Shanghai'
) -> Optional[datetime]:
    """
    计算下次执行时间
    
    Args:
        cron_expression: Cron 表达式
        base_time: 基准时间（默认为当前时间）
        timezone: 时区
        
    Returns:
        下次执行时间，如果表达式无效则返回 None
    """
    try:
        if base_time is None:
            base_time = datetime.now()
        
        cron = croniter(cron_expression, base_time)
        return cron.get_next(datetime)
    except Exception as e:
        logger.error(f"❌ 计算下次执行时间失败: {str(e)}")
        return None


def get_next_n_run_times(
    cron_expression: str,
    n: int = 5,
    base_time: Optional[datetime] = None
) -> List[datetime]:
    """
    计算接下来 N 次执行时间
    
    Args:
        cron_expression: Cron 表达式
        n: 计算次数
        base_time: 基准时间
        
    Returns:
        执行时间列表
    """
    try:
        if base_time is None:
            base_time = datetime.now()
        
        cron = croniter(cron_expression, base_time)
        return [cron.get_next(datetime) for _ in range(n)]
    except Exception as e:
        logger.error(f"❌ 计算执行时间列表失败: {str(e)}")
        return []


def parse_cron_expression(cron_expression: str) -> Dict[str, str]:
    """
    解析 Cron 表达式
    
    Args:
        cron_expression: Cron 表达式
        
    Returns:
        解析后的字段字典
    """
    try:
        parts = cron_expression.split()
        
        # 支持 5 位和 6 位格式
        if len(parts) == 5:
            return {
                'minute': parts[0],
                'hour': parts[1],
                'day': parts[2],
                'month': parts[3],
                'weekday': parts[4]
            }
        elif len(parts) == 6:
            return {
                'second': parts[0],
                'minute': parts[1],
                'hour': parts[2],
                'day': parts[3],
                'month': parts[4],
                'weekday': parts[5]
            }
        else:
            raise ValueError(f"不支持的 Cron 表达式格式: {cron_expression}")
            
    except Exception as e:
        logger.error(f"❌ 解析 Cron 表达式失败: {str(e)}")
        return {}


def describe_cron_expression(cron_expression: str) -> str:
    """
    将 Cron 表达式转换为人类可读的描述
    
    Args:
        cron_expression: Cron 表达式
        
    Returns:
        描述文本
    """
    try:
        parts = parse_cron_expression(cron_expression)
        
        if not parts:
            return "无效的 Cron 表达式"
        
        # 简单的描述生成（可以使用 croniter 或其他库来生成更详细的描述）
        descriptions = []
        
        # 秒
        if 'second' in parts and parts['second'] != '*':
            descriptions.append(f"第 {parts['second']} 秒")
        
        # 分钟
        if parts.get('minute', '*') != '*':
            descriptions.append(f"第 {parts['minute']} 分钟")
        
        # 小时
        if parts.get('hour', '*') != '*':
            descriptions.append(f"{parts['hour']} 点")
        
        # 日期
        if parts.get('day', '*') != '*':
            descriptions.append(f"每月 {parts['day']} 日")
        
        # 月份
        if parts.get('month', '*') != '*':
            descriptions.append(f"{parts['month']} 月")
        
        # 星期
        if parts.get('weekday', '*') != '*':
            weekday_map = {
                '0': '周日', '1': '周一', '2': '周二', '3': '周三',
                '4': '周四', '5': '周五', '6': '周六', '7': '周日'
            }
            weekday = parts['weekday']
            if weekday in weekday_map:
                descriptions.append(weekday_map[weekday])
        
        if descriptions:
            return ' '.join(descriptions)
        else:
            return "每秒执行"
            
    except Exception as e:
        logger.error(f"❌ 描述 Cron 表达式失败: {str(e)}")
        return "无法解析"


def get_cron_presets() -> Dict[str, str]:
    """
    获取常用的 Cron 表达式预设
    
    Returns:
        预设字典 {名称: 表达式}
    """
    return {
        '每分钟': '* * * * *',
        '每5分钟': '*/5 * * * *',
        '每10分钟': '*/10 * * * *',
        '每15分钟': '*/15 * * * *',
        '每30分钟': '*/30 * * * *',
        '每小时': '0 * * * *',
        '每2小时': '0 */2 * * *',
        '每天凌晨': '0 0 * * *',
        '每天中午': '0 12 * * *',
        '每周一': '0 0 * * 1',
        '每月1号': '0 0 1 * *',
        '工作日早上9点': '0 9 * * 1-5',
        '周末早上10点': '0 10 * * 0,6',
    }


def is_time_to_run(cron_expression: str, check_time: Optional[datetime] = None) -> bool:
    """
    检查指定时间是否应该执行任务
    
    Args:
        cron_expression: Cron 表达式
        check_time: 检查时间（默认为当前时间）
        
    Returns:
        是否应该执行
    """
    try:
        if check_time is None:
            check_time = datetime.now()
        
        # 获取上一次应该执行的时间
        cron = croniter(cron_expression, check_time)
        prev_time = cron.get_prev(datetime)
        
        # 如果上一次执行时间在1分钟内，认为应该执行
        time_diff = (check_time - prev_time).total_seconds()
        return 0 <= time_diff <= 60
        
    except Exception as e:
        logger.error(f"❌ 检查执行时间失败: {str(e)}")
        return False


def calculate_execution_interval(cron_expression: str) -> Optional[int]:
    """
    计算任务执行间隔（秒）
    
    Args:
        cron_expression: Cron 表达式
        
    Returns:
        间隔秒数，如果无法计算则返回 None
    """
    try:
        base_time = datetime.now()
        cron = croniter(cron_expression, base_time)
        
        # 获取接下来两次执行时间
        next1 = cron.get_next(datetime)
        next2 = cron.get_next(datetime)
        
        # 计算间隔
        interval = (next2 - next1).total_seconds()
        return int(interval)
        
    except Exception as e:
        logger.error(f"❌ 计算执行间隔失败: {str(e)}")
        return None


def format_duration(milliseconds: int) -> str:
    """
    格式化执行时长
    
    Args:
        milliseconds: 毫秒数
        
    Returns:
        格式化的时长字符串
    """
    if milliseconds < 1000:
        return f"{milliseconds}ms"
    
    seconds = milliseconds / 1000
    
    if seconds < 60:
        return f"{seconds:.2f}s"
    
    minutes = seconds / 60
    
    if minutes < 60:
        return f"{minutes:.2f}分钟"
    
    hours = minutes / 60
    return f"{hours:.2f}小时"


def sanitize_command(command: str) -> str:
    """
    清理和验证命令字符串（防止命令注入）
    
    Args:
        command: 原始命令
        
    Returns:
        清理后的命令
    """
    # 移除危险字符
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>']
    
    for char in dangerous_chars:
        if char in command:
            logger.warning(f"⚠️ 命令包含危险字符: {char}")
    
    # 这里可以添加更多的安全检查
    return command.strip()
