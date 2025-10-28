"""
REI 订单邮件正文内容服务
用于获取 REI 订单邮件的完整正文内容（文本和HTML）
"""

from config.database import get_db_connection
from imap_tools import MailBox, AND
from email import message_from_bytes
from email.header import decode_header
from typing import Dict, Any, Optional
import json
import traceback
from bs4 import BeautifulSoup
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor


class ReiEmailContentService:
    """REI 订单邮件正文内容服务类"""
    
    # 线程池（用于执行阻塞的IMAP操作）
    _executor = ThreadPoolExecutor(max_workers=5)
    
    @staticmethod
    def _decode_mail_header(header_value):
        """
        解码邮件头部
        
        Args:
            header_value: 邮件头部原始值
            
        Returns:
            解码后的字符串
        """
        if not header_value:
            return ''
        
        try:
            decoded_parts = decode_header(header_value)
            result = []
            
            for content, charset in decoded_parts:
                if isinstance(content, bytes):
                    if charset:
                        try:
                            result.append(content.decode(charset))
                        except:
                            result.append(content.decode('utf-8', errors='replace'))
                    else:
                        result.append(content.decode('utf-8', errors='replace'))
                else:
                    result.append(str(content))
            
            return ''.join(result)
        except Exception as e:
            print(f"⚠️ 解码头部失败: {e}")
            return str(header_value)
    
    @staticmethod
    def _try_decode_bytes(byte_content, suggested_charset=None):
        """
        尝试使用多种编码解码字节内容
        
        Args:
            byte_content: 字节内容
            suggested_charset: 建议的字符集
            
        Returns:
            解码后的字符串
        """
        if not byte_content:
            return ''
        
        encodings = []
        if suggested_charset:
            encodings.append(suggested_charset.lower())
        
        encodings.extend([
            'utf-8', 'iso-8859-1', 'gbk', 'gb2312', 'big5',
            'iso-2022-jp', 'shift_jis', 'euc-jp', 'cp932'
        ])
        
        # 去重
        seen = set()
        unique_encodings = []
        for enc in encodings:
            if enc and enc not in seen:
                seen.add(enc)
                unique_encodings.append(enc)
        
        for encoding in unique_encodings:
            try:
                decoded = byte_content.decode(encoding)
                if decoded.count('�') < len(decoded) * 0.1:
                    return decoded
            except (UnicodeDecodeError, LookupError):
                continue
        
        return byte_content.decode('utf-8', errors='replace')
    
    @staticmethod
    def _html_to_text(html_content: str) -> str:
        """
        将HTML内容转换为纯文本
        
        Args:
            html_content: HTML内容
            
        Returns:
            纯文本内容
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script和style标签
            for script in soup(['script', 'style']):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"⚠️ HTML转文本失败: {e}")
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
    
    @staticmethod
    def _get_account(account_id: int):
        """
        获取账户信息
        
        Args:
            account_id: 账户ID
            
        Returns:
            账户信息字典
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, email, password, imap_host, imap_port, use_ssl
                    FROM imap_accounts
                    WHERE id = %s
                """, (account_id,))
                
                account = cursor.fetchone()
                return account
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            return None
    
    @staticmethod
    def _get_email_content_by_id_sync(email_id: int, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        根据邮件ID获取REI订单邮件的完整正文内容
        
        Args:
            email_id: 邮件数据库ID
            account_id: 账户ID（可选，用于安全验证）
            
        Returns:
            {
                'success': True,
                'data': {
                    'id': 31,
                    'order_number': 'Y127241896',
                    'subject': '...',
                    'from_email': '...',
                    'date': '...',
                    'text_content': '完整文本内容',
                    'html_content': '完整HTML内容',
                    'has_html': True
                }
            }
        """
        try:
            # 1. 从数据库获取邮件基本信息
            db = get_db_connection()
            with db.get_cursor() as cursor:
                where_clause = "id = %s"
                params = [email_id]
                
                if account_id is not None:
                    where_clause += " AND account_id = %s"
                    params.append(account_id)
                
                cursor.execute(f"""
                    SELECT 
                        id, account_id, uid, message_id, subject, 
                        from_email, from_name, to_emails, 
                        date, size, flags, has_attachments, 
                        attachment_count, folder, synced_at
                    FROM email_list
                    WHERE {where_clause}
                """, params)
                
                email = cursor.fetchone()
                
                if not email:
                    return {
                        'success': False,
                        'error': '邮件不存在'
                    }
            
            # 2. 获取账户信息
            account = ReiEmailContentService._get_account(email['account_id'])
            if not account:
                return {
                    'success': False,
                    'error': '账户不存在'
                }
            
            # 3. 连接IMAP服务器获取完整邮件内容
            try:
                with MailBox(account['imap_host'], account['imap_port']).login(
                    account['email'], 
                    account['password'],
                    initial_folder=email['folder']
                ) as mailbox:
                    # 使用UID获取邮件
                    for msg in mailbox.fetch(AND(uid=email['uid']), mark_seen=False):
                        # 使用 Python email 标准库解析
                        raw_email = msg.obj.as_bytes()
                        email_msg = message_from_bytes(raw_email)
                        
                        # 获取文本和HTML内容
                        text_content = None
                        html_content = None
                        
                        if email_msg.is_multipart():
                            # 多部分邮件
                            for part in email_msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = part.get('Content-Disposition', '')
                                
                                # 跳过附件
                                if 'attachment' in content_disposition:
                                    continue
                                
                                # 处理正文
                                if content_type == 'text/plain' and not text_content:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset()
                                        text_content = ReiEmailContentService._try_decode_bytes(payload, charset)
                                
                                elif content_type == 'text/html' and not html_content:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset()
                                        html_content = ReiEmailContentService._try_decode_bytes(payload, charset)
                        else:
                            # 单部分邮件
                            content_type = email_msg.get_content_type()
                            payload = email_msg.get_payload(decode=True)
                            
                            if payload:
                                charset = email_msg.get_content_charset()
                                decoded_content = ReiEmailContentService._try_decode_bytes(payload, charset)
                                
                                if content_type == 'text/plain':
                                    text_content = decoded_content
                                elif content_type == 'text/html':
                                    html_content = decoded_content
                        
                        # 如果没有纯文本但有HTML，将HTML转为文本
                        if not text_content and html_content:
                            text_content = ReiEmailContentService._html_to_text(html_content)
                        
                        # 提取订单号
                        from services.rei.email.rei_email_filter import ReiEmailFilter
                        order_number = ReiEmailFilter.extract_order_number(email['subject'])
                        
                        # 解析JSON字段
                        to_emails = json.loads(email['to_emails']) if email['to_emails'] else []
                        
                        print(f"✅ 成功获取邮件正文内容: ID={email_id}, 订单号={order_number}")
                        
                        return {
                            'success': True,
                            'data': {
                                'id': email['id'],
                                'account_id': email['account_id'],
                                'uid': email['uid'],
                                'order_number': order_number,
                                'subject': email['subject'],
                                'from_email': email['from_email'],
                                'from_name': email['from_name'],
                                'to_emails': to_emails,
                                'date': email['date'].isoformat() if email['date'] else None,
                                'size': email['size'],
                                'has_attachments': email['has_attachments'] == 1,
                                'attachment_count': email['attachment_count'],
                                'text_content': text_content,
                                'html_content': html_content,
                                'has_html': bool(html_content and html_content.strip()),
                                'folder': email['folder']
                            }
                        }
                    
                    # 如果循环结束没有找到邮件
                    return {
                        'success': False,
                        'error': '在IMAP服务器上未找到该邮件'
                    }
                    
            except Exception as e:
                print(f"❌ 连接IMAP服务器失败: {e}")
                traceback.print_exc()
                return {
                    'success': False,
                    'error': f'连接IMAP服务器失败: {str(e)}'
                }
        
        except Exception as e:
            print(f"❌ 获取邮件内容失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    async def get_email_content_by_id(email_id: int, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        异步获取邮件内容（使用线程池避免阻塞）
        
        Args:
            email_id: 邮件数据库ID
            account_id: 账户ID（可选，用于安全验证）
            
        Returns:
            邮件完整内容
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ReiEmailContentService._executor,
            ReiEmailContentService._get_email_content_by_id_sync,
            email_id,
            account_id
        )
    
    @staticmethod
    def get_email_content_by_order_number(
        order_number: str,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        根据订单号获取REI订单邮件的完整正文内容
        
        Args:
            order_number: REI 订单号（如：Y127241896）
            account_id: 账户ID（可选）
            
        Returns:
            邮件完整内容
        """
        try:
            # 1. 先根据订单号查询邮件ID
            from services.rei.email.rei_email_filter import ReiEmailFilter
            result = ReiEmailFilter.get_rei_email_by_order_number(order_number, account_id)
            
            if not result.get('success'):
                return result
            
            email_data = result['data']
            email_id = email_data['id']
            
            # 2. 获取完整内容
            return ReiEmailContentService._get_email_content_by_id_sync(
                email_id=email_id,
                account_id=email_data['account_id']
            )
        
        except Exception as e:
            print(f"❌ 根据订单号获取邮件内容失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
