"""
REI 订单HTML解析服务
从REI订单邮件的HTML内容中提取订单信息
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import traceback


class ReiOrderParser:
    """REI 订单HTML解析器"""
    
    @staticmethod
    def parse_order_from_html(html_content: str) -> Dict[str, Any]:
        """
        从HTML内容中解析REI订单信息
        
        Args:
            html_content: 邮件的HTML内容
            
        Returns:
            解析后的订单数据字典
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            order_data = {
                'order_number': None,
                'order_date': None,
                'order_time': None,
                'email': None,
                'status': 'pending',
                'estimated_arrival': None,
                'delivery_status': 'not_delivered',
                'delivered_date': None,
                'scheduled_delivery_date': None,
                'amount': 0.00,
                'subtotal': 0.00,
                'shipping_fee': 0.00,
                'tax': 0.00,
                'total': 0.00,
                'paid': 0.00,
                'total_savings': 0.00,
                'shipping_name': None,
                'shipping_address': None,
                'shipping_city': None,
                'shipping_state': None,
                'shipping_zip_code': None,
                'shipping_method': 'Standard shipping',
                'billing_name': None,
                'billing_address': None,
                'billing_city': None,
                'billing_state': None,
                'billing_zip_code': None,
                'products': [],
                'gift_cards': []
            }
            
            # 1. 提取订单号
            order_number = ReiOrderParser._extract_order_number(soup)
            if order_number:
                order_data['order_number'] = order_number
            
            # 2. 提取订单日期和时间
            order_date_info = ReiOrderParser._extract_order_date(soup)
            if order_date_info:
                order_data.update(order_date_info)
            
            # 3. 提取预计到达时间
            estimated_arrival = ReiOrderParser._extract_estimated_arrival(soup)
            if estimated_arrival:
                order_data['estimated_arrival'] = estimated_arrival
            
            # 4. 提取收货地址
            shipping_info = ReiOrderParser._extract_shipping_address(soup)
            if shipping_info:
                order_data.update(shipping_info)
            
            # 5. 提取配送方式
            shipping_method = ReiOrderParser._extract_shipping_method(soup)
            if shipping_method:
                order_data['shipping_method'] = shipping_method
            
            # 6. 提取账单地址
            billing_info = ReiOrderParser._extract_billing_address(soup)
            if billing_info:
                order_data.update(billing_info)
            
            # 7. 提取金额信息（已移除商品信息提取）
            amount_info = ReiOrderParser._extract_amounts(soup)
            if amount_info:
                order_data.update(amount_info)
            
            # 9. 提取礼品卡信息
            gift_cards = ReiOrderParser._extract_gift_cards(soup)
            if gift_cards:
                order_data['gift_cards'] = gift_cards
            
            print(f"✅ 成功解析订单: {order_data['order_number']}")
            return order_data
            
        except Exception as e:
            print(f"❌ 解析订单HTML失败: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def _extract_order_number(soup: BeautifulSoup) -> Optional[str]:
        """提取订单号"""
        try:
            # 查找包含订单号的p标签
            # <p style="...font-size:20px..."> A385267303 </p>
            for p in soup.find_all('p'):
                style = p.get('style', '')
                if 'font-size:20px' in style or 'font-size: 20px' in style:
                    text = p.get_text(strip=True)
                    # 验证是否为订单号格式（字母+数字）
                    if re.match(r'^[A-Z]\d{9}$', text):
                        return text
            
            # 备用方法：查找包含"Order date"的段落附近的订单号
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if re.match(r'^[A-Z]\d{9}$', text):
                    return text
            
            return None
        except Exception as e:
            print(f"⚠️ 提取订单号失败: {e}")
            return None
    
    @staticmethod
    def _extract_order_date(soup: BeautifulSoup) -> Optional[Dict]:
        """提取订单日期和时间"""
        try:
            # 查找包含"Order date:"的p标签
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if 'Order date:' in text:
                    # 提取日期 "Order date: 10/06/2025"
                    match = re.search(r'Order date:\s*(\d{2})/(\d{2})/(\d{4})', text)
                    if match:
                        month, day, year = match.groups()
                        order_date = f"{year}-{month}-{day}"
                        return {
                            'order_date': order_date,
                            'order_time': None  # 留空，使用其他方法获取
                        }
            
            return None
        except Exception as e:
            print(f"⚠️ 提取订单日期失败: {e}")
            return None
    
    @staticmethod
    def _extract_estimated_arrival(soup: BeautifulSoup) -> Optional[str]:
        """提取预计到达时间"""
        try:
            # 查找包含预计到达时间的p标签
            # <p style="...font-size:22px...">Fri, Oct 10</p>
            for p in soup.find_all('p'):
                style = p.get('style', '')
                if 'font-size:22px' in style or 'font-size: 22px' in style:
                    text = p.get_text(strip=True)
                    # 验证日期格式 "Fri, Oct 10"
                    if re.match(r'^[A-Z][a-z]{2},\s+[A-Z][a-z]{2}\s+\d{1,2}$', text):
                        return text
            
            return None
        except Exception as e:
            print(f"⚠️ 提取预计到达时间失败: {e}")
            return None
    
    @staticmethod
    def _extract_shipping_address(soup: BeautifulSoup) -> Optional[Dict]:
        """提取收货地址和物流URL"""
        try:
            text = soup.get_text()
            
            # 方法1：查找 "Ship to:" 后面的地址
            ship_to_pattern = r'Ship\s+to:\s*([^\n]+)\n([^\n]+)\n([A-Z\s]+),\s+([A-Z]{2})\s+(\d{5})'
            match = re.search(ship_to_pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                address = match.group(2).strip()
                city = match.group(3).strip()
                state = match.group(4)
                zip_code = match.group(5)
                
                # 尝试提取物流URL（查找地址相关的链接）
                tracking_url = ReiOrderParser._extract_tracking_url(soup)
                
                return {
                    'shipping_name': name,
                    'shipping_address': address,
                    'shipping_city': city,
                    'shipping_state': state,
                    'shipping_zip_code': zip_code,
                    'tracking_url': tracking_url
                }
            
            # 方法2：查找包含收货地址的p标签（原有逻辑）
            for p in soup.find_all('p'):
                # 查找包含多行地址的段落
                if '<br>' in str(p) or '<br/>' in str(p):
                    # 获取所有文本行
                    lines = [line.strip() for line in p.stripped_strings if line.strip()]
                    
                    if len(lines) >= 3:
                        # 第一行：姓名
                        name = lines[0]
                        
                        # 查找州和邮编所在的行（格式：CITY, STATE ZIPCODE）
                        for i, line in enumerate(lines):
                            # 匹配格式：WHITEFISH, MT 59937 或 San Leandro, CA 94577
                            match = re.search(r'([A-Za-z\s]+),\s+([A-Z]{2})\s+(\d{5})', line)
                            if match:
                                city, state, zip_code = match.groups()
                                # 地址是中间的行
                                address_parts = lines[1:i]
                                address = ' '.join(address_parts) if address_parts else lines[1] if len(lines) > 1 else ''
                                
                                # 验证是否为收货地址（检查是否在 "Ship to" 附近）
                                p_text = p.get_text()
                                # 查找前面的文本
                                all_p_tags = soup.find_all('p')
                                p_index = all_p_tags.index(p) if p in all_p_tags else -1
                                
                                if p_index >= 0:
                                    # 检查前面5个p标签是否包含 "Ship to"
                                    prev_text = ' '.join([all_p_tags[j].get_text() for j in range(max(0, p_index-5), p_index)])
                                    if 'ship' in prev_text.lower() or p_index < 15:
                                        # 尝试提取物流URL
                                        tracking_url = ReiOrderParser._extract_tracking_url(soup)
                                        
                                        return {
                                            'shipping_name': name,
                                            'shipping_address': address,
                                            'shipping_city': city.strip(),
                                            'shipping_state': state,
                                            'shipping_zip_code': zip_code,
                                            'tracking_url': tracking_url
                                        }
            
            print(f"  ⚠️ 未找到收货地址")
            return None
        except Exception as e:
            print(f"❌ 提取收货地址失败: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def _extract_tracking_url(soup: BeautifulSoup) -> Optional[str]:
        """提取物流追踪URL（从地址链接中提取）"""
        try:
            # 查找所有a标签
            for a in soup.find_all('a'):
                href = a.get('href', '')
                # 查找Google Maps链接（通常是地址链接）
                if 'google.com/maps' in href or 'maps.google.com' in href:
                    # 提取原始URL（去除Gmail重定向）
                    if 'data-saferedirecturl' in a.attrs:
                        safe_url = a.get('data-saferedirecturl', '')
                        # 从 data-saferedirecturl 中提取真实URL
                        # 格式: https://www.google.com/url?q=REAL_URL&source=...
                        if '?q=' in safe_url:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(safe_url)
                            query_params = urllib.parse.parse_qs(parsed.query)
                            if 'q' in query_params:
                                real_url = query_params['q'][0]
                                print(f"  📍 找到物流URL: {real_url}")
                                return real_url
                    
                    # 如果没有 data-saferedirecturl，直接返回 href
                    print(f"  📍 找到物流URL: {href}")
                    return href
            
            print(f"  ⚠️ 未找到物流URL")
            return None
        except Exception as e:
            print(f"⚠️ 提取物流URL失败: {e}")
            return None
    
    @staticmethod
    def _extract_shipping_method(soup: BeautifulSoup) -> Optional[str]:
        """提取配送方式"""
        try:
            # 查找包含配送方式的p标签（通常是斜体）
            for p in soup.find_all('p'):
                style = p.get('style', '')
                if 'font-style:italic' in style or 'font-style: italic' in style:
                    text = p.get_text(strip=True)
                    if 'shipping' in text.lower():
                        return text
            
            return None
        except Exception as e:
            print(f"⚠️ 提取配送方式失败: {e}")
            return None
    
    @staticmethod
    def _extract_billing_address(soup: BeautifulSoup) -> Optional[Dict]:
        """提取账单地址"""
        try:
            text = soup.get_text()
            
            # 方法1：查找 "Billing address:" 后面的地址
            billing_pattern = r'Billing\s+address:\s*([^\n]+)\n([^\n]+)\n([A-Za-z\s]+),\s+([A-Z]{2})\s+(\d{5})'
            match = re.search(billing_pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                address = match.group(2).strip()
                city = match.group(3).strip()
                state = match.group(4)
                zip_code = match.group(5)
                
                return {
                    'billing_name': name,
                    'billing_address': address,
                    'billing_city': city,
                    'billing_state': state,
                    'billing_zip_code': zip_code
                }
            
            # 方法2：查找包含账单地址的p标签（通常在邮件后半部分）
            all_paragraphs = soup.find_all('p')
            
            for i, p in enumerate(all_paragraphs):
                # 查找包含多行地址的段落
                if '<br>' in str(p) or '<br/>' in str(p):
                    lines = [line.strip() for line in p.stripped_strings if line.strip()]
                    
                    if len(lines) >= 3:
                        name = lines[0]
                        
                        # 查找州和邮编
                        for j, line in enumerate(lines):
                            match = re.search(r'([A-Za-z\s]+),\s+([A-Z]{2})\s+(\d{5})', line)
                            if match:
                                city, state, zip_code = match.groups()
                                address_parts = lines[1:j]
                                address = ' '.join(address_parts) if address_parts else lines[1] if len(lines) > 1 else ''
                                
                                # 验证是否为账单地址（在邮件后半部分或包含billing关键词）
                                prev_text = ' '.join([all_paragraphs[k].get_text() for k in range(max(0, i-3), i)])
                                if 'billing' in prev_text.lower() or i > len(all_paragraphs) // 2:
                                    return {
                                        'billing_name': name,
                                        'billing_address': address,
                                        'billing_city': city.strip(),
                                        'billing_state': state,
                                        'billing_zip_code': zip_code
                                    }
            
            print(f"  ⚠️ 未找到账单地址")
            return None
        except Exception as e:
            print(f"❌ 提取账单地址失败: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def _extract_amounts(soup: BeautifulSoup) -> Optional[Dict]:
        """提取金额信息"""
        try:
            amounts = {
                'subtotal': 0.00,
                'shipping_fee': 0.00,
                'tax': 0.00,
                'total': 0.00,
                'total_savings': 0.00
            }
            
            # 查找包含金额的文本
            text = soup.get_text()
            
            # 提取小计
            match = re.search(r'Subtotal[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                amounts['subtotal'] = float(match.group(1).replace(',', ''))
            
            # 提取运费
            match = re.search(r'Shipping[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                amounts['shipping_fee'] = float(match.group(1).replace(',', ''))
            
            # 提取税费
            match = re.search(r'Tax[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                amounts['tax'] = float(match.group(1).replace(',', ''))
            
            # 提取总计
            match = re.search(r'Total[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                amounts['total'] = float(match.group(1).replace(',', ''))
                amounts['amount'] = amounts['total']
            
            # 提取节省金额
            match = re.search(r'(?:You saved|Total savings)[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                amounts['total_savings'] = float(match.group(1).replace(',', ''))
            
            return amounts
        except Exception as e:
            print(f"⚠️ 提取金额信息失败: {e}")
            return None
    
    @staticmethod
    def _extract_gift_cards(soup: BeautifulSoup) -> List[float]:
        """提取礼品卡金额"""
        try:
            gift_cards = []
            
            # 查找包含礼品卡的文本
            text = soup.get_text()
            
            # 查找礼品卡金额（格式：$27.46, $52.37, $60.00）
            matches = re.findall(r'Gift\s+card[:\s]+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
            for match in matches:
                amount = float(match.replace(',', ''))
                gift_cards.append(amount)
            
            return gift_cards
        except Exception as e:
            print(f"⚠️ 提取礼品卡信息失败: {e}")
            return []
