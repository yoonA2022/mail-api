-- ============================================
-- IMAP 账户配置表
-- 支持多平台的IMAP邮箱配置存储
-- ============================================

CREATE TABLE IF NOT EXISTS `imap_accounts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  
  -- 账户基本信息
  `user_id` INT DEFAULT NULL COMMENT '关联的用户ID（外键关联users表）',
  `email` VARCHAR(255) NOT NULL COMMENT '邮箱地址',
  `password` VARCHAR(500) NOT NULL COMMENT '邮箱密码或授权码（建议加密存储）',
  `nickname` VARCHAR(100) DEFAULT NULL COMMENT '账户昵称',
  
  -- IMAP服务器配置
  `platform` VARCHAR(50) NOT NULL COMMENT '邮箱平台（gmail/outlook/qq/163/126等）',
  `imap_host` VARCHAR(255) NOT NULL COMMENT 'IMAP服务器地址',
  `imap_port` INT NOT NULL DEFAULT 993 COMMENT 'IMAP端口号',
  `use_ssl` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否使用SSL（0:否 1:是）',
  
  -- 状态和设置
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '账户状态（0:禁用 1:启用）',
  `auto_sync` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否自动同步（0:否 1:是）',
  `last_sync_time` DATETIME DEFAULT NULL COMMENT '上次同步时间',
  
  -- 额外配置
  `folder` VARCHAR(100) DEFAULT 'INBOX' COMMENT '默认同步的邮件文件夹',
  `max_fetch` INT DEFAULT 50 COMMENT '每次最多获取邮件数',
  `remark` TEXT DEFAULT NULL COMMENT '备注说明',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 索引
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_platform` (`platform`),
  KEY `idx_status` (`status`),
  KEY `idx_user_id` (`user_id`),
  
  -- 外键约束
  CONSTRAINT `fk_imap_accounts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='IMAP账户配置表';

-- ============================================
-- 插入示例数据（可选）
-- ============================================

-- Gmail 示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'example@gmail.com', 'your_app_password', 'Gmail账户', 'gmail', 'imap.gmail.com', 993, 1, 1);

-- QQ邮箱 示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'example@qq.com', 'your_auth_code', 'QQ邮箱', 'qq', 'imap.qq.com', 993, 1, 0);

-- 163邮箱 示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'example@163.com', 'your_auth_code', '163邮箱', '163', 'imap.163.com', 993, 1, 0);

-- Outlook 示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'example@outlook.com', 'your_password', 'Outlook账户', 'outlook', 'outlook.office365.com', 993, 1, 1);

-- 126邮箱 示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'hi@example.com', 'your_auth_code', '126邮箱', 'imap', 'example.com', 993, 1, 0);

-- 邮箱示例
INSERT INTO `imap_accounts` (`user_id`, `email`, `password`, `nickname`, `platform`, `imap_host`, `imap_port`, `use_ssl`, `status`) 
VALUES 
(1,'example@126.com', 'your_auth_code', '126邮箱', '126', 'imap.126.com', 993, 1, 0);
