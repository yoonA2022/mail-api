# IMAP 服务模块说明

## 📁 模块结构

```
services/imap/
├── imap_connector.py    # IMAP连接器 - 统一的连接管理
├── account.py           # 账户管理 - 账户CRUD操作
├── email.py             # 邮件获取 - 从IMAP实时获取邮件
├── email_sync.py        # 邮件同步 - 同步邮件列表到数据库
└── README.md            # 本文档
```
