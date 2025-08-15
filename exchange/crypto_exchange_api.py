#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import hmac
import hashlib
import requests
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class OrderResult:
    """Order operation result"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None

@dataclass
class BalanceInfo:
    """Balance information"""
    currency: str
    available: float
    total: float
    locked: float = 0.0

@dataclass
class OrderInfo:
    """Order bilgisi"""
    order_id: str
    instrument_name: str
    side: str  # BUY/SELL
    type: str  # MARKET/LIMIT/STOP_LOSS/TAKE_PROFIT
    status: str  # ACTIVE/FILLED/CANCELLED/REJECTED/EXPIRED
    price: float
    quantity: float
    filled_quantity: float = 0.0
    avg_price: float = 0.0
    created_time: Optional[str] = None
    updated_time: Optional[str] = None

@dataclass
class TradeInfo:
    """Trade bilgisi"""
    trade_id: str
    order_id: str
    instrument_name: str
    side: str
    price: float
    quantity: float
    fee: float
    timestamp: str

class CryptoExchangeAPI:
    """
    Crypto.com Exchange API için gelişmiş adapter sınıfı
    - Thread-safe operations
    - Async support
    - Error handling ve retry logic
    - Rate limiting
    """
    
    def __init__(self, config_manager):
        self.config = config_manager.exchange
        self.trading_config = config_manager.trading
        
        # API endpoints
        self.trading_base_url = self.config.base_url
        self.account_base_url = self.config.account_url
        
        # Rate limiting
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_reset_time = 0
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # API credentials validation
        if not self.config.api_key or not self.config.api_secret:
            raise ValueError("API key and secret are required")
        
        logger.info(f"CryptoExchangeAPI initialized - Trading: {self.trading_base_url}, Account: {self.account_base_url}")
        
        # Test authentication
        if self._test_authentication():
            logger.info("✅ Exchange API authentication successful")
        else:
            logger.error("❌ Exchange API authentication failed")
            raise ValueError("Could not authenticate with Crypto.com Exchange API")
    
    def _wait_for_rate_limit(self):
        """Rate limiting kontrolü"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self._rate_limit_reset_time > 60:
            self._request_count = 0
            self._rate_limit_reset_time = current_time
        
        # Check if we've hit the rate limit
        if self._request_count >= self.config.rate_limit_per_minute:
            wait_time = 60 - (current_time - self._rate_limit_reset_time)
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self._request_count = 0
                self._rate_limit_reset_time = time.time()
        
        # Minimum delay between requests
        time_since_last = current_time - self._last_request_time
        if time_since_last < 0.1:  # 100ms minimum between requests
            time.sleep(0.1 - time_since_last)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    def params_to_str(self, obj, level: int = 0) -> str:
        """
        Crypto.com'un resmi algoritmasına göre params'ları string'e çevir
        """
        MAX_LEVEL = 3
        
        if level >= MAX_LEVEL:
            return str(obj)

        if isinstance(obj, dict):
            return_str = ""
            for key in sorted(obj.keys()):
                return_str += key
                if obj[key] is None:
                    return_str += 'null'
                elif isinstance(obj[key], bool):
                    return_str += str(obj[key]).lower()
                elif isinstance(obj[key], list):
                    for sub_obj in obj[key]:
                        return_str += self.params_to_str(sub_obj, level + 1)
                else:
                    return_str += str(obj[key])
            return return_str
        else:
            return str(obj)
    
    def _convert_numbers_to_strings(self, obj):
        """Tüm sayısal değerleri string'e çevir (API requirement)"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (int, float, Decimal)):
                    obj[key] = str(value)
                elif isinstance(value, (dict, list)):
                    self._convert_numbers_to_strings(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (int, float, Decimal)):
                    obj[i] = str(item)
                elif isinstance(item, (dict, list)):
                    self._convert_numbers_to_strings(item)
        return obj
    
    def send_request(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """
        API request gönder with retry logic
        """
        if params is None:
            params = {}
        
        # Rate limiting
        self._wait_for_rate_limit()
        
        # Convert numbers to strings
        params = self._convert_numbers_to_strings(params.copy())
        
        # Generate request ID and nonce
        request_id = int(time.time() * 1000)
        nonce = request_id
        
        # Convert params to string
        param_str = self.params_to_str(params)
        
        # Determine base URL
        account_methods = [
            "private/get-account-summary", 
            "private/margin/get-account-summary",
            "private/get-subaccount-balances",
            "private/get-accounts"
        ]
        is_account_method = any(method.startswith(acc_method) for acc_method in account_methods)
        base_url = self.account_base_url if is_account_method else self.trading_base_url
        
        # Build signature payload
        sig_payload = method + str(request_id) + self.config.api_key + param_str + str(nonce)
        
        # Generate signature
        signature = hmac.new(
            bytes(self.config.api_secret, 'utf-8'),
            msg=bytes(sig_payload, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Create request body
        request_body = {
            "id": request_id,
            "method": method,
            "api_key": self.config.api_key,
            "params": params,
            "nonce": nonce,
            "sig": signature
        }
        
        endpoint = f"{base_url}{method}"
        
        logger.debug(f"API Request: {method} -> {endpoint}")
        logger.debug(f"Params: {params}")
        
        # Send request with retry logic
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    endpoint,
                    json=request_body,
                    timeout=self.config.timeout
                )
                
                # Parse response
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response: {response.text}")
                    if attempt == self.config.max_retries - 1:
                        return {"error": "Failed to parse JSON", "raw": response.text}
                    continue
                
                # Check for success
                if response.status_code == 200:
                    if response_data.get("code") == 0:
                        logger.debug(f"API Response: Success")
                        return response_data
                    else:
                        error_code = response_data.get("code")
                        error_msg = response_data.get("message", response_data.get("msg", "Unknown error"))
                        logger.error(f"API Error: {error_code} - {error_msg}")
                        return response_data
                
                # Handle rate limiting
                elif response.status_code == 429:
                    wait_time = 60  # Wait 1 minute for rate limit
                    logger.warning(f"Rate limited, waiting {wait_time} seconds (attempt {attempt + 1})")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                # Other HTTP errors
                else:
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    if attempt == self.config.max_retries - 1:
                        return {"error": f"HTTP {response.status_code}", "message": response.text}
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {"error": "Request timeout"}
            
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": "Connection error"}
            
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return {"error": f"Unexpected error: {str(e)}"}
        
        return {"error": "Max retries exceeded"}
    
    def _test_authentication(self) -> bool:
        """API authentication test"""
        try:
            response = self.get_account_summary()
            return response is not None
        except Exception as e:
            logger.error(f"Authentication test failed: {str(e)}")
            return False
    
    # ============ ACCOUNT METHODS ============
    
    def get_account_summary(self) -> Optional[Dict]:
        """Hesap özetini getir"""
        try:
            response = self.send_request("private/get-account-summary", {})
            
            if response.get("code") == 0:
                return response.get("result")
            else:
                logger.error(f"Failed to get account summary: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error in get_account_summary: {str(e)}")
            return None
    
    def get_balance(self, currency: str = "USDT") -> float:
        """Belirli bir para birimi bakiyesi"""
        try:
            account_summary = self.get_account_summary()
            if not account_summary or "accounts" not in account_summary:
                logger.error("Failed to get account summary for balance check")
                return 0.0
                
            for account in account_summary["accounts"]:
                if account.get("currency") == currency:
                    available = float(account.get("available", 0))
                    logger.debug(f"Available {currency} balance: {available}")
                    return available
                    
            logger.warning(f"Currency {currency} not found in account")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting balance for {currency}: {str(e)}")
            return 0.0
    
    def get_all_balances(self) -> List[BalanceInfo]:
        """Tüm bakiyeleri getir"""
        try:
            account_summary = self.get_account_summary()
            if not account_summary or "accounts" not in account_summary:
                return []
            
            balances = []
            for account in account_summary["accounts"]:
                currency = account.get("currency", "")
                available = float(account.get("available", 0))
                balance = float(account.get("balance", 0))
                
                if available > 0 or balance > 0:  # Only include non-zero balances
                    balance_info = BalanceInfo(
                        currency=currency,
                        available=available,
                        total=balance,
                        locked=balance - available
                    )
                    balances.append(balance_info)
            
            return balances
            
        except Exception as e:
            logger.error(f"Error getting all balances: {str(e)}")
            return []
    
    def has_sufficient_balance(self, currency: str = "USDT", required_amount: float = None) -> bool:
        """Yeterli bakiye kontrolü"""
        if required_amount is None:
            required_amount = self.trading_config.min_balance_required
        
        balance = self.get_balance(currency)
        sufficient = balance >= required_amount
        
        if sufficient:
            logger.debug(f"Sufficient balance: {balance} {currency} >= {required_amount}")
        else:
            logger.warning(f"Insufficient balance: {balance} {currency} < {required_amount}")
        
        return sufficient
    
    # ============ TRADING METHODS ============
    
    def get_current_price(self, instrument_name: str) -> Optional[float]:
        """Güncel fiyat getir (public API)"""
        try:
            url = f"{self.account_base_url}public/get-ticker"
            params = {"instrument_name": instrument_name}
            
            response = requests.get(url, params=params, timeout=self.config.timeout)
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get("code") == 0:
                    result = response_data.get("result", {})
                    data = result.get("data", [])
                    
                    if data:
                        # Get the ask price (latest price)
                        latest_price = float(data[0].get("a", 0))
                        logger.debug(f"Current price for {instrument_name}: {latest_price}")
                        return latest_price
                    else:
                        logger.warning(f"No ticker data found for {instrument_name}")
                else:
                    error_code = response_data.get("code")
                    error_msg = response_data.get("message", "Unknown error")
                    logger.error(f"Ticker API error: {error_code} - {error_msg}")
            else:
                logger.error(f"HTTP error getting price: {response.status_code}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {instrument_name}: {str(e)}")
            return None
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Quantity formatını coin'e göre ayarla"""
        base_currency = symbol.split('_')[0]
        
        # Decimal precision'ı coin'e göre ayarla
        if base_currency in ["BTC", "ETH"]:
            # High-value coins: 6 decimal places
            decimal_places = 6
        elif base_currency in ["SUI", "SOL", "ADA", "DOT"]:
            # Medium-value coins: 2 decimal places
            decimal_places = 2
        elif base_currency in ["BONK", "SHIB", "PEPE"]:
            # Meme coins: whole numbers
            decimal_places = 0
        else:
            # Default: 2 decimal places
            decimal_places = 2
        
        # Use Decimal for precise rounding
        decimal_quantity = Decimal(str(quantity))
        rounded_quantity = decimal_quantity.quantize(
            Decimal('0.1') ** decimal_places, 
            rounding=ROUND_HALF_UP
        )
        
        formatted = str(rounded_quantity)
        logger.debug(f"Formatted quantity for {symbol}: {quantity} -> {formatted}")
        
        return formatted
    
    def create_buy_order(self, instrument_name: str, amount_usd: float) -> OrderResult:
        """Market buy order (USDT amount ile)"""
        try:
            logger.info(f"Creating market buy order: {instrument_name} with ${amount_usd} USDT")
            
            # Check balance
            if not self.has_sufficient_balance("USDT", amount_usd * 1.05):  # 5% buffer for fees
                return OrderResult(
                    success=False,
                    error_message="Insufficient USDT balance"
                )
            
            params = {
                "instrument_name": instrument_name,
                "side": "BUY",
                "type": "MARKET",
                "notional": str(amount_usd)
            }
            
            response = self.send_request("private/create-order", params)
            
            if response.get("code") == 0:
                order_id = response.get("result", {}).get("order_id")
                logger.info(f"✅ Buy order created successfully: {order_id}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    response_data=response
                )
            else:
                error_code = response.get("code")
                error_msg = response.get("message", response.get("msg", "Unknown error"))
                logger.error(f"❌ Failed to create buy order: {error_code} - {error_msg}")
                
                return OrderResult(
                    success=False,
                    error_message=f"API Error {error_code}: {error_msg}",
                    response_data=response
                )
                
        except Exception as e:
            logger.error(f"Error creating buy order: {str(e)}")
            return OrderResult(
                success=False,
                error_message=f"Exception: {str(e)}"
            )
    
    def create_sell_order(self, instrument_name: str, quantity: float = None) -> OrderResult:
        """Market sell order"""
        try:
            base_currency = instrument_name.split('_')[0]
            
            # If quantity not provided, get available balance
            if quantity is None:
                available_balance = self.get_balance(base_currency)
                if available_balance <= 0:
                    return OrderResult(
                        success=False,
                        error_message=f"No {base_currency} balance available"
                    )
                quantity = available_balance * 0.99  # Use 99% to avoid precision issues
            
            # Format quantity
            formatted_quantity = self.format_quantity(instrument_name, quantity)
            
            logger.info(f"Creating market sell order: {instrument_name} quantity {formatted_quantity}")
            
            params = {
                "instrument_name": instrument_name,
                "side": "SELL",
                "type": "MARKET",
                "quantity": formatted_quantity
            }
            
            response = self.send_request("private/create-order", params)
            
            if response.get("code") == 0:
                order_id = response.get("result", {}).get("order_id")
                logger.info(f"✅ Sell order created successfully: {order_id}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    response_data=response
                )
            else:
                error_code = response.get("code")
                error_msg = response.get("message", response.get("msg", "Unknown error"))
                logger.error(f"❌ Failed to create sell order: {error_code} - {error_msg}")
                
                # Try with different quantity formats if format error
                if error_code in [213, 10004] and "quantity" in error_msg.lower():
                    logger.info("Trying alternative quantity formats...")
                    
                    # Try different formats
                    alt_quantities = [
                        str(int(quantity)),  # Integer
                        f"{quantity:.0f}",   # No decimals
                        f"{quantity:.8f}".rstrip('0').rstrip('.'),  # Remove trailing zeros
                    ]
                    
                    for alt_qty in alt_quantities:
                        if alt_qty != formatted_quantity:
                            logger.info(f"Trying quantity format: {alt_qty}")
                            params["quantity"] = alt_qty
                            
                            alt_response = self.send_request("private/create-order", params)
                            if alt_response.get("code") == 0:
                                order_id = alt_response.get("result", {}).get("order_id")
                                logger.info(f"✅ Sell order created with alternative format: {order_id}")
                                
                                return OrderResult(
                                    success=True,
                                    order_id=order_id,
                                    response_data=alt_response
                                )
                
                return OrderResult(
                    success=False,
                    error_message=f"API Error {error_code}: {error_msg}",
                    response_data=response
                )
                
        except Exception as e:
            logger.error(f"Error creating sell order: {str(e)}")
            return OrderResult(
                success=False,
                error_message=f"Exception: {str(e)}"
            )
    
    def create_limit_order(self, instrument_name: str, side: str, price: float, 
                          quantity: float) -> OrderResult:
        """Limit order oluştur"""
        try:
            formatted_quantity = self.format_quantity(instrument_name, quantity)
            
            params = {
                "instrument_name": instrument_name,
                "side": side.upper(),
                "type": "LIMIT",
                "price": str(price),
                "quantity": formatted_quantity
            }
            
            response = self.send_request("private/create-order", params)
            
            if response.get("code") == 0:
                order_id = response.get("result", {}).get("order_id")
                logger.info(f"✅ Limit order created: {side} {formatted_quantity} {instrument_name} @ {price}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    response_data=response
                )
            else:
                error_code = response.get("code")
                error_msg = response.get("message", response.get("msg", "Unknown error"))
                logger.error(f"❌ Failed to create limit order: {error_code} - {error_msg}")
                
                return OrderResult(
                    success=False,
                    error_message=f"API Error {error_code}: {error_msg}",
                    response_data=response
                )
                
        except Exception as e:
            logger.error(f"Error creating limit order: {str(e)}")
            return OrderResult(
                success=False,
                error_message=f"Exception: {str(e)}"
            )
    
    # ============ ORDER MANAGEMENT METHODS ============
    
    def get_order_details(self, order_id: str) -> Optional[OrderInfo]:
        """Order detaylarını getir"""
        try:
            params = {"order_id": order_id}
            response = self.send_request("private/get-order-detail", params)
            
            if response.get("code") == 0:
                result = response.get("result", {})
                
                order_info = OrderInfo(
                    order_id=result.get("order_id", ""),
                    instrument_name=result.get("instrument_name", ""),
                    side=result.get("side", ""),
                    type=result.get("type", ""),
                    status=result.get("status", ""),
                    price=float(result.get("price", 0)),
                    quantity=float(result.get("quantity", 0)),
                    filled_quantity=float(result.get("cumulative_quantity", 0)),
                    avg_price=float(result.get("avg_price", 0)),
                    created_time=result.get("create_time"),
                    updated_time=result.get("update_time")
                )
                
                return order_info
            else:
                logger.error(f"Failed to get order details: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting order details for {order_id}: {str(e)}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Order iptal et"""
        try:
            params = {"order_id": order_id}
            response = self.send_request("private/cancel-order", params)
            
            if response.get("code") == 0:
                logger.info(f"✅ Order cancelled successfully: {order_id}")
                return True
            else:
                error_code = response.get("code")
                error_msg = response.get("message", response.get("msg", "Unknown error"))
                logger.error(f"❌ Failed to cancel order {order_id}: {error_code} - {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False
    
    def get_order_history(self, instrument_name: str = None, limit: int = 50) -> List[OrderInfo]:
        """Order geçmişini getir"""
        try:
            current_time = int(time.time() * 1000)
            one_hour_ago = current_time - (60 * 60 * 1000)
            
            params = {
                "start_time": one_hour_ago,
                "end_time": current_time,
                "limit": limit
            }
            
            if instrument_name:
                params["instrument_name"] = instrument_name
            
            response = self.send_request("private/get-order-history", params)
            
            if response.get("code") == 0:
                orders_data = response.get("result", {}).get("data", [])
                
                orders = []
                for order_data in orders_data:
                    order_info = OrderInfo(
                        order_id=order_data.get("order_id", ""),
                        instrument_name=order_data.get("instrument_name", ""),
                        side=order_data.get("side", ""),
                        type=order_data.get("type", ""),
                        status=order_data.get("status", ""),
                        price=float(order_data.get("price", 0)),
                        quantity=float(order_data.get("quantity", 0)),
                        filled_quantity=float(order_data.get("cumulative_quantity", 0)),
                        avg_price=float(order_data.get("avg_price", 0)),
                        created_time=order_data.get("create_time"),
                        updated_time=order_data.get("update_time")
                    )
                    orders.append(order_info)
                
                return orders
            else:
                logger.error(f"Failed to get order history: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []
    
    def get_trade_history(self, instrument_name: str = None, limit: int = 50) -> List[TradeInfo]:
        """Trade geçmişini getir"""
        try:
            current_time = int(time.time() * 1000)
            one_hour_ago = current_time - (60 * 60 * 1000)
            
            params = {
                "start_time": one_hour_ago,
                "end_time": current_time,
                "limit": limit
            }
            
            if instrument_name:
                params["instrument_name"] = instrument_name
            
            response = self.send_request("private/get-trades", params)
            
            if response.get("code") == 0:
                trades_data = response.get("result", {}).get("data", [])
                
                trades = []
                for trade_data in trades_data:
                    trade_info = TradeInfo(
                        trade_id=trade_data.get("trade_id", ""),
                        order_id=trade_data.get("order_id", ""),
                        instrument_name=trade_data.get("instrument_name", ""),
                        side=trade_data.get("side", ""),
                        price=float(trade_data.get("traded_price", 0)),
                        quantity=float(trade_data.get("traded_quantity", 0)),
                        fee=float(trade_data.get("fee", 0)),
                        timestamp=trade_data.get("create_time", "")
                    )
                    trades.append(trade_info)
                
                return trades
            else:
                logger.error(f"Failed to get trade history: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return []
    
    # ============ UTILITY METHODS ============
    
    def validate_instrument(self, instrument_name: str) -> bool:
        """Instrument geçerli mi kontrol et"""
        try:
            price = self.get_current_price(instrument_name)
            return price is not None
        except Exception:
            return False
    
    def get_trading_pairs(self) -> List[str]:
        """Mevcut trading pair'leri getir"""
        try:
            url = f"{self.account_base_url}public/get-instruments"
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get("code") == 0:
                    instruments = response_data.get("result", {}).get("data", [])
                    
                    trading_pairs = []
                    for instrument in instruments:
                        if instrument.get("quote_currency") == "USDT":
                            trading_pairs.append(instrument.get("instrument_name", ""))
                    
                    return trading_pairs
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting trading pairs: {str(e)}")
            return []
    
    def close(self):
        """API bağlantısını kapat"""
        try:
            if hasattr(self, 'session'):
                self.session.close()
            logger.info("Exchange API connection closed")
        except Exception as e:
            logger.error(f"Error closing exchange API: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
