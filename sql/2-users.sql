-- ============================================
-- 用户表
-- 用于管理系统用户账号
-- ============================================

CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  
  -- 用户基本信息
  `username` VARCHAR(50) NOT NULL COMMENT '用户名（登录用）',
  `email` VARCHAR(255) DEFAULT NULL COMMENT '用户邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
  
  -- 用户资料
  `nickname` VARCHAR(100) DEFAULT NULL COMMENT '昵称',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
  `real_name` VARCHAR(100) DEFAULT NULL COMMENT '真实姓名',
  `gender` TINYINT(1) DEFAULT NULL COMMENT '性别（0:女 1:男 2:其他）',
  `birthday` DATE DEFAULT NULL COMMENT '生日',
  
  -- 账户状态
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '账户状态（0:禁用 1:正常 2:锁定）',
  `is_verified` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已验证（0:否 1:是）',
  `verified_at` DATETIME DEFAULT NULL COMMENT '验证时间',
  
  -- 角色和权限
  `role` VARCHAR(50) NOT NULL DEFAULT 'user' COMMENT '用户角色（admin:管理员 user:普通用户 vip:VIP用户）',
  `permissions` JSON DEFAULT NULL COMMENT '用户权限（JSON格式）',
  
  -- 登录信息
  `last_login_at` DATETIME DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP',
  `login_count` INT NOT NULL DEFAULT 0 COMMENT '登录次数',
  
  -- 安全设置
  `two_factor_enabled` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否启用两步验证（0:否 1:是）',
  `two_factor_secret` VARCHAR(255) DEFAULT NULL COMMENT '两步验证密钥',
  
  -- 其他信息
  `bio` TEXT DEFAULT NULL COMMENT '个人简介',
  `preferences` JSON DEFAULT NULL COMMENT '用户偏好设置（JSON格式）',
  `remark` TEXT DEFAULT NULL COMMENT '备注说明',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '删除时间（软删除）',
  
  -- 索引
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_phone` (`phone`),
  KEY `idx_status` (`status`),
  KEY `idx_role` (`role`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 插入示例数据（可选）
-- ============================================

-- 管理员账户
INSERT INTO `users` (`username`, `email`, `password`, `nickname`, `role`, `status`, `is_verified`) 
VALUES 
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2', '系统管理员', 'admin', 1, 1);
-- 默认密码: admin123 (请在生产环境中修改)

-- 普通用户示例
INSERT INTO `users` (`username`, `email`, `password`, `nickname`, `role`, `status`, `is_verified`) 
VALUES 
('user001', 'user001@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2', '测试用户', 'user', 1, 1);
-- 默认密码: user123

-- VIP用户示例
INSERT INTO `users` (`username`, `email`, `password`, `nickname`, `role`, `status`, `is_verified`) 
VALUES 
('vip001', 'vip001@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2', 'VIP用户', 'vip', 1, 1);
-- 默认密码: vip123

-- ============================================
-- 创建用户会话表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `token` VARCHAR(500) NOT NULL COMMENT '会话令牌（JWT或其他）',
  `refresh_token` VARCHAR(500) DEFAULT NULL COMMENT '刷新令牌',
  `device_info` JSON DEFAULT NULL COMMENT '设备信息（JSON格式）',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
  `expires_at` DATETIME NOT NULL COMMENT '过期时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  -- 索引
  UNIQUE KEY `uk_token` (`token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_expires_at` (`expires_at`),
  
  -- 外键约束
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- ============================================
-- 创建用户登录日志表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS `user_login_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `login_type` VARCHAR(50) NOT NULL COMMENT '登录类型（password:密码登录 oauth:第三方登录 sms:短信登录）',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
  `device_info` JSON DEFAULT NULL COMMENT '设备信息',
  `location` VARCHAR(255) DEFAULT NULL COMMENT '登录地点',
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '登录状态（0:失败 1:成功）',
  `failure_reason` VARCHAR(255) DEFAULT NULL COMMENT '失败原因',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
  
  -- 索引
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  
  -- 外键约束
  CONSTRAINT `fk_login_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户登录日志表';
