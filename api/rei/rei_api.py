"""
REI 订单 API
提供REI订单数据的查询接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from config.database import get_db_connection
import json

router = APIRouter(prefix="/api/rei", tags=["REI订单"])


@router.get("/orders")
async def get_orders(
    account_id: Optional[int] = Query(None, description="邮箱账户ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=2000, description="每页数量"),
    status: Optional[str] = Query(None, description="订单状态筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取REI订单列表
    
    参数:
    - account_id: 邮箱账户ID（可选）
    - page: 页码，从1开始
    - page_size: 每页数量，默认10条
    - status: 订单状态筛选（可选）
    - start_date: 开始日期（可选）
    - end_date: 结束日期（可选）
    
    返回:
    - orders: 订单列表
    - total: 总订单数
    - page: 当前页码
    - page_size: 每页数量
    - total_pages: 总页数
    """
    
    try:
        # 获取数据库连接
        db = get_db_connection()
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if account_id is not None:
            where_conditions.append("account_id = %s")
            params.append(account_id)
        
        if start_date:
            where_conditions.append("order_date >= %s")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("order_date <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # 查询总数
        with db.get_cursor() as cursor:
            count_query = f"SELECT COUNT(*) as total FROM rei_orders WHERE {where_clause}"
            cursor.execute(count_query, params)
            total_result = cursor.fetchone()
            total = total_result['total'] if total_result else 0
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # 查询订单数据
        with db.get_cursor() as cursor:
            query = f"""
                SELECT 
                    id,
                    order_id,
                    is_guest,
                    is_released,
                    order_type,
                    order_date,
                    is_complete,
                    est_rewards_earned,
                    has_dividend_refund,
                    order_header_key,
                    remorse_deadline,
                    cancellability,
                    retail_store_info,
                    total_order_discount,
                    total_discounted_order_amount,
                    total_tax_amount,
                    total_shipping_amount,
                    order_total,
                    amount_paid,
                    fulfillment_groups,
                    tenders,
                    fees,
                    shipping_charges,
                    discounts,
                    billing_address,
                    tracking_info,
                    tracking_url,
                    account_id,
                    email_id,
                    remark,
                    created_at,
                    updated_at
                FROM rei_orders
                WHERE {where_clause}
                ORDER BY order_date DESC, created_at DESC
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, params + [page_size, offset])
            orders = cursor.fetchall()
        
        # 处理JSON字段
        for order in orders:
            # 解析JSON字段
            json_fields = [
                'retail_store_info', 'fulfillment_groups', 'tenders',
                'fees', 'shipping_charges', 'discounts', 'billing_address',
                'tracking_info'
            ]
            for field in json_fields:
                if order.get(field):
                    try:
                        order[field] = json.loads(order[field]) if isinstance(order[field], str) else order[field]
                    except:
                        order[field] = None
            
            # 转换日期时间为字符串
            if order.get('order_date'):
                order['order_date'] = order['order_date'].isoformat() if hasattr(order['order_date'], 'isoformat') else str(order['order_date'])
            if order.get('remorse_deadline'):
                order['remorse_deadline'] = order['remorse_deadline'].isoformat() if hasattr(order['remorse_deadline'], 'isoformat') else str(order['remorse_deadline'])
            if order.get('created_at'):
                order['created_at'] = order['created_at'].isoformat() if hasattr(order['created_at'], 'isoformat') else str(order['created_at'])
            if order.get('updated_at'):
                order['updated_at'] = order['updated_at'].isoformat() if hasattr(order['updated_at'], 'isoformat') else str(order['updated_at'])
        
        return {
            "success": True,
            "data": {
                "orders": orders,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        print(f"❌ 查询订单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询订单失败: {str(e)}")


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str):
    """
    获取单个订单详情
    
    参数:
    - order_id: 订单号
    
    返回:
    - 订单详细信息
    """
    
    try:
        # 获取数据库连接
        db = get_db_connection()
        
        # 查询订单
        with db.get_cursor() as cursor:
            query = """
                SELECT 
                    id,
                    order_id,
                    is_guest,
                    is_released,
                    order_type,
                    order_date,
                    is_complete,
                    est_rewards_earned,
                    has_dividend_refund,
                    order_header_key,
                    remorse_deadline,
                    cancellability,
                    retail_store_info,
                    total_order_discount,
                    total_discounted_order_amount,
                    total_tax_amount,
                    total_shipping_amount,
                    order_total,
                    amount_paid,
                    fulfillment_groups,
                    tenders,
                    fees,
                    shipping_charges,
                    discounts,
                    billing_address,
                    tracking_info,
                    tracking_url,
                    account_id,
                    email_id,
                    remark,
                    created_at,
                    updated_at
                FROM rei_orders
                WHERE order_id = %s
            """
            
            cursor.execute(query, (order_id,))
            order = cursor.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
        
        # 解析JSON字段
        json_fields = [
            'retail_store_info', 'fulfillment_groups', 'tenders',
            'fees', 'shipping_charges', 'discounts', 'billing_address',
            'tracking_info'
        ]
        for field in json_fields:
            if order.get(field):
                try:
                    order[field] = json.loads(order[field]) if isinstance(order[field], str) else order[field]
                except:
                    order[field] = None
        
        # 转换日期时间为字符串
        if order.get('order_date'):
            order['order_date'] = order['order_date'].isoformat() if hasattr(order['order_date'], 'isoformat') else str(order['order_date'])
        if order.get('remorse_deadline'):
            order['remorse_deadline'] = order['remorse_deadline'].isoformat() if hasattr(order['remorse_deadline'], 'isoformat') else str(order['remorse_deadline'])
        if order.get('created_at'):
            order['created_at'] = order['created_at'].isoformat() if hasattr(order['created_at'], 'isoformat') else str(order['created_at'])
        if order.get('updated_at'):
            order['updated_at'] = order['updated_at'].isoformat() if hasattr(order['updated_at'], 'isoformat') else str(order['updated_at'])
        
        return {
            "success": True,
            "data": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查询订单详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询订单详情失败: {str(e)}")


@router.get("/orders/stats/summary")
async def get_orders_summary(account_id: Optional[int] = Query(None, description="邮箱账户ID")):
    """
    获取订单统计摘要
    
    参数:
    - account_id: 邮箱账户ID（可选）
    
    返回:
    - 订单统计信息（总数、总金额等）
    """
    
    try:
        # 获取数据库连接
        db = get_db_connection()
        
        # 构建查询条件
        where_clause = "account_id = %s" if account_id is not None else "1=1"
        params = [account_id] if account_id is not None else []
        
        # 查询统计信息
        with db.get_cursor() as cursor:
            query = f"""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(order_total) as total_amount,
                    SUM(amount_paid) as total_paid,
                    COUNT(CASE WHEN is_complete = 1 THEN 1 END) as completed_orders,
                    COUNT(CASE WHEN is_complete = 0 THEN 1 END) as pending_orders
                FROM rei_orders
                WHERE {where_clause}
            """
            
            cursor.execute(query, params)
            stats = cursor.fetchone()
        
        return {
            "success": True,
            "data": {
                "total_orders": stats['total_orders'] or 0,
                "total_amount": float(stats['total_amount']) if stats['total_amount'] else 0.0,
                "total_paid": float(stats['total_paid']) if stats['total_paid'] else 0.0,
                "completed_orders": stats['completed_orders'] or 0,
                "pending_orders": stats['pending_orders'] or 0
            }
        }
        
    except Exception as e:
        print(f"❌ 查询订单统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询订单统计失败: {str(e)}")


@router.post("/orders/sync")
async def sync_orders(
    account_id: int = Query(..., description="邮箱账户ID"),
    limit: int = Query(100, ge=1, le=500, description="最多处理邮件数量"),
    skip_existing: bool = Query(True, description="是否跳过已存在的订单"),
    background: bool = Query(True, description="是否在后台执行")
):
    """
    同步指定邮箱账户的订单
    
    流程:
    1. 筛选 REI 订单邮件
    2. 从邮件中提取关键信息（订单号、姓名、邮编、地址）
    3. 调用 REI API 获取完整订单数据
    4. 合并邮件信息和 API 数据
    5. 保存到数据库
    
    参数:
    - account_id: 邮箱账户ID（必填）
    - limit: 最多处理多少封邮件（默认100）
    - skip_existing: 是否跳过已存在的订单（默认True）
    - background: 是否在后台执行（默认False）
    
    返回:
    - 如果 background=True，返回任务ID
    - 如果 background=False，返回同步结果统计
    """
    
    try:
        from services.rei.rei_order_sync_service_optimized import ReiOrderSyncServiceOptimized
        from services.rei.task_manager import get_task_manager
        
        print(f"\n{'='*60}")
        print(f"🚀 API: 开始同步订单 (后台模式: {background})")
        print(f"   账户ID: {account_id}")
        print(f"   邮件限制: {limit}")
        print(f"   跳过已存在: {skip_existing}")
        print(f"{'='*60}\n")
        
        if background:
            # 后台执行
            task_manager = get_task_manager()
            
            # 确保任务管理器已启动
            if not task_manager.is_running:
                await task_manager.start()
            
            # 创建后台任务
            task_id = task_manager.create_task(
                ReiOrderSyncServiceOptimized.sync_orders_for_account_async,
                account_id=account_id,
                limit=limit,
                skip_existing=skip_existing,
                task_name=f"同步订单 - 账户{account_id}"
            )
            
            return {
                "success": True,
                "message": "任务已创建，正在后台执行",
                "task_id": task_id,
                "background": True
            }
        else:
            # 前台执行（优化版本）
            result = await ReiOrderSyncServiceOptimized.sync_orders_for_account_async(
                account_id=account_id,
                limit=limit,
                skip_existing=skip_existing
            )
            
            if result.get('success'):
                return {
                    "success": True,
                    "message": result.get('message', '同步完成'),
                    "background": False,
                    "data": {
                        "account_id": account_id,
                        "emails_found": result.get('results', {}).get('emails_found', 0),
                        "orders_synced": result.get('results', {}).get('orders_synced', 0),
                        "orders_skipped": result.get('results', {}).get('orders_skipped', 0),
                        "orders_failed": result.get('results', {}).get('orders_failed', 0),
                        "synced_orders": result.get('results', {}).get('synced_orders', []),
                        "skipped_orders": result.get('results', {}).get('skipped_orders', []),
                        "failed_orders": result.get('results', {}).get('failed_orders', [])
                    }
                }
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=result.get('error', '同步订单失败')
                )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API: 同步订单失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"同步订单失败: {str(e)}")


@router.post("/orders/refresh-details")
async def refresh_order_details(
    account_id: int = Query(..., description="邮箱账户ID"),
    limit: int = Query(100, ge=1, le=500, description="最多处理订单数量"),
    background: bool = Query(True, description="是否在后台执行")
):
    """
    刷新指定邮箱账户的订单详情（步骤2）
    
    流程:
    1. 从数据库读取订单列表
    2. 提取账单姓名和邮编
    3. 调用 REI API 获取完整订单数据
    4. 更新到数据库
    
    参数:
    - account_id: 邮箱账户ID（必填）
    - limit: 最多处理多少个订单（默认100）
    - background: 是否在后台执行（默认False）
    
    返回:
    - 如果 background=True，返回任务ID
    - 如果 background=False，返回刷新结果统计
    """
    
    try:
        from services.rei.rei_order_sync_service_optimized import ReiOrderSyncServiceOptimized
        from services.rei.task_manager import get_task_manager
        
        print(f"\n{'='*60}")
        print(f"🔄 API: 开始刷新订单详情 (后台模式: {background})")
        print(f"   账户ID: {account_id}")
        print(f"   订单限制: {limit}")
        print(f"{'='*60}\n")
        
        if background:
            # 后台执行
            task_manager = get_task_manager()
            
            # 确保任务管理器已启动
            if not task_manager.is_running:
                await task_manager.start()
            
            # 创建后台任务
            task_id = task_manager.create_task(
                ReiOrderSyncServiceOptimized.refresh_order_details_async,
                account_id=account_id,
                limit=limit,
                task_name=f"刷新订单详情 - 账户{account_id}"
            )
            
            return {
                "success": True,
                "message": "任务已创建，正在后台执行",
                "task_id": task_id,
                "background": True
            }
        else:
            # 前台执行（优化版本）
            result = await ReiOrderSyncServiceOptimized.refresh_order_details_async(
                account_id=account_id,
                limit=limit
            )
            
            if result.get('success'):
                return {
                    "success": True,
                    "message": result.get('message', '刷新完成'),
                    "background": False,
                    "data": {
                        "account_id": account_id,
                        "orders_found": result.get('results', {}).get('orders_found', 0),
                        "orders_updated": result.get('results', {}).get('orders_updated', 0),
                        "orders_failed": result.get('results', {}).get('orders_failed', 0),
                        "updated_orders": result.get('results', {}).get('updated_orders', []),
                        "failed_orders": result.get('results', {}).get('failed_orders', [])
                    }
                }
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=result.get('error', '刷新订单详情失败')
                )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API: 刷新订单详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"刷新订单详情失败: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    获取后台任务状态
    
    参数:
    - task_id: 任务ID
    
    返回:
    - 任务状态和进度信息
    """
    try:
        from services.rei.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        task_status = task_manager.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return {
            "success": True,
            "data": task_status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/tasks")
async def get_all_tasks():
    """
    获取所有后台任务
    
    返回:
    - 所有任务列表
    """
    try:
        from services.rei.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        tasks = task_manager.get_all_tasks()
        
        return {
            "success": True,
            "data": {
                "tasks": list(tasks.values()),
                "total": len(tasks)
            }
        }
    
    except Exception as e:
        print(f"❌ 获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.post("/orders/{order_id}/refresh")
async def refresh_single_order(order_id: str):
    """
    刷新单个订单详情
    
    流程:
    1. 从数据库读取订单信息
    2. 提取账单姓名和邮编
    3. 调用 REI API 获取最新订单数据
    4. 更新到数据库
    
    参数:
    - order_id: 订单号
    
    返回:
    - 刷新结果
    """
    try:
        from services.rei.rei_order_sync_service_optimized import ReiOrderSyncServiceOptimized
        
        print(f"\n{'='*60}")
        print(f"🔄 API: 开始刷新单个订单详情")
        print(f"   订单号: {order_id}")
        print(f"{'='*60}\n")
        
        # 调用服务层刷新单个订单
        result = await ReiOrderSyncServiceOptimized.refresh_single_order_async(order_id)
        
        if result.get('success'):
            return {
                "success": True,
                "message": result.get('message', '订单刷新成功'),
                "data": result.get('data')
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', '刷新订单失败')
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API: 刷新单个订单失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"刷新订单失败: {str(e)}")


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消后台任务
    
    参数:
    - task_id: 任务ID
    
    返回:
    - 取消结果
    """
    try:
        from services.rei.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        success = task_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在或无法取消")
        
        return {
            "success": True,
            "message": f"任务 {task_id} 已取消"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取消任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")
