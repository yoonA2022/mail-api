-- ============================================
-- REI 订单管理表
-- 用于存储REI订单的完整信息
-- 包括订单基本信息、收货地址、账单地址、商品和付款详情
-- ============================================

CREATE TABLE IF NOT EXISTS `rei_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '订单记录ID',
    `order_number` VARCHAR(50) NOT NULL COMMENT 'REI订单号',
    
    -- 订单基本信息
    `order_date` DATE NOT NULL COMMENT '订单日期',
    `email` VARCHAR(255) NOT NULL COMMENT '客户邮箱',
    `status` ENUM('pending', 'processing', 'success', 'failed') DEFAULT 'pending' COMMENT '订单状态',
    `estimated_arrival` VARCHAR(50) DEFAULT NULL COMMENT '预计到达时间',
    
    -- 金额信息（单位：美元）
    `amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '订单总金额',
    `subtotal` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '商品小计',
    `shipping_fee` DECIMAL(10,2) DEFAULT 0.00 COMMENT '运费',
    `tax` DECIMAL(10,2) DEFAULT 0.00 COMMENT '税费',
    `total` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '订单总计',
    `paid` DECIMAL(10,2) DEFAULT 0.00 COMMENT '已支付金额',
    
    -- 收货地址
    `shipping_name` VARCHAR(100) NOT NULL COMMENT '收货人姓名',
    `shipping_address` VARCHAR(500) NOT NULL COMMENT '收货地址',
    `shipping_city` VARCHAR(100) NOT NULL COMMENT '收货城市',
    `shipping_state` VARCHAR(50) NOT NULL COMMENT '收货州/省',
    `shipping_zip_code` VARCHAR(20) NOT NULL COMMENT '收货邮编',
    `shipping_method` VARCHAR(100) DEFAULT 'Standard shipping' COMMENT '配送方式',
    
    -- 账单地址
    `billing_name` VARCHAR(100) NOT NULL COMMENT '账单姓名',
    `billing_address` VARCHAR(500) NOT NULL COMMENT '账单地址',
    `billing_city` VARCHAR(100) NOT NULL COMMENT '账单城市',
    `billing_state` VARCHAR(50) NOT NULL COMMENT '账单州/省',
    `billing_zip_code` VARCHAR(20) NOT NULL COMMENT '账单邮编',
    
    -- 商品信息（JSON格式存储）
    `products` JSON NOT NULL COMMENT '商品列表（JSON数组）',
    
    -- 付款信息（JSON格式存储礼品卡列表）
    `gift_cards` JSON DEFAULT NULL COMMENT '礼品卡列表（JSON数组）',
    
    -- 关联信息
    `account_id` INT DEFAULT NULL COMMENT '关联的IMAP账户ID（可选）',
    `email_id` INT DEFAULT NULL COMMENT '关联的邮件ID（可选）',
    
    -- 备注
    `remark` TEXT DEFAULT NULL COMMENT '备注信息',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    UNIQUE KEY `unique_order_number` (`order_number`) COMMENT '订单号唯一索引',
    INDEX `idx_email` (`email`) COMMENT '邮箱索引',
    INDEX `idx_order_date` (`order_date`) COMMENT '订单日期索引',
    INDEX `idx_status` (`status`) COMMENT '状态索引',
    INDEX `idx_account_id` (`account_id`) COMMENT '账户ID索引',
    INDEX `idx_created_at` (`created_at`) COMMENT '创建时间索引',
    
    -- 外键约束（可选，如果需要关联IMAP账户）
    FOREIGN KEY (`account_id`) REFERENCES `imap_accounts`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='REI订单管理表';


-- ============================================
-- 插入示例数据
-- ============================================

-- 订单1: A385267303 (成功订单，使用了礼品卡)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'A385267303', '2025-10-06', 'chazrick.branson@example.com', 'success', 'Fri, Oct 10',
    139.83, 139.83, 0.00, 0.00, 139.83, 0.00,
    'Zhaohua Lu', '6479 US HIGHWAY 93 S UNIT 987', 'WHITEFISH', 'MT', '59937', 'Standard shipping',
    'Chazrick Branson', '2135 Buena Vista Ave', 'San Leandro', 'CA', '94577',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'Arc\'teryx Atom SL Insulated Hoody - Women\'s',
            'productId', '248404',
            'color', 'Arctic Silk',
            'size', 'XL',
            'quantity', 1
        )
    ),
    JSON_ARRAY(27.46, 52.37, 60.00)
);

-- 订单2: B123456789 (成功订单)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'B123456789', '2025-10-05', 'ken99@example.com', 'success', 'Wed, Oct 09',
    316.00, 316.00, 0.00, 0.00, 316.00, 316.00,
    'Ken Smith', '123 Main Street', 'Seattle', 'WA', '98101', 'Standard shipping',
    'Ken Smith', '123 Main Street', 'Seattle', 'WA', '98101',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'REI Co-op Trail 25 Pack',
            'productId', '123456',
            'color', 'Black',
            'size', 'One Size',
            'quantity', 1
        )
    ),
    JSON_ARRAY()
);

-- 订单3: C987654321 (成功订单)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'C987654321', '2025-10-04', 'Abe45@example.com', 'success', 'Tue, Oct 08',
    242.00, 242.00, 0.00, 0.00, 242.00, 242.00,
    'Abe Johnson', '456 Oak Avenue', 'Portland', 'OR', '97201', 'Express shipping',
    'Abe Johnson', '456 Oak Avenue', 'Portland', 'OR', '97201',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'Patagonia Down Sweater',
            'productId', '789012',
            'color', 'Navy Blue',
            'size', 'M',
            'quantity', 1
        )
    ),
    JSON_ARRAY()
);

-- 订单4: D456789012 (处理中订单)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'D456789012', '2025-10-03', 'Monserrat44@example.com', 'processing', 'Mon, Oct 14',
    837.00, 837.00, 0.00, 0.00, 837.00, 837.00,
    'Monserrat Garcia', '789 Pine Road', 'Denver', 'CO', '80201', 'Standard shipping',
    'Monserrat Garcia', '789 Pine Road', 'Denver', 'CO', '80201',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'The North Face Tent',
            'productId', '345678',
            'color', 'Green',
            'size', '4-Person',
            'quantity', 1
        )
    ),
    JSON_ARRAY()
);

-- 订单5: E234567890 (成功订单)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'E234567890', '2025-10-02', 'Silas22@example.com', 'success', 'Sat, Oct 12',
    874.00, 874.00, 0.00, 0.00, 874.00, 874.00,
    'Silas Brown', '321 Elm Street', 'Austin', 'TX', '78701', 'Standard shipping',
    'Silas Brown', '321 Elm Street', 'Austin', 'TX', '78701',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'Mountain Hardwear Sleeping Bag',
            'productId', '901234',
            'color', 'Red',
            'size', 'Long',
            'quantity', 1
        )
    ),
    JSON_ARRAY()
);

-- 订单6: F567890123 (失败订单)
INSERT INTO `rei_orders` (
    `order_number`, `order_date`, `email`, `status`, `estimated_arrival`,
    `amount`, `subtotal`, `shipping_fee`, `tax`, `total`, `paid`,
    `shipping_name`, `shipping_address`, `shipping_city`, `shipping_state`, `shipping_zip_code`, `shipping_method`,
    `billing_name`, `billing_address`, `billing_city`, `billing_state`, `billing_zip_code`,
    `products`, `gift_cards`
) VALUES (
    'F567890123', '2025-10-01', 'carmella@example.com', 'failed', 'Thu, Oct 10',
    721.00, 721.00, 0.00, 0.00, 721.00, 0.00,
    'Carmella Wilson', '654 Maple Drive', 'Boston', 'MA', '02101', 'Express shipping',
    'Carmella Wilson', '654 Maple Drive', 'Boston', 'MA', '02101',
    JSON_ARRAY(
        JSON_OBJECT(
            'nickname', 'Columbia Rain Jacket',
            'productId', '567890',
            'color', 'Yellow',
            'size', 'L',
            'quantity', 1
        )
    ),
    JSON_ARRAY()
);


-- ============================================
-- 常用查询示例
-- ============================================

-- 1. 查询所有订单（包含JSON解析）
-- SELECT 
--     id, order_number, order_date, email, status, amount,
--     shipping_name, shipping_city, shipping_state,
--     JSON_EXTRACT(products, '$[0].nickname') as first_product_name,
--     JSON_LENGTH(gift_cards) as gift_card_count
-- FROM rei_orders
-- ORDER BY order_date DESC;

-- 2. 查询使用了礼品卡的订单
-- SELECT order_number, email, amount, gift_cards
-- FROM rei_orders
-- WHERE JSON_LENGTH(gift_cards) > 0;

-- 3. 按状态统计订单数量
-- SELECT status, COUNT(*) as count, SUM(amount) as total_amount
-- FROM rei_orders
-- GROUP BY status;

-- 4. 查询特定邮箱的所有订单
-- SELECT order_number, order_date, status, amount
-- FROM rei_orders
-- WHERE email = 'chazrick.branson@example.com'
-- ORDER BY order_date DESC;

-- 5. 查询订单详情（解析JSON商品信息）
-- SELECT 
--     order_number, 
--     order_date, 
--     status,
--     JSON_EXTRACT(products, '$[0].nickname') as product_name,
--     JSON_EXTRACT(products, '$[0].color') as product_color,
--     JSON_EXTRACT(products, '$[0].size') as product_size,
--     amount
-- FROM rei_orders
-- WHERE order_number = 'A385267303';

