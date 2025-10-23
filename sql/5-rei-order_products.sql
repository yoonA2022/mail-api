-- ============================================
-- REI 订单商品详情表
-- 用于规范化存储订单商品信息
-- 如果需要更好的查询性能和商品维度分析，可以使用此表
-- 注意：这是可选表，订单主表(rei_orders)已使用JSON存储商品信息
-- ============================================

CREATE TABLE IF NOT EXISTS `rei_order_products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '商品记录ID',
    `order_id` INT NOT NULL COMMENT '订单ID（关联rei_orders表）',
    
    -- 商品信息
    `product_id` VARCHAR(50) NOT NULL COMMENT '商品编号',
    `product_nickname` VARCHAR(500) NOT NULL COMMENT '商品昵称/名称',
    `color` VARCHAR(100) DEFAULT NULL COMMENT '商品颜色',
    `size` VARCHAR(50) DEFAULT NULL COMMENT '商品尺寸',
    `quantity` INT NOT NULL DEFAULT 1 COMMENT '购买数量',
    `unit_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '单价',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_order_id` (`order_id`) COMMENT '订单ID索引',
    INDEX `idx_product_id` (`product_id`) COMMENT '商品ID索引',
    INDEX `idx_created_at` (`created_at`) COMMENT '创建时间索引',
    
    -- 外键约束
    FOREIGN KEY (`order_id`) REFERENCES `rei_orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='REI订单商品详情表（规范化设计）';


-- ============================================
-- 插入示例数据
-- ============================================

-- 获取订单ID并插入商品详情
INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '248404', 'Arc\'teryx Atom SL Insulated Hoody - Women\'s', 'Arctic Silk', 'XL', 1, 139.83
FROM `rei_orders` WHERE `order_number` = 'A385267303';

INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '123456', 'REI Co-op Trail 25 Pack', 'Black', 'One Size', 1, 316.00
FROM `rei_orders` WHERE `order_number` = 'B123456789';

INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '789012', 'Patagonia Down Sweater', 'Navy Blue', 'M', 1, 242.00
FROM `rei_orders` WHERE `order_number` = 'C987654321';

INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '345678', 'The North Face Tent', 'Green', '4-Person', 1, 837.00
FROM `rei_orders` WHERE `order_number` = 'D456789012';

INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '901234', 'Mountain Hardwear Sleeping Bag', 'Red', 'Long', 1, 874.00
FROM `rei_orders` WHERE `order_number` = 'E234567890';

INSERT INTO `rei_order_products` (`order_id`, `product_id`, `product_nickname`, `color`, `size`, `quantity`, `unit_price`)
SELECT id, '567890', 'Columbia Rain Jacket', 'Yellow', 'L', 1, 721.00
FROM `rei_orders` WHERE `order_number` = 'F567890123';


-- ============================================
-- 常用查询示例
-- ============================================

-- 1. 查询订单及其所有商品详情
-- SELECT 
--     o.order_number, 
--     o.order_date, 
--     o.status,
--     op.product_nickname, 
--     op.color, 
--     op.size, 
--     op.quantity, 
--     op.unit_price
-- FROM rei_orders o
-- LEFT JOIN rei_order_products op ON o.id = op.order_id
-- WHERE o.order_number = 'A385267303';

-- 2. 查询特定商品的所有订单
-- SELECT 
--     o.order_number,
--     o.order_date,
--     o.email,
--     op.product_nickname,
--     op.quantity,
--     op.unit_price
-- FROM rei_order_products op
-- JOIN rei_orders o ON op.order_id = o.id
-- WHERE op.product_id = '248404'
-- ORDER BY o.order_date DESC;

-- 3. 按商品统计销售数量
-- SELECT 
--     product_id,
--     product_nickname,
--     SUM(quantity) as total_quantity,
--     COUNT(DISTINCT order_id) as order_count,
--     SUM(quantity * unit_price) as total_revenue
-- FROM rei_order_products
-- GROUP BY product_id, product_nickname
-- ORDER BY total_revenue DESC;

-- 4. 查询包含多件商品的订单
-- SELECT 
--     o.order_number,
--     o.order_date,
--     COUNT(op.id) as product_count,
--     SUM(op.quantity * op.unit_price) as products_total
-- FROM rei_orders o
-- LEFT JOIN rei_order_products op ON o.id = op.order_id
-- GROUP BY o.id, o.order_number, o.order_date
-- HAVING product_count > 1
-- ORDER BY o.order_date DESC;

-- 5. 查询特定颜色/尺寸的商品销售情况
-- SELECT 
--     product_nickname,
--     color,
--     size,
--     COUNT(*) as order_count,
--     SUM(quantity) as total_sold
-- FROM rei_order_products
-- WHERE color = 'Arctic Silk'
-- GROUP BY product_nickname, color, size;

