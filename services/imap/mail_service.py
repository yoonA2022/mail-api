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


class MailService:
    """邮件服务 - 统一管理IMAP和数据库操作"""
    
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
    def _parse_imap_tools_message(msg, account_id, folder):
        """使用mailparser解析imap-tools的邮件对象"""
        try:
            # 获取真实UID（imap-tools直接提供）
            uid = str(msg.uid)
            
            # 获取原始邮件字节数据
            raw_email = msg.obj.as_bytes()
            
            # 使用mailparser解析邮件
            mail = mailparser.parse_from_bytes(raw_email)
            
            # 解析主题（mailparser自动解码）
            subject = mail.subject or ''
            
            # 解析发件人（mailparser自动解码）
            from_email = ''
            from_name = ''
            if mail.from_:
                # mail.from_ 是一个列表，格式: [(name, email)]
                if isinstance(mail.from_, list) and len(mail.from_) > 0:
                    from_tuple = mail.from_[0]
                    if isinstance(from_tuple, tuple) and len(from_tuple) >= 2:
                        from_name = from_tuple[0] or ''
                        from_email = from_tuple[1] or ''
                    else:
                        from_email = str(from_tuple)
            
            # 解析收件人（mailparser自动解码）
            to_emails = []
            if mail.to:
                for to_tuple in mail.to:
                    if isinstance(to_tuple, tuple) and len(to_tuple) >= 2:
                        to_emails.append(to_tuple[1])
                    else:
                        to_emails.append(str(to_tuple))
            
            # 解析抄送（mailparser自动解码）
            cc_emails = []
            if mail.cc:
                for cc_tuple in mail.cc:
                    if isinstance(cc_tuple, tuple) and len(cc_tuple) >= 2:
                        cc_emails.append(cc_tuple[1])
                    else:
                        cc_emails.append(str(cc_tuple))
            
            # 解析密送（mailparser自动解码）
            bcc_emails = []
            if mail.bcc:
                for bcc_tuple in mail.bcc:
                    if isinstance(bcc_tuple, tuple) and len(bcc_tuple) >= 2:
                        bcc_emails.append(bcc_tuple[1])
                    else:
                        bcc_emails.append(str(bcc_tuple))
            
            # 解析日期
            date = None
            if mail.date:
                try:
                    date = mail.date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    date = str(mail.date) if mail.date else None
            
            # Message-ID
            message_id = mail.message_id or ''
            
            # 邮件大小
            size = msg.size or 0
            
            # 标记（flags）- 从imap-tools获取
            flags = list(msg.flags) if msg.flags else []
            
            # 附件信息（mailparser自动解码文件名）
            has_attachments = 1 if mail.attachments else 0
            attachment_count = len(mail.attachments) if mail.attachments else 0
            attachment_names = []
            if mail.attachments:
                for att in mail.attachments:
                    filename = att.get('filename', '')
                    if filename:
                        attachment_names.append(filename)
            
            # 提取文本预览（mailparser自动解码）
            text_preview = ''
            is_html = 0
            
            # 优先使用纯文本
            if mail.text_plain:
                text_preview = mail.text_plain[0][:500] if isinstance(mail.text_plain, list) else mail.text_plain[:500]
            elif mail.text_html:
                is_html = 1
                html_content = mail.text_html[0] if isinstance(mail.text_html, list) else mail.text_html
                # 将HTML转换为纯文本
                text_preview = MailService._html_to_text(html_content)[:500]
            
            # 如果没有提取到文本，使用主题
            if not text_preview:
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
                'attachment_names': attachment_names,
                'text_preview': text_preview,
                'is_html': is_html
            }
        except Exception as e:
            print(f"❌ mailparser解析失败，使用备用方案: {e}")
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
    
