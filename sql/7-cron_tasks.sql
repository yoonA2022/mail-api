-- ============================================
-- 定时任务表
-- 用于管理系统定时任务的配置和执行状态
-- ============================================

CREATE TABLE IF NOT EXISTS `cron_tasks` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  
  -- 任务基本信息
  `name` VARCHAR(255) NOT NULL COMMENT '任务名称',
  `description` TEXT DEFAULT NULL COMMENT '任务描述',
  `type` VARCHAR(50) NOT NULL DEFAULT 'custom' COMMENT '任务类型（email_sync:邮件同步 order_sync:订单数据同步 email_to_order:订单自动同步状态 cleanup:清理任务 backup:备份任务 custom:自定义）',
  
  -- Cron配置
  `cron_expression` VARCHAR(100) NOT NULL COMMENT 'Cron表达式（6位格式：秒 分 时 日 月 星期）',
  `timezone` VARCHAR(50) NOT NULL DEFAULT 'Asia/Shanghai' COMMENT '时区',
  
  -- 执行配置
  `command` TEXT NOT NULL COMMENT '执行命令或脚本路径',
  `parameters` JSON DEFAULT NULL COMMENT '执行参数（JSON格式）',
  `working_directory` VARCHAR(500) DEFAULT NULL COMMENT '工作目录',
  `environment_vars` JSON DEFAULT NULL COMMENT '环境变量（JSON格式）',
  `log_file_path` VARCHAR(500) DEFAULT NULL COMMENT '日志文件路径（相对于项目根目录）',
  
  -- 任务状态
  `status` ENUM('enabled', 'disabled', 'running', 'error') NOT NULL DEFAULT 'enabled' COMMENT '任务状态',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活（0:否 1:是）',
  
  -- 执行统计
  `run_count` INT NOT NULL DEFAULT 0 COMMENT '总执行次数',
  `success_count` INT NOT NULL DEFAULT 0 COMMENT '成功执行次数',
  `error_count` INT NOT NULL DEFAULT 0 COMMENT '失败执行次数',
  
  -- 时间信息
  `last_run_at` DATETIME DEFAULT NULL COMMENT '上次执行时间',
  `last_success_at` DATETIME DEFAULT NULL COMMENT '上次成功执行时间',
  `last_error_at` DATETIME DEFAULT NULL COMMENT '上次失败执行时间',
  `next_run_at` DATETIME DEFAULT NULL COMMENT '下次执行时间',
  
  -- 执行限制
  `timeout_seconds` INT DEFAULT 300 COMMENT '超时时间（秒）',
  `max_retries` INT DEFAULT 3 COMMENT '最大重试次数',
  `retry_interval` INT DEFAULT 60 COMMENT '重试间隔（秒）',
  
  -- 通知配置
  `notify_on_success` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '成功时是否通知（0:否 1:是）',
  `notify_on_failure` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '失败时是否通知（0:否 1:是）',
  `notification_emails` JSON DEFAULT NULL COMMENT '通知邮箱列表（JSON格式）',
  
  -- 管理信息
  `created_by` INT DEFAULT NULL COMMENT '创建者ID',
  `updated_by` INT DEFAULT NULL COMMENT '更新者ID',
  `priority` TINYINT NOT NULL DEFAULT 5 COMMENT '优先级（1-10，数字越小优先级越高）',
  `tags` JSON DEFAULT NULL COMMENT '标签（JSON格式）',
  `remark` TEXT DEFAULT NULL COMMENT '备注说明',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '删除时间（软删除）',
  
  -- 索引
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_type` (`type`),
  KEY `idx_status` (`status`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_next_run_at` (`next_run_at`),
  KEY `idx_created_by` (`created_by`),
  KEY `idx_priority` (`priority`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_deleted_at` (`deleted_at`),
  
  -- 外键约束
  CONSTRAINT `fk_cron_tasks_created_by` FOREIGN KEY (`created_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_cron_tasks_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='定时任务表';

-- ============================================
-- 定时任务执行日志表
-- ============================================

CREATE TABLE IF NOT EXISTS `cron_task_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `task_id` INT NOT NULL COMMENT '任务ID',
  `task_name` VARCHAR(255) NOT NULL COMMENT '任务名称（冗余字段，便于查询）',
  
  -- 执行信息
  `execution_id` VARCHAR(100) NOT NULL COMMENT '执行ID（UUID）',
  `status` ENUM('running', 'success', 'error', 'timeout', 'cancelled') NOT NULL COMMENT '执行状态',
  `trigger_type` VARCHAR(50) NOT NULL DEFAULT 'scheduled' COMMENT '触发类型（scheduled:定时触发 manual:手动触发 retry:重试触发）',
  
  -- 时间信息
  `started_at` DATETIME NOT NULL COMMENT '开始执行时间',
  `finished_at` DATETIME DEFAULT NULL COMMENT '结束执行时间',
  `duration_ms` INT DEFAULT NULL COMMENT '执行耗时（毫秒）',
  
  -- 执行结果
  `exit_code` INT DEFAULT NULL COMMENT '退出码',
  `output` LONGTEXT DEFAULT NULL COMMENT '标准输出',
  `error_output` LONGTEXT DEFAULT NULL COMMENT '错误输出',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  
  -- 系统信息
  `server_hostname` VARCHAR(255) DEFAULT NULL COMMENT '执行服务器主机名',
  `server_ip` VARCHAR(45) DEFAULT NULL COMMENT '执行服务器IP',
  `process_id` INT DEFAULT NULL COMMENT '进程ID',
  
  -- 重试信息
  `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  `max_retries` INT DEFAULT NULL COMMENT '最大重试次数',
  `is_retry` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为重试执行（0:否 1:是）',
  `parent_log_id` INT DEFAULT NULL COMMENT '父日志ID（重试时关联原始日志）',
  
  -- 其他信息
  `memory_usage_mb` DECIMAL(10,2) DEFAULT NULL COMMENT '内存使用量（MB）',
  `cpu_usage_percent` DECIMAL(5,2) DEFAULT NULL COMMENT 'CPU使用率（%）',
  `triggered_by` INT DEFAULT NULL COMMENT '触发者ID（手动触发时）',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  -- 索引
  KEY `idx_task_id` (`task_id`),
  KEY `idx_execution_id` (`execution_id`),
  KEY `idx_status` (`status`),
  KEY `idx_trigger_type` (`trigger_type`),
  KEY `idx_started_at` (`started_at`),
  KEY `idx_finished_at` (`finished_at`),
  KEY `idx_is_retry` (`is_retry`),
  KEY `idx_parent_log_id` (`parent_log_id`),
  KEY `idx_created_at` (`created_at`),
  
  -- 外键约束
  CONSTRAINT `fk_cron_task_logs_task` FOREIGN KEY (`task_id`) REFERENCES `cron_tasks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_cron_task_logs_triggered_by` FOREIGN KEY (`triggered_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_cron_task_logs_parent` FOREIGN KEY (`parent_log_id`) REFERENCES `cron_task_logs` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='定时任务执行日志表';

-- ============================================
-- 插入演示数据
-- ============================================

-- 邮件同步任务1: 只同步启用自动同步的账户（推荐用于生产环境）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`, 
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '邮件同步 - 只同步启用的账户',
  '定时同步IMAP邮件（只同步 auto_sync=1 且 status=1 的账户）',
  'email_sync',
  '0 0 */3 * * *',
  'python services/cron/tasks/email_sync/email_sync_task.py --folder INBOX --batch-size 50 --auto-sync-only',
  NULL,
  'services/cron/tasks/email_sync/logs/task.log',
  'disabled',
  600,
  1,
  '["admin@example.com", "tech@example.com"]',
  1,
  3,
  '["邮件", "同步", "IMAP", "自动"]'
);

-- 邮件同步任务2: 同步所有账户（用于全量同步）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`, 
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '邮件同步 - 同步所有账户',
  '定时同步IMAP邮件（同步所有账户，忽略 auto_sync 状态）',
  'email_sync',
  '0 0 */3 * * *',
  'python services/cron/tasks/email_sync/email_sync_task.py --folder INBOX --batch-size 100 --all',
  NULL,
  'services/cron/tasks/email_sync/logs/task.log',
  'disabled',
  1200,
  1,
  '["admin@example.com"]',
  1,
  2,
  '["邮件", "同步", "IMAP", "全量"]'
);

-- 邮件同步任务3: 同步指定账户（用于测试或单账户同步）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`, 
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '邮件同步 - 同步指定账户',
  '定时同步IMAP邮件（只同步账户ID=1，用于测试）',
  'email_sync',
  '0 0 */3 * * *',
  'python services/cron/tasks/email_sync/email_sync_task.py --account-id 1 --folder INBOX --batch-size 50',
  NULL,
  'services/cron/tasks/email_sync/logs/task.log',
  'disabled',
  300,
  0,
  '["tech@example.com"]',
  1,
  1,
  '["邮件", "同步", "IMAP", "测试"]'
);

-- 订单同步任务 场景 1：使用默认配置（跳过已存在的订单）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`,
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '订单数据同步使用默认配置（跳过已存在的订单）',
  '每2小时自动筛选订单邮件并保存到订单数据库里',
  'order_sync',
  '0 0 */2 * * *',
  'python services/cron/tasks/order_sync/order_sync_task.py',
  '{"limit": 100, "skip_existing": true, "auto_sync_only": true}',
  'services/cron/tasks/order_sync/logs/task.log',
  'disabled',
  1800,
  1,
  '["admin@example.com", "business@example.com"]',
  1,
  2,
  '["订单", "同步", "REI"]'
);

-- 订单同步任务 场景 2：强制重新同步所有订单
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`,
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '订单数据同步 - 强制重新同步',
  '强制重新同步所有订单（不跳过已存在的订单），适用于数据修复场景',
  'order_sync',
  '0 0 3 * * *',
  'python services/cron/tasks/order_sync/order_sync_task.py',
  '{"limit": 200, "skip_existing": false, "auto_sync_only": true}',
  'services/cron/tasks/order_sync/logs/task.log',
  'disabled',
  3600,
  1,
  '["admin@example.com", "business@example.com"]',
  1,
  3,
  '["订单", "同步", "REI", "强制同步"]'
);

-- 订单同步任务 场景 3：同步所有账户（包括未启用自动同步的）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`,
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '订单数据同步 - 全量同步',
  '同步所有账户的订单（包括未启用自动同步的账户），适用于批量处理场景',
  'order_sync',
  '0 0 4 * * 0',
  'python services/cron/tasks/order_sync/order_sync_task.py',
  '{"limit": 150, "skip_existing": true, "auto_sync_only": false}',
  'services/cron/tasks/order_sync/logs/task.log',
  'disabled',
  2400,
  1,
  '["admin@example.com", "business@example.com"]',
  1,
  4,
  '["订单", "同步", "REI", "全量同步"]'
);

-- 订单状态更新任务
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`,
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '订单状态自动更新',
  '每2小时从 REI API 获取订单最新状态并更新到数据库，包括订单状态、物流信息等',
  'order_status_update',
  '0 0 */2 * * *',
  'python services/cron/tasks/order_status_update/order_status_update_task.py',
  '{"limit": 100}',
  'services/cron/tasks/order_status_update/logs/task.log',
  'disabled',
  1800,
  1,
  '["admin@example.com", "business@example.com"]',
  1,
  5,
  '["订单", "状态更新", "REI", "API"]'
);

-- 订单状态更新任务（仅活跃订单）
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`,
  `log_file_path`,
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '订单状态更新（仅活跃订单）',
  '每30分钟从 REI API 获取活跃订单的最新状态，跳过已签收（0006）和取消发货（0001）的订单',
  'order_status_update',
  '0 */30 * * * *',
  'python services/cron/tasks/order_status_update_active/order_status_update_active_task.py',
  '{"limit": 100}',
  'services/cron/tasks/order_status_update_active/logs/task.log',
  'disabled',
  1800,
  1,
  '["admin@example.com", "business@example.com"]',
  1,
  6,
  '["订单", "状态更新", "REI", "API", "活跃订单"]'
);

-- 清理日志任务
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`, 
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '清理日志任务',
  '每天凌晨3点清理30天前的任务执行日志和软删除的数据，释放数据库空间',
  'cleanup',
  '0 0 3 * * *',
  'python /app/scripts/cleanup_logs.py',
  '{"retention_days": 30, "cleanup_soft_deleted": true, "cleanup_logs": true}',
  'disabled',
  600,
  1,
  '["admin@example.com"]',
  1,
  5,
  '["清理", "日志", "维护"]'
);

-- 数据库备份任务
INSERT INTO `cron_tasks` (
  `name`, 
  `description`, 
  `type`, 
  `cron_expression`, 
  `command`, 
  `parameters`, 
  `status`, 
  `timeout_seconds`, 
  `notify_on_failure`, 
  `notification_emails`,
  `created_by`,
  `priority`,
  `tags`
) VALUES (
  '数据库备份',
  '每天凌晨2点自动备份数据库，保留最近7天的备份文件',
  'backup',
  '0 0 2 * * *',
  'python /app/scripts/backup_database.py',
  '{"backup_path": "/backups", "retention_days": 7, "compress": true}',
  'disabled',
  1800,
  1,
  '["admin@example.com", "ops@example.com"]',
  1,
  1,
  '["备份", "数据库", "运维"]'
);

-- ============================================
-- 插入一些执行日志示例数据
-- ============================================

-- 邮件同步任务的执行日志
INSERT INTO `cron_task_logs` (
  `task_id`,
  `task_name`,
  `execution_id`,
  `status`,
  `trigger_type`,
  `started_at`,
  `finished_at`,
  `duration_ms`,
  `exit_code`,
  `output`,
  `server_hostname`,
  `server_ip`
) VALUES 
(1, '邮件同步任务', 'exec_001_20241115_001', 'success', 'scheduled', '2024-11-15 14:00:00', '2024-11-15 14:02:30', 150000, 0, '成功同步了85封邮件', 'mail-server-01', '192.168.1.100'),
(1, '邮件同步任务', 'exec_001_20241115_002', 'success', 'scheduled', '2024-11-15 14:05:00', '2024-11-15 14:06:45', 105000, 0, '成功同步了42封邮件', 'mail-server-01', '192.168.1.100');

-- 订单同步任务的执行日志
INSERT INTO `cron_task_logs` (
  `task_id`,
  `task_name`,
  `execution_id`,
  `status`,
  `trigger_type`,
  `started_at`,
  `finished_at`,
  `duration_ms`,
  `exit_code`,
  `output`,
  `server_hostname`,
  `server_ip`
) VALUES 
(2, '订单数据同步', 'exec_002_20241115_001', 'success', 'scheduled', '2024-11-15 12:00:00', '2024-11-15 12:15:30', 930000, 0, '成功同步了256个订单，更新了128个物流状态', 'order-server-01', '192.168.1.101'),
(2, '订单数据同步', 'exec_002_20241115_002', 'error', 'scheduled', '2024-11-15 14:00:00', '2024-11-15 14:05:15', 315000, 1, '同步过程中发生网络超时', 'order-server-01', '192.168.1.101');

-- ============================================
-- 更新任务统计信息
-- ============================================

-- 更新邮件同步任务的统计
UPDATE `cron_tasks` SET 
  `run_count` = 2,
  `success_count` = 2,
  `error_count` = 0,
  `last_run_at` = '2024-11-15 14:05:00',
  `last_success_at` = '2024-11-15 14:05:00',
  `next_run_at` = '2024-11-15 14:10:00'
WHERE `id` = 1;

-- 更新订单同步任务的统计
UPDATE `cron_tasks` SET 
  `run_count` = 2,
  `success_count` = 1,
  `error_count` = 1,
  `last_run_at` = '2024-11-15 14:00:00',
  `last_success_at` = '2024-11-15 12:00:00',
  `last_error_at` = '2024-11-15 14:00:00',
  `next_run_at` = '2024-11-15 16:00:00'
WHERE `id` = 2;

-- ============================================
-- 创建视图：定时任务概览
-- ============================================

CREATE OR REPLACE VIEW `v_cron_tasks_overview` AS
SELECT 
  t.`id`,
  t.`name`,
  t.`description`,
  t.`type`,
  t.`cron_expression`,
  t.`status`,
  t.`is_active`,
  t.`run_count`,
  t.`success_count`,
  t.`error_count`,
  CASE 
    WHEN t.`run_count` > 0 THEN ROUND((t.`success_count` / t.`run_count`) * 100, 2)
    ELSE 0
  END AS `success_rate_percent`,
  t.`last_run_at`,
  t.`last_success_at`,
  t.`last_error_at`,
  t.`next_run_at`,
  t.`priority`,
  t.`created_at`,
  a.`username` AS `created_by_username`,
  -- 最近一次执行状态
  (SELECT l.`status` FROM `cron_task_logs` l WHERE l.`task_id` = t.`id` ORDER BY l.`started_at` DESC LIMIT 1) AS `last_execution_status`,
  -- 最近一次执行耗时
  (SELECT l.`duration_ms` FROM `cron_task_logs` l WHERE l.`task_id` = t.`id` ORDER BY l.`started_at` DESC LIMIT 1) AS `last_execution_duration_ms`
FROM `cron_tasks` t
LEFT JOIN `admins` a ON t.`created_by` = a.`id`
WHERE t.`deleted_at` IS NULL
ORDER BY t.`priority` ASC, t.`created_at` DESC;

-- ============================================
-- 创建索引优化查询性能
-- ============================================

-- 为日志表创建复合索引，优化常用查询
CREATE INDEX `idx_cron_task_logs_task_status_time` ON `cron_task_logs` (`task_id`, `status`, `started_at`);
CREATE INDEX `idx_cron_task_logs_status_time` ON `cron_task_logs` (`status`, `started_at`);
