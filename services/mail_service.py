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


class MailService:
    """邮件服务 - 统一管理IMAP和数据库操作"""
    
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
    def sync_from_imap(account_id: int, folder: str = 'INBOX'):
        """
        从IMAP服务器同步邮件到数据库
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
            
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
            
            # 2. 连接IMAP服务器（使用imap-tools）
            with MailBox(account['imap_host'], account['imap_port']).login(account['email'], account['password']) as mailbox:
                # 选择文件夹
                mailbox.folder.set(folder)
                
                # 3. 获取所有邮件（imap-tools自动使用UID）
                messages = list(mailbox.fetch(AND(all=True), mark_seen=False))
                print(f"📧 发现 {len(messages)} 封邮件")
                
                if not messages:
                    return {'success': True, 'count': 0, 'message': '没有邮件'}
                
                # 4. 解析并存入数据库
                db = get_db_connection()
                saved_count = 0
                total_count = len(messages)
                
                with db.get_cursor() as cursor:
                    for idx, msg in enumerate(messages, 1):
                        try:
                            # 解析邮件数据
                            email_data = MailService._parse_imap_tools_message(msg, account_id, folder)
                            
                            print(f"📧 [{idx}/{total_count}] UID={email_data['uid']}, Subject={email_data['subject'][:50]}")
                            
                            # 检查是否已存在
                            cursor.execute("""
                                SELECT id FROM email_list
                                WHERE account_id = %s AND uid = %s AND folder = %s
                            """, (account_id, email_data['uid'], folder))
                            
                            existing = cursor.fetchone()
                            if existing:
                                print(f"  ⏭️ 跳过（已存在）")
                                continue
                            
                            # 插入数据库
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
                            print(f"  ✅ 已保存")
                        
                        except Exception as e:
                            print(f"⚠️ 解析邮件失败: {e}")
                            traceback.print_exc()
                            continue
                
                print(f"✅ 同步完成: 新增 {saved_count}/{total_count} 封邮件")
                
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
                    'message': f'同步完成: 新增 {saved_count} 封邮件'
                }
        
        except Exception as e:
            print(f"❌ IMAP同步失败: {e}")
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
                # mailparser已经提供了纯文本版本
                if mail.text_plain:
                    text_preview = mail.text_plain[0][:500] if isinstance(mail.text_plain, list) else mail.text_plain[:500]
                else:
                    # 如果没有纯文本，使用HTML（mailparser会自动处理）
                    text_preview = html_content[:500]
            
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
    
