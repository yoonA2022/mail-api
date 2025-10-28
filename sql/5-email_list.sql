-- ============================================
-- 邮件列表表
-- 用于存储邮件元数据（不含正文和附件）
-- 支持多邮箱账户
-- 注意：正文和附件不存储在服务器，需要时从IMAP服务器实时获取
-- ============================================

CREATE TABLE IF NOT EXISTS `email_list` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '邮件记录ID',
    `account_id` INT NOT NULL COMMENT 'IMAP账户ID（关联imap_accounts表）',
    `uid` VARCHAR(255) NOT NULL COMMENT '邮件UID（邮箱服务器唯一标识）',
    `message_id` VARCHAR(500) DEFAULT NULL COMMENT '邮件Message-ID',
    
    -- 邮件基本信息
    `subject` VARCHAR(1000) DEFAULT NULL COMMENT '邮件主题',
    `from_email` VARCHAR(255) DEFAULT NULL COMMENT '发件人邮箱',
    `from_name` VARCHAR(255) DEFAULT NULL COMMENT '发件人名称',
    `to_emails` TEXT DEFAULT NULL COMMENT '收件人列表（JSON格式）',
    `cc_emails` TEXT DEFAULT NULL COMMENT '抄送列表（JSON格式）',
    `bcc_emails` TEXT DEFAULT NULL COMMENT '密送列表（JSON格式）',
    
    -- 邮件状态
    `date` DATETIME DEFAULT NULL COMMENT '邮件发送时间',
    `size` INT DEFAULT 0 COMMENT '邮件大小（字节）',
    `flags` VARCHAR(500) DEFAULT NULL COMMENT '邮件标记（JSON格式，如已读、星标等）',
    `has_attachments` TINYINT(1) DEFAULT 0 COMMENT '是否有附件（0:无 1:有）',
    `attachment_count` INT DEFAULT 0 COMMENT '附件数量',
    `attachment_names` TEXT DEFAULT NULL COMMENT '附件文件名列表（JSON格式）',
    
    -- 邮件预览
    `text_preview` TEXT DEFAULT NULL COMMENT '纯文本预览（前500字符）',
    `is_html` TINYINT(1) DEFAULT 0 COMMENT '是否包含HTML内容（0:否 1:是）',
    
    -- 邮件文件夹
    `folder` VARCHAR(255) DEFAULT 'INBOX' COMMENT '所属文件夹',
    
    -- 时间戳
    `synced_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    UNIQUE KEY `unique_account_uid` (`account_id`, `uid`) COMMENT '账户+UID唯一索引',
    INDEX `idx_account_id` (`account_id`) COMMENT '账户ID索引',
    INDEX `idx_date` (`date`) COMMENT '日期索引',
    INDEX `idx_from_email` (`from_email`) COMMENT '发件人索引',
    INDEX `idx_folder` (`folder`) COMMENT '文件夹索引',
    INDEX `idx_has_attachments` (`has_attachments`) COMMENT '附件标记索引',
    INDEX `idx_synced_at` (`synced_at`) COMMENT '同步时间索引',
    
    -- 外键约束
    FOREIGN KEY (`account_id`) REFERENCES `imap_accounts`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮件列表表（元数据，不存储正文和附件）';


-- ============================================
-- 邮件同步日志表
-- 记录每次同步的状态和结果
-- ============================================

CREATE TABLE IF NOT EXISTS `email_sync_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    `account_id` INT NOT NULL COMMENT 'IMAP账户ID',
    `folder` VARCHAR(255) DEFAULT 'INBOX' COMMENT '同步的文件夹',
    
    -- 同步统计
    `total_emails` INT DEFAULT 0 COMMENT '服务器总邮件数',
    `new_emails` INT DEFAULT 0 COMMENT '新增邮件数',
    `updated_emails` INT DEFAULT 0 COMMENT '更新邮件数',
    `deleted_emails` INT DEFAULT 0 COMMENT '删除邮件数',
    
    -- 同步状态
    `status` ENUM('running', 'success', 'failed', 'partial') DEFAULT 'running' COMMENT '同步状态',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    
    -- 时间统计
    `start_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
    `duration` DECIMAL(10,2) DEFAULT 0 COMMENT '耗时（秒）',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_account_id` (`account_id`) COMMENT '账户ID索引',
    INDEX `idx_status` (`status`) COMMENT '状态索引',
    INDEX `idx_start_time` (`start_time`) COMMENT '开始时间索引',
    
    -- 外键约束
    FOREIGN KEY (`account_id`) REFERENCES `imap_accounts`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮件同步日志表';


-- ============================================
-- 插入示例数据（可选）
-- ============================================

-- 注意：这里不插入示例数据，因为邮件列表需要从实际邮箱同步
