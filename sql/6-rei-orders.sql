-- ============================================
-- REI 订单管理表（完整版）
-- 基于REI API返回的JSON数据结构设计
-- 包含所有订单字段，使用JSON存储复杂嵌套数据
-- ============================================

CREATE TABLE IF NOT EXISTS `rei_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '订单记录ID',
    
    -- ========================================
    -- 一、订单基本信息（根层级）
    -- ========================================
    `order_id` VARCHAR(50) NOT NULL COMMENT '订单号（orderId）',
    `is_guest` BOOLEAN DEFAULT FALSE COMMENT '是否为游客订单（非会员）',
    `is_released` BOOLEAN DEFAULT FALSE COMMENT '订单是否已释放（可发货）',
    `order_type` VARCHAR(50) DEFAULT 'ONLINE' COMMENT '订单类型（如 ONLINE）',
    `order_date` DATETIME NOT NULL COMMENT '下单时间（ISO 8601 格式）',
    `is_complete` BOOLEAN DEFAULT FALSE COMMENT '订单是否已完成',
    `est_rewards_earned` DECIMAL(10,2) DEFAULT 0.00 COMMENT '预计获得的奖励积分金额',
    `has_dividend_refund` BOOLEAN DEFAULT FALSE COMMENT '是否有分红退款',
    `order_header_key` VARCHAR(100) DEFAULT NULL COMMENT '订单头唯一标识',
    `remorse_deadline` DATETIME DEFAULT NULL COMMENT '后悔期截止时间（可取消订单的时间）',
    `cancellability` VARCHAR(10) DEFAULT NULL COMMENT '是否可取消（E 可能表示可取消）',
    `retail_store_info` JSON DEFAULT NULL COMMENT '零售店信息（如为线下订单）',
    
    -- 金额信息
    `total_order_discount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '订单总折扣金额',
    `total_discounted_order_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '折扣后订单总金额',
    `total_tax_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '总税费',
    `total_shipping_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '总运费',
    `order_total` DECIMAL(10,2) DEFAULT 0.00 COMMENT '订单总金额',
    `amount_paid` DECIMAL(10,2) DEFAULT 0.00 COMMENT '已支付金额',
    
    -- ========================================
    -- 二、配送信息（fulfillmentGroups）- JSON存储
    -- ========================================
    `fulfillment_groups` JSON DEFAULT NULL COMMENT '配送组信息（JSON数组）- 仅由API数据填充
包含字段：
- deliveryType: 配送类型（DTC=直邮，CANCELED=已取消）
- storeId/storeName: 发货门店ID/名称
- shipTo: 收货地址信息
- originalEad: 原始预计送达时间
- currentEad: 当前预计送达时间
- pickupByDate: 自提截止时间
- carrier: 物流公司名称
- carrierMoniker: 物流公司代号
- trackingNumber: 物流追踪号
- trackingUrl: 物流追踪链接
- assemblyRequired: 是否需要组装
- carrierServiceCode: 物流服务代码
- hasDividendRefund: 配送组是否有分红退款
- status: 配送状态（statusDate, summaryStatusCode, detailStatusCode）
- fulfillmentItems: 商品列表（见下方商品字段说明）',
    
    -- ========================================
    -- 三、商品信息（fulfillmentItems）- 包含在fulfillmentGroups中
    -- ========================================
    -- 商品字段说明（JSON结构）：
    -- sku: 商品SKU
    -- name: 商品名称
    -- brand: 品牌
    -- url: 商品页面链接
    -- imageUrl: 商品图片链接
    -- color: 颜色
    -- size: 尺寸
    -- quantity: 数量
    -- status: 商品状态
    -- unitPrice: 单价
    -- discountedUnitPrice: 折扣后单价
    -- totalPrice: 商品总价
    -- totalDiscount: 商品总折扣
    -- reviewability: 是否可评价（Y/N/F）
    -- reviewUrl: 评价链接
    -- returnability: 是否可退货（Y/N/F）
    -- giftTo: 礼品收件人
    -- giftFrom: 礼品发件人
    -- hazardous: 是否为危险品
    -- returnWindow: 退货期限（天数）
    -- mediaType: 媒体类型
    -- discounts: 商品级别的折扣明细
    -- deliveryIssueWindow: 是否在配送问题处理期内
    -- dividendEligible: 是否可积分
    -- orderLineKey: 订单行唯一标识
    
    -- ========================================
    -- 四、支付信息（tenders）- JSON存储
    -- ========================================
    `tenders` JSON DEFAULT NULL COMMENT '支付信息（JSON数组）
包含字段：
- tenderType: 支付类型（Gift_Card=礼品卡，Dividend=分红）
- displaySvcNo: 显示的服务号（如卡号后四位）
- creditCardType: 信用卡类型
- amount: 支付金额',
    
    -- ========================================
    -- 五、其他信息
    -- ========================================
    `fees` JSON DEFAULT NULL COMMENT '附加费用',
    `shipping_charges` JSON DEFAULT NULL COMMENT '运费明细（JSON数组）',
    `discounts` JSON DEFAULT NULL COMMENT '折扣明细（JSON数组）',
    `billing_address` JSON DEFAULT NULL COMMENT '账单地址',
    
    -- ========================================
    -- 六、物流信息（从邮件解析）
    -- ========================================
    `tracking_info` JSON DEFAULT NULL COMMENT '物流信息（JSON数组）- 从邮件解析的配送信息
包含字段：
- shipTo: 收货地址信息（name, address, city, state, zipCode）
- deliveryType: 配送方式（如 "Standard shipping"）',
    `tracking_url` VARCHAR(500) DEFAULT NULL COMMENT '物流追踪URL（从邮件中的地址链接提取，通常是Google Maps链接）',
    
    -- ========================================
    -- 系统字段
    -- ========================================
    `account_id` INT DEFAULT NULL COMMENT '关联的IMAP账户ID（可选）',
    `email_id` INT DEFAULT NULL COMMENT '关联的邮件ID（可选）',
    `remark` TEXT DEFAULT NULL COMMENT '备注信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- ========================================
    -- 索引
    -- ========================================
    UNIQUE KEY `unique_order_id` (`order_id`) COMMENT '订单号唯一索引',
    INDEX `idx_order_date` (`order_date`) COMMENT '订单日期索引',
    INDEX `idx_is_complete` (`is_complete`) COMMENT '完成状态索引',
    INDEX `idx_order_header_key` (`order_header_key`) COMMENT '订单头标识索引',
    INDEX `idx_account_id` (`account_id`) COMMENT '账户ID索引',
    INDEX `idx_created_at` (`created_at`) COMMENT '创建时间索引',
    
    -- 外键约束（可选）
    FOREIGN KEY (`account_id`) REFERENCES `imap_accounts`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='REI订单管理表（完整版-基于API数据结构）';
