"""
核心邮件服务 - 简洁版
负责：IMAP连接、邮件同步、数据库操作
"""

from imap_tools import MailBox, AND
from config.database import get_db_connection
import json
from datetime import datetime
import traceback
import mailparser
from bs4 import BeautifulSoup
import re
from email import message_from_bytes
from email.header import decode_header
from email.utils import parseaddr, getaddresses


class MailService:
    """邮件服务 - 统一管理IMAP和数据库操作"""
    
    @staticmethod
    def _parse_email_addresses(header_value):
        """
        解析邮件地址字段（From, To, Cc, Bcc）
        正确处理各种格式：
        - "Name" <email@example.com>
        - Name <email@example.com>
        - email@example.com
        
        Args:
            header_value: 邮件地址头部原始值
            
        Returns:
            邮件地址列表（只包含邮箱地址）
        """
        if not header_value:
            return []
        
        try:
            # 先解码头部
            decoded = MailService._decode_mail_header(header_value)
            
            # 使用 getaddresses 正确解析地址
            addresses = getaddresses([decoded])
            
            # 只返回邮箱地址部分
            return [email.strip() for name, email in addresses if email.strip()]
        except Exception as e:
            print(f"⚠️ 解析邮件地址失败: {e}")
            # 降级处理：简单分割
            decoded = MailService._decode_mail_header(header_value)
            return [addr.strip() for addr in decoded.split(',') if addr.strip()]
    
    @staticmethod
    def _parse_from_address(header_value):
        """
        解析发件人地址
        返回 (名称, 邮箱) 元组
        
        Args:
            header_value: From 头部原始值
            
        Returns:
            (from_name, from_email) 元组
        """
        if not header_value:
            return ('', '')
        
        try:
            # 先解码头部
            decoded = MailService._decode_mail_header(header_value)
            
            # 使用 parseaddr 解析
            name, email = parseaddr(decoded)
            
            return (name.strip(), email.strip())
        except Exception as e:
            print(f"⚠️ 解析发件人失败: {e}")
            return ('', decoded.strip())
    
    @staticmethod
    def _decode_mail_header(header_value):
        """
        解码邮件头部（主题、发件人等）
        正确处理各种编码，特别是 iso-2022-jp
        
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
                            # 如果指定的charset失败，尝试其他编码
                            decoded = MailService._try_decode_bytes(content, charset)
                            result.append(decoded)
                    else:
                        # 没有指定charset，尝试智能解码
                        decoded = MailService._try_decode_bytes(content)
                        result.append(decoded)
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
        
        # 编码优先级列表
        encodings = []
        
        # 如果有建议的编码，优先尝试
        if suggested_charset:
            encodings.append(suggested_charset.lower())
        
        # 常见编码列表（优先日文和中文）
        encodings.extend([
            'iso-2022-jp',      # 日文邮件最常用
            'shift_jis',        # 日文 Windows
            'euc-jp',           # 日文 Unix
            'cp932',            # 日文 Windows 扩展
            'utf-8',            # 通用
            'gbk',              # 中文简体
            'gb2312',           # 中文简体
            'gb18030',          # 中文简体扩展
            'big5',             # 中文繁体
            'latin1',           # 西文
            'ascii',            # ASCII
        ])
        
        # 去重，保持顺序
        seen = set()
        unique_encodings = []
        for enc in encodings:
            if enc and enc not in seen:
                seen.add(enc)
                unique_encodings.append(enc)
        
        # 逐个尝试
        for encoding in unique_encodings:
            try:
                decoded = byte_content.decode(encoding)
                # 检查是否包含太多替换字符（�）
                if decoded.count('�') < len(decoded) * 0.1:  # 如果替换字符少于10%
                    return decoded
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 所有编码都失败，使用utf-8带错误处理
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
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script和style标签
            for script in soup(['script', 'style']):
                script.decompose()
            
            # 获取纯文本
            text = soup.get_text()
            
            # 清理多余的空白字符
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"⚠️ HTML转文本失败: {e}")
            # 如果解析失败，使用简单的正则表达式去除HTML标签
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
            账户信息字典，如果不存在返回None
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
    def get_mail_list(account_id: int, folder: str = 'INBOX', limit: int = 100, offset: int = 0):
        """
        获取邮件列表（智能模式）
        
        逻辑：
        1. 先查询数据库
        2. 如果数据库为空，从IMAP同步
        3. 返回邮件列表
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            {
                'success': True,
                'data': [...],
                'count': 22,
                'total': 22
            }
        """
        try:
            db = get_db_connection()
            
            # 1. 查询数据库邮件总数
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                """, (account_id, folder))
                
                total = cursor.fetchone()['total']
            
            # 2. 如果数据库为空，从IMAP同步
            if total == 0:
                print(f"📥 数据库为空，开始同步账户 {account_id} 的邮件...")
                sync_result = MailService.sync_from_imap(account_id, folder)
                
                if not sync_result['success']:
                    return sync_result
                
                total = sync_result['count']
            
            # 3. 查询邮件列表
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, has_attachments, 
                        attachment_count, attachment_names, text_preview, 
                        is_html, folder, synced_at
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                    ORDER BY date DESC
                    LIMIT %s OFFSET %s
                """, (account_id, folder, limit, offset))
                
                emails = cursor.fetchall()
                print(f"✅ 查询结果: 返回 {len(emails)} 封邮件")
                
                return {
                    'success': True,
                    'data': emails,
                    'count': len(emails),
                    'total': total
                }
        
        except Exception as e:
            print(f"❌ 获取邮件列表失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0,
                'total': 0
            }
    
    @staticmethod
    def sync_from_imap(account_id: int, folder: str = 'INBOX', batch_size: int = 50, progress_callback=None):
        """
        从IMAP服务器同步邮件到数据库（优化版）
        
        优化点：
        1. 批量检查已存在的UID
        2. 批量插入数据库
        3. 分批处理，避免内存溢出
        4. 支持进度回调
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            batch_size: 每批处理的邮件数量，默认50
            progress_callback: 进度回调函数 callback(current, total, message)
            
        Returns:
            {
                'success': True,
                'count': 22,
                'message': '同步成功'
            }
        """
        start_time = datetime.now()
        
        try:
            # 1. 获取账户信息
            account = MailService._get_account(account_id)
            if not account:
                return {'success': False, 'error': '账户不存在'}
            
            print(f"🔗 连接IMAP服务器: {account['imap_host']}:{account['imap_port']}")
            
            # 2. 连接IMAP服务器
            with MailBox(account['imap_host'], account['imap_port']).login(account['email'], account['password']) as mailbox:
                mailbox.folder.set(folder)
                
                # 3. 获取所有邮件UID（只获取UID，不获取邮件内容）
                messages = list(mailbox.fetch(AND(all=True), mark_seen=False))
                total_count = len(messages)
                print(f"📧 发现 {total_count} 封邮件")
                
                if not messages:
                    return {'success': True, 'count': 0, 'message': '没有邮件'}
                
                # 4. 批量检查哪些UID已存在
                db = get_db_connection()
                all_uids = [str(msg.uid) for msg in messages]
                
                with db.get_cursor() as cursor:
                    # 批量查询已存在的UID
                    placeholders = ','.join(['%s'] * len(all_uids))
                    cursor.execute(f"""
                        SELECT uid FROM email_list
                        WHERE account_id = %s AND folder = %s AND uid IN ({placeholders})
                    """, [account_id, folder] + all_uids)
                    
                    existing_uids = {row['uid'] for row in cursor.fetchall()}
                    print(f"📊 数据库已有 {len(existing_uids)} 封邮件")
                
                # 5. 过滤出需要同步的邮件
                new_messages = [msg for msg in messages if str(msg.uid) not in existing_uids]
                new_count = len(new_messages)
                
                if new_count == 0:
                    print(f"✅ 没有新邮件需要同步")
                    return {'success': True, 'count': 0, 'message': '没有新邮件'}
                
                print(f"📥 准备同步 {new_count} 封新邮件")
                
                # 6. 分批处理邮件
                saved_count = 0
                
                for batch_start in range(0, new_count, batch_size):
                    batch_end = min(batch_start + batch_size, new_count)
                    batch_messages = new_messages[batch_start:batch_end]
                    
                    print(f"\n🔄 处理第 {batch_start + 1}-{batch_end} 封邮件...")
                    
                    # 解析这批邮件
                    batch_data = []
                    for idx, msg in enumerate(batch_messages, batch_start + 1):
                        try:
                            email_data = MailService._parse_imap_tools_message(msg, account_id, folder)
                            batch_data.append(email_data)
                            
                            print(f"📧 [{idx}/{new_count}] UID={email_data['uid']}, Subject={email_data['subject'][:50]}")
                            
                            # 进度回调
                            if progress_callback:
                                progress_callback(idx, new_count, f"正在解析第 {idx}/{new_count} 封邮件")
                        
                        except Exception as e:
                            print(f"⚠️ 解析邮件失败: {e}")
                            traceback.print_exc()
                            continue
                    
                    # 批量插入数据库
                    if batch_data:
                        with db.get_cursor() as cursor:
                            for email_data in batch_data:
                                try:
                                    cursor.execute("""
                                        INSERT INTO email_list (
                                            account_id, uid, message_id, subject, from_email, from_name,
                                            to_emails, cc_emails, bcc_emails, date, size, flags, has_attachments,
                                            attachment_count, attachment_names, text_preview,
                                            is_html, folder, synced_at
                                        ) VALUES (
                                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                        )
                                    """, (
                                        account_id,
                                        email_data['uid'],
                                        email_data['message_id'],
                                        email_data['subject'],
                                        email_data['from_email'],
                                        email_data['from_name'],
                                        json.dumps(email_data['to_emails']),
                                        json.dumps(email_data['cc_emails']),
                                        json.dumps(email_data['bcc_emails']),
                                        email_data['date'],
                                        email_data['size'],
                                        json.dumps(email_data['flags']),
                                        email_data['has_attachments'],
                                        email_data['attachment_count'],
                                        json.dumps(email_data['attachment_names']),
                                        email_data['text_preview'],
                                        email_data['is_html'],
                                        folder,
                                        datetime.now()
                                    ))
                                    saved_count += 1
                                except Exception as e:
                                    print(f"⚠️ 插入数据库失败: {e}")
                                    continue
                        
                        print(f"✅ 批次保存完成: {len(batch_data)} 封邮件")
                
                print(f"\n✅ 同步完成: 新增 {saved_count}/{new_count} 封邮件")
                
                # 记录同步日志
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                try:
                    with db.get_cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO email_sync_log (
                                account_id, folder, total_emails, new_emails, 
                                status, start_time, end_time, duration
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            account_id, folder, total_count, saved_count,
                            'success', start_time, end_time, duration
                        ))
                        print(f"📊 同步日志已记录: 耗时 {duration:.2f}秒")
                except Exception as e:
                    print(f"⚠️ 记录同步日志失败: {e}")
                
                return {
                    'success': True,
                    'count': saved_count,
                    'total': total_count,
                    'message': f'同步完成: 新增 {saved_count} 封邮件'
                }
        
        except Exception as e:
            print(f"❌ IMAP同步失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    @staticmethod
    def check_new_mail(account_id: int, folder: str = 'INBOX'):
        """
        检测是否有新邮件
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            
        Returns:
            {
                'has_new': True,
                'server_count': 25,
                'db_count': 22,
                'new_count': 3
            }
        """
        try:
            # 1. 获取IMAP服务器邮件数量
            account = MailService._get_account(account_id)
            if not account:
                return {'has_new': False, 'error': '账户不存在'}
            
            with MailBox(account['imap_host'], account['imap_port']).login(account['email'], account['password']) as mailbox:
                mailbox.folder.set(folder)
                messages = list(mailbox.fetch(AND(all=True), mark_seen=False))
                server_count = len(messages)
            
            # 2. 获取数据库邮件数量
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                """, (account_id, folder))
                
                db_count = cursor.fetchone()['count']
            
            # 3. 比较数量
            has_new = server_count > db_count
            new_count = server_count - db_count if has_new else 0
            
            return {
                'has_new': has_new,
                'server_count': server_count,
                'db_count': db_count,
                'new_count': new_count
            }
        
        except Exception as e:
            print(f"❌ 检测新邮件失败: {e}")
            return {
                'has_new': False,
                'error': str(e)
            }
    
    @staticmethod
    def sync_deleted_emails(account_id: int, folder: str = 'INBOX'):
        """
        同步删除的邮件
        
        工作流程：
        1. 连接IMAP服务器，获取所有邮件UID
        2. 查询数据库中的所有UID
        3. 找出数据库中存在但服务器上不存在的UID（已删除的邮件）
        4. 从数据库中删除这些邮件
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            
        Returns:
            {
                'success': True,
                'deleted_count': 5,
                'server_count': 100,
                'db_count': 105,
                'message': '同步删除完成'
            }
        """
        try:
            # 1. 获取账户信息
            account = MailService._get_account(account_id)
            if not account:
                return {'success': False, 'error': '账户不存在'}
            
            print(f"🔄 开始同步删除邮件: 账户 {account_id}, 文件夹 {folder}")
            
            # 2. 连接IMAP服务器，获取所有邮件UID
            with MailBox(account['imap_host'], account['imap_port']).login(account['email'], account['password']) as mailbox:
                mailbox.folder.set(folder)
                
                # 获取服务器上所有邮件的UID
                messages = list(mailbox.fetch(AND(all=True), mark_seen=False))
                server_uids = {str(msg.uid) for msg in messages}
                server_count = len(server_uids)
                
                print(f"📧 IMAP服务器上有 {server_count} 封邮件")
            
            # 3. 查询数据库中的所有UID
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT uid FROM email_list
                    WHERE account_id = %s AND folder = %s
                """, (account_id, folder))
                
                db_uids = {row['uid'] for row in cursor.fetchall()}
                db_count = len(db_uids)
                
                print(f"💾 数据库中有 {db_count} 封邮件")
            
            # 4. 找出需要删除的UID（数据库中有但服务器上没有的）
            uids_to_delete = db_uids - server_uids
            deleted_count = len(uids_to_delete)
            
            if deleted_count == 0:
                print(f"✅ 没有需要删除的邮件")
                return {
                    'success': True,
                    'deleted_count': 0,
                    'server_count': server_count,
                    'db_count': db_count,
                    'message': '没有需要删除的邮件'
                }
            
            print(f"🗑️ 发现 {deleted_count} 封已删除的邮件，准备从数据库中删除...")
            
            # 5. 从数据库中删除这些邮件
            with db.get_cursor() as cursor:
                for uid in uids_to_delete:
                    try:
                        cursor.execute("""
                            DELETE FROM email_list
                            WHERE account_id = %s AND uid = %s AND folder = %s
                        """, (account_id, uid, folder))
                        
                        print(f"🗑️ 已删除 UID: {uid}")
                    
                    except Exception as e:
                        print(f"⚠️ 删除邮件失败 (UID={uid}): {e}")
                        continue
            
            print(f"✅ 同步删除完成: 删除了 {deleted_count} 封邮件")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'server_count': server_count,
                'db_count': db_count - deleted_count,
                'message': f'成功删除 {deleted_count} 封邮件'
            }
        
        except Exception as e:
            print(f"❌ 同步删除邮件失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    @staticmethod
    def refresh_mail_status(account_id: int, folder: str = 'INBOX'):
        """
        刷新邮件状态（已读、星标等）
        
        工作流程：
        1. 连接IMAP服务器
        2. 获取所有邮件的UID和flags
        3. 批量更新数据库中对应邮件的flags字段
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            
        Returns:
            {
                'success': True,
                'updated_count': 22,
                'message': '更新成功'
            }
        """
        try:
            # 1. 获取账户信息
            account = MailService._get_account(account_id)
            if not account:
                return {'success': False, 'error': '账户不存在'}
            
            print(f"🔄 开始刷新邮件状态: 账户 {account_id}, 文件夹 {folder}")
            
            # 2. 连接IMAP服务器
            with MailBox(account['imap_host'], account['imap_port']).login(account['email'], account['password']) as mailbox:
                mailbox.folder.set(folder)
                
                # 3. 获取所有邮件的UID和flags（不下载邮件内容）
                messages = list(mailbox.fetch(AND(all=True), mark_seen=False))
                
                if not messages:
                    return {'success': True, 'updated_count': 0, 'message': '没有邮件需要更新'}
                
                print(f"📧 服务器上有 {len(messages)} 封邮件，开始更新状态...")
                
                # 4. 批量更新数据库
                db = get_db_connection()
                updated_count = 0
                
                with db.get_cursor() as cursor:
                    for msg in messages:
                        try:
                            uid = str(msg.uid)
                            flags = list(msg.flags) if msg.flags else []
                            
                            # 更新数据库中的flags字段
                            cursor.execute("""
                                UPDATE email_list
                                SET flags = %s
                                WHERE account_id = %s AND uid = %s AND folder = %s
                            """, (json.dumps(flags), account_id, uid, folder))
                            
                            if cursor.rowcount > 0:
                                updated_count += 1
                        
                        except Exception as e:
                            print(f"⚠️ 更新邮件状态失败 (UID={uid}): {e}")
                            continue
                
                print(f"✅ 状态刷新完成: 更新了 {updated_count}/{len(messages)} 封邮件")
                
                return {
                    'success': True,
                    'updated_count': updated_count,
                    'total_count': len(messages),
                    'message': f'成功更新 {updated_count} 封邮件的状态'
                }
        
        except Exception as e:
            print(f"❌ 刷新邮件状态失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0
            }
    
    @staticmethod
    def _parse_imap_tools_message(msg, account_id, folder):
        """
        使用 Python email 标准库解析邮件（正确处理各种编码）
        
        Args:
            msg: imap-tools 邮件对象
            account_id: 账户ID
            folder: 文件夹名称
            
        Returns:
            解析后的邮件数据字典
        """
        try:
            # 获取真实UID（imap-tools直接提供）
            uid = str(msg.uid)
            
            # 获取原始邮件字节数据
            raw_email = msg.obj.as_bytes()
            
            # 使用 Python email 标准库解析（能正确处理 iso-2022-jp 等编码）
            email_msg = message_from_bytes(raw_email)
            
            # 解析主题
            subject = MailService._decode_mail_header(email_msg.get('Subject', ''))
            
            # 解析发件人（使用新的解析方法）
            from_name, from_email = MailService._parse_from_address(email_msg.get('From', ''))
            
            # 解析收件人（使用新的解析方法）
            to_emails = MailService._parse_email_addresses(email_msg.get('To', ''))
            
            # 解析抄送
            cc_emails = MailService._parse_email_addresses(email_msg.get('Cc', ''))
            
            # 解析密送
            bcc_emails = MailService._parse_email_addresses(email_msg.get('Bcc', ''))
            
            # 解析日期
            date = None
            if msg.date:
                try:
                    date = msg.date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    date = None
            
            # Message-ID
            message_id = email_msg.get('Message-ID', '')
            
            # 邮件大小
            size = msg.size or 0
            
            # 标记（flags）- 从imap-tools获取
            flags = list(msg.flags) if msg.flags else []
            
            # 解析邮件正文和附件
            text_content = ''
            html_content = ''
            attachments_info = []
            
            if email_msg.is_multipart():
                # 多部分邮件
                for part in email_msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get('Content-Disposition', '')
                    
                    # 处理附件
                    if 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            # 解码文件名
                            decoded_filename = MailService._decode_mail_header(filename)
                            attachments_info.append(decoded_filename)
                    
                    # 处理正文
                    elif content_type == 'text/plain' and not text_content:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset()
                            text_content = MailService._try_decode_bytes(payload, charset)
                    
                    elif content_type == 'text/html' and not html_content:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset()
                            html_content = MailService._try_decode_bytes(payload, charset)
            else:
                # 单部分邮件
                content_type = email_msg.get_content_type()
                payload = email_msg.get_payload(decode=True)
                
                if payload:
                    charset = email_msg.get_content_charset()
                    decoded_content = MailService._try_decode_bytes(payload, charset)
                    
                    if content_type == 'text/plain':
                        text_content = decoded_content
                    elif content_type == 'text/html':
                        html_content = decoded_content
            
            # 附件信息
            has_attachments = 1 if attachments_info else 0
            attachment_count = len(attachments_info)
            
            # 生成文本预览
            text_preview = ''
            is_html = 0
            
            if text_content:
                # 优先使用纯文本
                text_preview = text_content[:500]
            elif html_content:
                # 如果没有纯文本，从HTML提取
                is_html = 1
                text_preview = MailService._html_to_text(html_content)[:500]
            else:
                # 都没有，使用主题
                text_preview = subject[:200] if subject else ''
            
            return {
                'uid': uid,
                'message_id': message_id,
                'subject': subject,
                'from_email': from_email,
                'from_name': from_name,
                'to_emails': to_emails,
                'cc_emails': cc_emails,
                'bcc_emails': bcc_emails,
                'date': date,
                'size': size,
                'flags': flags,
                'has_attachments': has_attachments,
                'attachment_count': attachment_count,
                'attachment_names': attachments_info,
                'text_preview': text_preview,
                'is_html': is_html
            }
            
        except Exception as e:
            print(f"❌ email标准库解析失败，使用备用方案: {e}")
            traceback.print_exc()
            
            # 备用方案：使用imap-tools的基本信息
            return {
                'uid': str(msg.uid),
                'message_id': '',
                'subject': msg.subject or '',
                'from_email': msg.from_ or '',
                'from_name': '',
                'to_emails': [addr.email for addr in msg.to_values] if msg.to_values else [],
                'cc_emails': [],
                'bcc_emails': [],
                'date': msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else None,
                'size': msg.size or 0,
                'flags': list(msg.flags) if msg.flags else [],
                'has_attachments': 1 if msg.attachments else 0,
                'attachment_count': len(msg.attachments) if msg.attachments else 0,
                'attachment_names': [],
                'text_preview': msg.text[:500] if msg.text else '',
                'is_html': 1 if msg.html else 0
            }
    
    @staticmethod
    def get_email_detail(account_id: int, email_id: int):
        """
        获取邮件详情（包括完整正文）
        
        Args:
            account_id: 账户ID
            email_id: 邮件ID（数据库ID）
            
        Returns:
            邮件详情字典，包含完整的文本和HTML内容
        """
        try:
            # 1. 从数据库获取邮件基本信息
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, 
                        has_attachments, attachment_count, attachment_names, 
                        text_preview, is_html, folder, synced_at
                    FROM email_list
                    WHERE id = %s AND account_id = %s
                """, (email_id, account_id))
                
                email = cursor.fetchone()
                
                if not email:
                    return {
                        'success': False,
                        'error': '邮件不存在'
                    }
            
            # 2. 从IMAP服务器获取完整邮件内容
            account = MailService._get_account(account_id)
            if not account:
                return {
                    'success': False,
                    'error': '账户不存在'
                }
            
            # 连接IMAP服务器
            try:
                with MailBox(account['imap_host'], account['imap_port']).login(
                    account['email'], 
                    account['password'],
                    initial_folder=email['folder']
                ) as mailbox:
                    # 使用UID获取邮件
                    for msg in mailbox.fetch(AND(uid=email['uid'])):
                        # 解析邮件获取完整内容
                        try:
                            # 使用 Python email 标准库解析（正确处理编码）
                            raw_email = msg.obj.as_bytes()
                            email_msg = message_from_bytes(raw_email)
                            
                            # 获取文本和HTML内容
                            text_content = None
                            html_content = None
                            attachments = []
                            
                            if email_msg.is_multipart():
                                # 多部分邮件
                                for part in email_msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = part.get('Content-Disposition', '')
                                    
                                    # 处理附件
                                    if 'attachment' in content_disposition:
                                        filename = part.get_filename()
                                        if filename:
                                            decoded_filename = MailService._decode_mail_header(filename)
                                            payload = part.get_payload(decode=True)
                                            attachments.append({
                                                'filename': decoded_filename,
                                                'content_type': part.get_content_type(),
                                                'size': len(payload) if payload else 0,
                                                'content_id': part.get('Content-ID')
                                            })
                                    
                                    # 处理正文
                                    elif content_type == 'text/plain' and not text_content:
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            charset = part.get_content_charset()
                                            text_content = MailService._try_decode_bytes(payload, charset)
                                    
                                    elif content_type == 'text/html' and not html_content:
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            charset = part.get_content_charset()
                                            html_content = MailService._try_decode_bytes(payload, charset)
                            else:
                                # 单部分邮件
                                content_type = email_msg.get_content_type()
                                payload = email_msg.get_payload(decode=True)
                                
                                if payload:
                                    charset = email_msg.get_content_charset()
                                    decoded_content = MailService._try_decode_bytes(payload, charset)
                                    
                                    if content_type == 'text/plain':
                                        text_content = decoded_content
                                    elif content_type == 'text/html':
                                        html_content = decoded_content
                            
                            # 如果没有纯文本但有HTML，将HTML转为文本
                            if not text_content and html_content:
                                text_content = MailService._html_to_text(html_content)
                            
                            # 解析JSON字段
                            to_emails = json.loads(email['to_emails']) if email['to_emails'] else []
                            cc_emails = json.loads(email['cc_emails']) if email['cc_emails'] else []
                            bcc_emails = json.loads(email['bcc_emails']) if email['bcc_emails'] else []
                            flags = json.loads(email['flags']) if email['flags'] else []
                            
                            # 返回完整邮件详情
                            # 根据实际内容判断是否为HTML邮件
                            has_html = bool(html_content and html_content.strip())
                            
                            return {
                                'success': True,
                                'data': {
                                    'id': email['id'],
                                    'uid': email['uid'],
                                    'message_id': email['message_id'],
                                    'subject': email['subject'],
                                    'from_email': email['from_email'],
                                    'from_name': email['from_name'],
                                    'to_emails': to_emails,
                                    'cc_emails': cc_emails,
                                    'bcc_emails': bcc_emails,
                                    'date': email['date'].isoformat() if email['date'] else None,
                                    'size': email['size'],
                                    'flags': flags,
                                    'has_attachments': email['has_attachments'] == 1,
                                    'attachment_count': email['attachment_count'],
                                    'attachments': attachments,
                                    'text_content': text_content,
                                    'html_content': html_content,
                                    'text_preview': email['text_preview'],
                                    'is_html': has_html,  # 使用实际HTML内容判断
                                    'folder': email['folder'],
                                    'synced_at': email['synced_at'].isoformat() if email['synced_at'] else None
                                }
                            }
                        except Exception as e:
                            print(f"❌ 解析邮件内容失败: {e}")
                            traceback.print_exc()
                            # 返回数据库中的基本信息
                            return {
                                'success': True,
                                'data': {
                                    'id': email['id'],
                                    'uid': email['uid'],
                                    'message_id': email['message_id'],
                                    'subject': email['subject'],
                                    'from_email': email['from_email'],
                                    'from_name': email['from_name'],
                                    'to_emails': json.loads(email['to_emails']) if email['to_emails'] else [],
                                    'cc_emails': json.loads(email['cc_emails']) if email['cc_emails'] else [],
                                    'bcc_emails': json.loads(email['bcc_emails']) if email['bcc_emails'] else [],
                                    'date': email['date'].isoformat() if email['date'] else None,
                                    'size': email['size'],
                                    'flags': json.loads(email['flags']) if email['flags'] else [],
                                    'has_attachments': email['has_attachments'] == 1,
                                    'attachment_count': email['attachment_count'],
                                    'attachments': [],
                                    'text_content': email['text_preview'],
                                    'html_content': None,
                                    'text_preview': email['text_preview'],
                                    'is_html': email['is_html'] == 1,
                                    'folder': email['folder'],
                                    'synced_at': email['synced_at'].isoformat() if email['synced_at'] else None
                                },
                                'warning': '无法获取完整邮件内容，仅返回预览'
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
            print(f"❌ 获取邮件详情失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def mark_as_read(account_id: int, email_id: int):
        """
        标记邮件为已读
        
        工作流程：
        1. 从数据库获取邮件UID
        2. 连接IMAP服务器，设置\\Seen标记
        3. 更新数据库中的flags字段
        
        Args:
            account_id: 账户ID
            email_id: 邮件ID（数据库ID）
            
        Returns:
            {
                'success': True,
                'message': '标记成功'
            }
        """
        try:
            # 1. 从数据库获取邮件信息
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT uid, folder, flags
                    FROM email_list
                    WHERE id = %s AND account_id = %s
                """, (email_id, account_id))
                
                email = cursor.fetchone()
                
                if not email:
                    return {
                        'success': False,
                        'error': '邮件不存在'
                    }
            
            # 解析当前flags
            current_flags = json.loads(email['flags']) if email['flags'] else []
            
            # 检查是否已经是已读状态
            if '\\Seen' in current_flags or '\\SEEN' in current_flags:
                return {
                    'success': True,
                    'message': '邮件已经是已读状态',
                    'already_read': True
                }
            
            # 2. 获取账户信息并连接IMAP服务器
            account = MailService._get_account(account_id)
            if not account:
                return {
                    'success': False,
                    'error': '账户不存在'
                }
            
            # 3. 连接IMAP服务器，设置已读标记
            try:
                with MailBox(account['imap_host'], account['imap_port']).login(
                    account['email'], 
                    account['password'],
                    initial_folder=email['folder']
                ) as mailbox:
                    # 设置已读标记
                    mailbox.flag(email['uid'], ['\\Seen'], True)
                    print(f"✅ IMAP服务器已标记邮件为已读: UID={email['uid']}")
                    
                    # 4. 更新数据库中的flags
                    new_flags = current_flags + ['\\Seen']
                    
                    with db.get_cursor() as cursor:
                        cursor.execute("""
                            UPDATE email_list
                            SET flags = %s
                            WHERE id = %s AND account_id = %s
                        """, (json.dumps(new_flags), email_id, account_id))
                    
                    print(f"✅ 数据库已更新邮件状态: ID={email_id}")
                    
                    return {
                        'success': True,
                        'message': '标记为已读成功',
                        'flags': new_flags
                    }
                    
            except Exception as e:
                print(f"❌ 连接IMAP服务器失败: {e}")
                traceback.print_exc()
                return {
                    'success': False,
                    'error': f'连接IMAP服务器失败: {str(e)}'
                }
                
        except Exception as e:
            print(f"❌ 标记邮件为已读失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
