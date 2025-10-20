"""
性能配置
用于调整线程池、连接池等性能参数
"""

# ==================== 线程池配置 ====================

# IMAP操作线程池配置
IMAP_THREAD_POOL_SIZE = 10  # 增加到10个工作线程，支持更多并发

# 数据库操作线程池配置
DB_THREAD_POOL_SIZE = 20  # 数据库操作相对较快，可以更多

# ==================== 数据库连接池配置 ====================

DATABASE_POOL_CONFIG = {
    'maxconnections': 50,   # 最大连接数
    'mincached': 5,         # 最小空闲连接数
    'maxcached': 20,        # 最大空闲连接数
    'blocking': True,       # 连接池满时等待而非报错
    'maxusage': 0,          # 连接可重用次数（0=无限制）
    'ping': 1,              # 使用前检查连接（0=不检查, 1=默认检查, 2=乐观检查）
}

# ==================== 监控服务配置 ====================

# 新邮件检测间隔（秒）
MONITOR_CHECK_INTERVAL = 60  # 从15秒改为60秒，减少频繁检测

# 监控服务并发检测数
MONITOR_MAX_CONCURRENT = 5  # 同时检测的账户数

# ==================== IMAP 操作配置 ====================

# IMAP 连接超时（秒）
IMAP_CONNECT_TIMEOUT = 30

# IMAP 操作超时（秒）
IMAP_OPERATION_TIMEOUT = 60

# 每次同步的最大邮件数
SYNC_MAX_EMAILS = 100

# ==================== 缓存配置 ====================

# 账户信息缓存时间（秒）
ACCOUNT_CACHE_TTL = 300  # 5分钟

# 邮件列表缓存时间（秒）
EMAIL_LIST_CACHE_TTL = 60  # 1分钟

# ==================== 搜索配置 ====================

# 搜索结果最大返回数量
SEARCH_MAX_LIMIT = 500

# 搜索超时（秒）
SEARCH_TIMEOUT = 10

# ==================== WebSocket 配置 ====================

# 心跳间隔（秒）
WS_PING_INTERVAL = 30

# 连接超时（秒）
WS_CONNECTION_TIMEOUT = 60

# 每个账户最大连接数
WS_MAX_CONNECTIONS_PER_ACCOUNT = 10

