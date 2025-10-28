"""
REI 订单 API 服务
调用 REI 官方接口获取订单详细信息
支持反爬虫绕过机制
"""

import httpx
import asyncio
import random
from typing import Dict, Any, Optional
from datetime import datetime


class ReiOrderApiService:
    """REI 订单 API 服务类"""
    
    # 常用浏览器 User-Agent 列表
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    def __init__(self, timeout: int = 30):
        """
        初始化
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.cookies = httpx.Cookies()
    
    def _get_browser_headers(self) -> Dict[str, str]:
        """
        生成浏览器级别的请求头（绕过反爬虫）
        
        Returns:
            完整的请求头字典
        """
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.rei.com/'
        }
        return headers
    
    async def fetch_order_details(
        self,
        order_number: str,
        last_name: str,
        zip_code: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        调用 REI API 获取订单详细信息
        
        Args:
            order_number: 订单号（如 A385893454）
            last_name: 用户姓氏（如 Branson）
            zip_code: 邮政编码（如 94577）
            max_retries: 最大重试次数
            
        Returns:
            {
                'success': True,
                'order_data': {...},  # REI API 返回的完整 JSON 数据
                'status_code': 200,
                'elapsed_ms': 1949.38
            }
        """
        # 构建 API URL
        url = f"https://www.rei.com/order-details/rs/purchase-details/tracking/{order_number}"
        params = {
            'lastName': last_name,
            'zipCode': zip_code
        }
        
        print(f"📡 调用 REI API: {order_number}")
        print(f"   参数: lastName={last_name}, zipCode={zip_code}")
        
        # 重试逻辑
        for attempt in range(max_retries):
            try:
                # 创建客户端配置
                client_config = {
                    'timeout': self.timeout,
                    'follow_redirects': True,
                    'cookies': self.cookies,
                    'http2': True,  # 启用 HTTP/2
                }
                
                async with httpx.AsyncClient(**client_config) as client:
                    # 添加随机延迟（模拟人类行为）
                    if attempt > 0:
                        delay = random.uniform(1, 3)
                        print(f"   ⏳ 重试 {attempt + 1}/{max_retries}，延迟 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    
                    # 发送请求
                    response = await client.get(
                        url=url,
                        params=params,
                        headers=self._get_browser_headers()
                    )
                    
                    # 更新 cookies
                    self.cookies.update(response.cookies)
                    
                    # 检查状态码
                    if response.status_code == 200:
                        try:
                            order_data = response.json()
                            elapsed_ms = response.elapsed.total_seconds() * 1000
                            
                            print(f"   ✅ 成功获取订单数据 (耗时: {elapsed_ms:.2f}ms)")
                            
                            return {
                                'success': True,
                                'order_data': order_data,
                                'status_code': 200,
                                'elapsed_ms': elapsed_ms,
                                'attempt': attempt + 1
                            }
                        except Exception as e:
                            print(f"   ❌ JSON 解析失败: {e}")
                            return {
                                'success': False,
                                'error': f'JSON 解析失败: {str(e)}',
                                'error_type': 'json_parse_error',
                                'status_code': response.status_code,
                                'attempt': attempt + 1
                            }
                    
                    elif response.status_code == 403:
                        print(f"   ⚠️ 被反爬虫拦截 (403)，尝试重试...")
                        if attempt == max_retries - 1:
                            return {
                                'success': False,
                                'error': '被反爬虫拦截，已达到最大重试次数',
                                'error_type': 'anti_bot_blocked',
                                'status_code': 403,
                                'attempt': attempt + 1
                            }
                    
                    elif response.status_code == 404:
                        print(f"   ❌ 订单不存在或参数错误 (404)")
                        return {
                            'success': False,
                            'error': '订单不存在或参数错误',
                            'error_type': 'not_found',
                            'status_code': 404,
                            'attempt': attempt + 1
                        }
                    
                    else:
                        print(f"   ❌ 请求失败，状态码: {response.status_code}")
                        if attempt == max_retries - 1:
                            return {
                                'success': False,
                                'error': f'请求失败，状态码: {response.status_code}',
                                'error_type': 'http_error',
                                'status_code': response.status_code,
                                'attempt': attempt + 1
                            }
            
            except httpx.TimeoutException:
                print(f"   ⏰ 请求超时")
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': '请求超时',
                        'error_type': 'timeout',
                        'attempt': attempt + 1
                    }
            
            except httpx.RequestError as e:
                print(f"   ❌ 请求错误: {e}")
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': f'请求错误: {str(e)}',
                        'error_type': 'request_error',
                        'attempt': attempt + 1
                    }
            
            except Exception as e:
                print(f"   ❌ 未知错误: {e}")
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': f'未知错误: {str(e)}',
                        'error_type': 'unknown',
                        'attempt': attempt + 1
                    }
        
        return {
            'success': False,
            'error': '达到最大重试次数',
            'error_type': 'max_retries_reached',
            'attempt': max_retries
        }
    
    @staticmethod
    def extract_last_name(full_name: str) -> str:
        """
        从完整姓名中提取姓氏
        
        Args:
            full_name: 完整姓名（如 "Chazrick Branson"）
            
        Returns:
            姓氏（如 "Branson"）
        """
        if not full_name:
            return ""
        
        # 按空格分割，取最后一个单词
        parts = full_name.strip().split()
        return parts[-1] if parts else ""


# 创建全局实例
rei_order_api_service = ReiOrderApiService()
