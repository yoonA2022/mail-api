-- ============================================
-- 管理员表
-- 用于管理系统管理员账号
-- ============================================

CREATE TABLE IF NOT EXISTS `admins` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  
  -- 管理员基本信息
  `username` VARCHAR(50) NOT NULL COMMENT '用户名（登录用）',
  `email` VARCHAR(255) DEFAULT NULL COMMENT '管理员邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
  
  -- 管理员资料
  `nickname` VARCHAR(100) DEFAULT NULL COMMENT '昵称',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
  `real_name` VARCHAR(100) DEFAULT NULL COMMENT '真实姓名',
  `gender` TINYINT(1) DEFAULT NULL COMMENT '性别（0:女 1:男 2:其他）',
  `department` VARCHAR(100) DEFAULT NULL COMMENT '所属部门',
  `position` VARCHAR(100) DEFAULT NULL COMMENT '职位',
  
  -- 账户状态
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '账户状态（0:禁用 1:正常 2:锁定）',
  `is_verified` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已验证（0:否 1:是）',
  `verified_at` DATETIME DEFAULT NULL COMMENT '验证时间',
  
  -- 角色和权限
  `role` VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '管理员角色（super_admin:超级管理员 admin:管理员 operator:操作员）',
  `permissions` JSON DEFAULT NULL COMMENT '管理员权限（JSON格式）',
  `permission_groups` JSON DEFAULT NULL COMMENT '权限组（JSON格式）',
  
  -- 登录信息
  `last_login_at` DATETIME DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP',
  `login_count` INT NOT NULL DEFAULT 0 COMMENT '登录次数',
  
  -- 安全设置
  `two_factor_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用两步验证（0:否 1:是，管理员默认开启）',
  `two_factor_secret` VARCHAR(255) DEFAULT NULL COMMENT '两步验证密钥',
  `password_expires_at` DATETIME DEFAULT NULL COMMENT '密码过期时间',
  `must_change_password` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否必须修改密码（0:否 1:是）',
  
  -- 管理员特有字段
  `is_super_admin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为超级管理员（0:否 1:是）',
  `created_by` INT DEFAULT NULL COMMENT '创建者ID',
  `approved_by` INT DEFAULT NULL COMMENT '审批者ID',
  `approved_at` DATETIME DEFAULT NULL COMMENT '审批时间',
  
  -- 其他信息
  `remark` TEXT DEFAULT NULL COMMENT '备注说明',
  `preferences` JSON DEFAULT NULL COMMENT '管理员偏好设置（JSON格式）',
  
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
  KEY `idx_is_super_admin` (`is_super_admin`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_deleted_at` (`deleted_at`),
  KEY `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员表';

-- ============================================
-- 插入示例数据（可选）
-- ============================================

-- 超级管理员账户
INSERT INTO `admins` (`username`, `email`, `password`, `nickname`, `avatar`, `real_name`, `role`, `is_super_admin`, `status`, `is_verified`, `two_factor_enabled`) 
VALUES 
('superadmin', 'superadmin@example.com', '$2b$12$fF/vYSdmKJXKTcKc9GWrVeD4iTNYfA/6snQKSinlsyIZeiilTFV/G', '超级管理员', '/assets/images/avatars/shadcn.png', '系统管理员', 'super_admin', 1, 1, 1, 1);
-- 默认密码: admin123 (请在生产环境中修改)

-- 普通管理员示例
INSERT INTO `admins` (`username`, `email`, `password`, `nickname`, `avatar`, `real_name`, `department`, `position`, `role`, `status`, `is_verified`, `created_by`) 
VALUES 
('admin001', 'admin001@example.com', '$2b$12$fF/vYSdmKJXKTcKc9GWrVeD4iTNYfA/6snQKSinlsyIZeiilTFV/G', '管理员001', '/assets/images/avatars/shadcn.png', '张三', '技术部', '系统管理员', 'admin', 1, 1, 1);
-- 默认密码: admin123

-- 操作员示例
INSERT INTO `admins` (`username`, `email`, `password`, `nickname`, `avatar`, `real_name`, `department`, `position`, `role`, `status`, `is_verified`, `created_by`) 
VALUES 
('operator001', 'operator001@example.com', '$2b$12$fF/vYSdmKJXKTcKc9GWrVeD4iTNYfA/6snQKSinlsyIZeiilTFV/G', '操作员001', '/assets/images/avatars/shadcn.png', '李四', '运营部', '运营专员', 'operator', 1, 1, 1);
-- 默认密码: admin123

-- ============================================
-- 创建管理员会话表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS `admin_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `admin_id` INT NOT NULL COMMENT '管理员ID',
  `token` VARCHAR(500) NOT NULL COMMENT '会话令牌（JWT或其他）',
  `refresh_token` VARCHAR(500) DEFAULT NULL COMMENT '刷新令牌',
  `device_info` JSON DEFAULT NULL COMMENT '设备信息（JSON格式）',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
  `expires_at` DATETIME NOT NULL COMMENT '过期时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  -- 索引
  UNIQUE KEY `uk_token` (`token`),
  KEY `idx_admin_id` (`admin_id`),
  KEY `idx_expires_at` (`expires_at`),
  
  -- 外键约束
  CONSTRAINT `fk_admin_sessions_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员会话表';

-- ============================================
-- 创建管理员登录日志表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS `admin_login_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `admin_id` INT NOT NULL COMMENT '管理员ID',
  `login_type` VARCHAR(50) NOT NULL COMMENT '登录类型（password:密码登录 two_factor:两步验证登录）',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
  `device_info` JSON DEFAULT NULL COMMENT '设备信息',
  `location` VARCHAR(255) DEFAULT NULL COMMENT '登录地点',
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '登录状态（0:失败 1:成功）',
  `failure_reason` VARCHAR(255) DEFAULT NULL COMMENT '失败原因',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
  
  -- 索引
  KEY `idx_admin_id` (`admin_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  
  -- 外键约束
  CONSTRAINT `fk_admin_login_logs_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员登录日志表';

-- ============================================
-- 创建管理员操作日志表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS `admin_operation_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `admin_id` INT NOT NULL COMMENT '管理员ID',
  `admin_username` VARCHAR(50) NOT NULL COMMENT '管理员用户名',
  `module` VARCHAR(100) NOT NULL COMMENT '操作模块',
  `action` VARCHAR(100) NOT NULL COMMENT '操作动作',
  `description` TEXT DEFAULT NULL COMMENT '操作描述',
  `request_method` VARCHAR(10) DEFAULT NULL COMMENT '请求方法（GET/POST/PUT/DELETE等）',
  `request_url` VARCHAR(500) DEFAULT NULL COMMENT '请求URL',
  `request_params` JSON DEFAULT NULL COMMENT '请求参数（JSON格式）',
  `response_status` INT DEFAULT NULL COMMENT '响应状态码',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
  `execution_time` INT DEFAULT NULL COMMENT '执行时间（毫秒）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  
  -- 索引
  KEY `idx_admin_id` (`admin_id`),
  KEY `idx_module` (`module`),
  KEY `idx_action` (`action`),
  KEY `idx_created_at` (`created_at`),
  
  -- 外键约束
  CONSTRAINT `fk_admin_operation_logs_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员操作日志表';
