-- ============================================
-- SMTP 账户配置表
-- 支持多平台的SMTP邮箱配置存储
-- ============================================

CREATE TABLE IF NOT EXISTS `smtp_accounts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  
  -- 账户基本信息
  `email` VARCHAR(255) NOT NULL COMMENT '邮箱地址',
  `password` VARCHAR(500) NOT NULL COMMENT '邮箱密码或授权码（建议加密存储）',
  `nickname` VARCHAR(100) DEFAULT NULL COMMENT '账户昵称',
  `sender_name` VARCHAR(100) DEFAULT NULL COMMENT '发件人显示名称',
  
  -- SMTP服务器配置
  `platform` VARCHAR(50) NOT NULL COMMENT '邮箱平台（gmail/outlook/qq/163/126等）',
  `smtp_host` VARCHAR(255) NOT NULL COMMENT 'SMTP服务器地址',
  `smtp_port` INT NOT NULL DEFAULT 465 COMMENT 'SMTP端口号',
  `use_ssl` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否使用SSL（0:否 1:是）',
  `use_tls` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否使用TLS（0:否 1:是）',
  
  -- 状态和限制
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '账户状态（0:禁用 1:启用）',
  `daily_limit` INT DEFAULT 500 COMMENT '每日发送限制',
  `sent_today` INT DEFAULT 0 COMMENT '今日已发送数量',
  `last_send_time` DATETIME DEFAULT NULL COMMENT '上次发送时间',
  
  -- 发送设置
  `signature` TEXT DEFAULT NULL COMMENT '邮件签名',
  `reply_to` VARCHAR(255) DEFAULT NULL COMMENT '回复邮箱地址',
  `cc_default` VARCHAR(500) DEFAULT NULL COMMENT '默认抄送地址（多个用逗号分隔）',
  `bcc_default` VARCHAR(500) DEFAULT NULL COMMENT '默认密送地址（多个用逗号分隔）',
  
  -- 额外配置
  `priority` TINYINT(1) DEFAULT 3 COMMENT '优先级（1:高 3:正常 5:低）',
  `remark` TEXT DEFAULT NULL COMMENT '备注说明',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 索引
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_platform` (`platform`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SMTP账户配置表';

-- ============================================
-- 插入示例数据（可选）
-- ============================================

-- Gmail 示例（SSL端口465）
INSERT INTO `smtp_accounts` (`email`, `password`, `nickname`, `sender_name`, `platform`, `smtp_host`, `smtp_port`, `use_ssl`) 
VALUES 
('example@gmail.com', 'your_app_password', 'Gmail账户', '张三', 'gmail', 'smtp.gmail.com', 465, 1);

-- QQ邮箱 示例（SSL端口465）
INSERT INTO `smtp_accounts` (`email`, `password`, `nickname`, `sender_name`, `platform`, `smtp_host`, `smtp_port`, `use_ssl`) 
VALUES 
('example@qq.com', 'your_auth_code', 'QQ邮箱', '李四', 'qq', 'smtp.qq.com', 465, 1);

-- 163邮箱 示例（SSL端口465或TLS端口25）
INSERT INTO `smtp_accounts` (`email`, `password`, `nickname`, `sender_name`, `platform`, `smtp_host`, `smtp_port`, `use_ssl`) 
VALUES 
('example@163.com', 'your_auth_code', '163邮箱', '王五', '163', 'smtp.163.com', 465, 1);

-- Outlook 示例（TLS端口587）
INSERT INTO `smtp_accounts` (`email`, `password`, `nickname`, `sender_name`, `platform`, `smtp_host`, `smtp_port`, `use_ssl`, `use_tls`) 
VALUES 
('example@outlook.com', 'your_password', 'Outlook账户', '赵六', 'outlook', 'smtp.office365.com', 587, 0, 1);
