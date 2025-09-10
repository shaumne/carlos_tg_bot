#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Real Trade Executor
Production-ready implementation for executing real trades based on signals
Uses Crypto.com Exchange API with proper authentication
"""

import logging
import time
import hmac
import hashlib
import requests
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SimpleTradeExecutor:
    """Real trade executor for signals with Crypto.com Exchange API"""
    
    def __init__(self, config_manager, database_manager, exchange_api=None):
        self.config = config_manager
        self.db = database_manager
        self.exchange_api = exchange_api
        
        # Trade tracking
        self.active_positions = {}  # {symbol: position_data}
        
        # TP/SL monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        self.tp_sl_check_interval = 30  # 30 seconds
        
        # API Configuration from trade_executor.py style
        self.api_key = config_manager.exchange.api_key
        self.api_secret = config_manager.exchange.api_secret
        self.trading_base_url = "https://api.crypto.com/exchange/v1/"
        self.account_base_url = "https://api.crypto.com/v2/"
        self.trade_amount = float(config_manager.trading.trade_amount)
        self.min_balance_required = self.trade_amount * 1.05  # 5% buffer for fees
        self.trading_currency = "USDT"  # Default, may be changed to USD by get_balance
        
        if not self.api_key or not self.api_secret:
            logger.error("API key or secret not found in configuration")
            raise ValueError("Exchange API credentials are required for real trading")
        
        logger.info("✅ Real Trade Executor initialized for production trading")
    
    def params_to_str(self, obj, level=0):
        """Convert params object to string according to Crypto.com's official algorithm"""
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
    
    def send_request(self, method, params=None):
        """Send API request to Crypto.com using official documented signing method"""
        if params is None:
            params = {}
        
        # Convert all numeric values to strings
        def convert_numbers_to_strings(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (int, float)):
                        obj[key] = str(value)
                    elif isinstance(value, (dict, list)):
                        convert_numbers_to_strings(value)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (int, float)):
                        obj[i] = str(item)
                    elif isinstance(item, (dict, list)):
                        convert_numbers_to_strings(item)
            return obj
        
        params = convert_numbers_to_strings(params)
        
        # Generate request ID and nonce
        request_id = int(time.time() * 1000)
        nonce = request_id
        
        # Convert params to string
        param_str = self.params_to_str(params)
        
        # Choose base URL based on method
        account_methods = [
            "private/get-account-summary", 
            "private/margin/get-account-summary",
            "private/get-subaccount-balances",
            "private/get-accounts"
        ]
        is_account_method = any(method.startswith(acc_method) for acc_method in account_methods)
        base_url = self.account_base_url if is_account_method else self.trading_base_url
        
        # Build signature payload
        sig_payload = method + str(request_id) + self.api_key + param_str + str(nonce)
        
        # Generate signature
        signature = hmac.new(
            bytes(self.api_secret, 'utf-8'),
            msg=bytes(sig_payload, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Create request body
        request_body = {
            "id": request_id,
            "method": method,
            "api_key": self.api_key,
            "params": params,
            "nonce": nonce,
            "sig": signature
        }
        
        # API endpoint
        endpoint = f"{base_url}{method}"
        
        logger.debug(f"API Request: {method} to {endpoint}")
        
        # Send request
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_body,
            timeout=30
        )
        
        # Process response
        try:
            response_data = response.json()
            logger.debug(f"API Response: {response_data.get('code', 'no_code')} - {response_data.get('message', 'no_message')}")
            return response_data
        except:
            logger.error(f"Failed to parse response as JSON. Raw response: {response.text}")
            return {"error": "Failed to parse JSON", "raw": response.text}
    
    def get_account_summary(self):
        """Get account summary from the exchange (following trade_executor.py approach)"""
        try:
            method = "private/get-account-summary"
            params = {}
            
            # Send request
            response = self.send_request(method, params)
            
            if response.get("code") == 0:
                logger.debug("Successfully fetched account summary")
                return response.get("result")
            else:
                error_code = response.get("code")
                error_msg = response.get("message", response.get("msg", "Unknown error"))
                logger.error(f"API error: {error_code} - {error_msg}")
            
            return None
        except Exception as e:
            logger.error(f"Error in get_account_summary: {str(e)}")
            return None
    
    def get_balance(self, currency="USDT"):
        """Get balance for a specific currency (following trade_executor.py approach)"""
        try:
            account_summary = self.get_account_summary()
            if not account_summary or "accounts" not in account_summary:
                logger.error("Failed to get account summary")
                return 0
                
            # Look for both requested currency and USD
            currency_balance = 0
            usd_balance = 0
            
            # Find the currency in accounts
            for account in account_summary["accounts"]:
                account_currency = account.get("currency")
                available = float(account.get("available", 0))
                
                # Check requested currency
                if account_currency == currency:
                    logger.debug(f"Available {currency} balance: {available}")
                    if available > 0:
                        currency_balance = available
                        logger.info(f"Found positive {currency} balance: {available}")
                
                # Check USD as fallback (many exchanges use USD for spot trading)
                elif account_currency == "USD" and available > 0:
                    usd_balance = available
                    logger.info(f"Found positive USD balance: {available}")
            
            # Return currency balance if positive, otherwise use USD
            if currency_balance > 0:
                logger.info(f"Using {currency} balance: {currency_balance}")
                return currency_balance
            elif usd_balance > 0 and currency == "USDT":
                logger.info(f"Using USD balance as USDT fallback: {usd_balance}")
                # Set the currency to USD for future trading operations
                self.trading_currency = "USD"
                return usd_balance
            else:
                logger.warning(f"Currency {currency} not found in account")
                return 0
                
        except Exception as e:
            logger.error(f"Error in get_balance: {str(e)}")
            return 0
    
    def has_sufficient_balance(self, currency="USDT"):
        """Check if there is sufficient balance for trading (following trade_executor.py approach)"""
        balance = self.get_balance(currency)
        sufficient = balance >= self.min_balance_required
        
        if sufficient:
            logger.info(f"Sufficient balance: {balance} {currency}")
        else:
            logger.warning(f"Insufficient balance: {balance} {currency}, minimum required: {self.min_balance_required}")
            
        return sufficient
    
    def buy_coin(self, instrument_name, amount_usd):
        """Buy coin with specified USD amount using market order"""
        # Follow trade_executor.py formatting logic
        original_instrument = instrument_name
        
        # Apply trade_executor.py symbol formatting first
        # Format for API: append _USDT if not already in pair format
        if '_' not in instrument_name and '/' not in instrument_name:
            formatted_pair = f"{instrument_name}_USDT"
        elif '/' in instrument_name:
            formatted_pair = instrument_name.replace('/', '_')
        else:
            formatted_pair = instrument_name
        
        # Now apply currency-specific formatting based on trading currency
        if hasattr(self, 'trading_currency') and self.trading_currency == "USD":
            # For USD balance, try USD spot formats FIRST
            if "_USDT" in formatted_pair:
                base_currency = formatted_pair.split("_")[0]
                # Try USD formats FIRST (highest priority)
                possible_formats = [
                    f"{base_currency}_USD",     # SOL_USD (with underscore) - PRIORITY
                    f"{base_currency}USD",      # SOLUSD (no underscore) - PRIORITY
                    f"{base_currency}_USDT",    # Original USDT format as fallback
                ]
            else:
                possible_formats = [formatted_pair]
        else:
            # For USDT, use the formatted pair
            possible_formats = [formatted_pair]
        
        # Try each format until one works
        for format_attempt in possible_formats:
            logger.info(f"Trying spot trading format: {format_attempt}")
            
            method = "private/create-order"
            params = {
                "instrument_name": format_attempt,
                "side": "BUY",
                "type": "MARKET",
                "notional": str(float(amount_usd))
            }
            
            response = self.send_request(method, params)
            
            if response.get("code") == 0:
                order_id = response.get("result", {}).get("order_id")
                logger.info(f"✅ BUY order successful with format: {format_attempt}")
                if order_id:
                    logger.info(f"BUY order successfully created! Order ID: {order_id}")
                    return order_id
                else:
                    logger.info(f"BUY order successful, but couldn't find order ID in response")
                    return True
            elif response.get("code") == 209:  # Invalid instrument_name
                logger.warning(f"Format {format_attempt} not valid, trying next format...")
                continue
            else:
                error_code = response.get("code")
                error_msg = response.get("message", "Unknown error")
                logger.error(f"Failed to create BUY order with format {format_attempt}. Error {error_code}: {error_msg}")
                # Don't continue for non-format errors
                return False
        
        # If all formats failed
        logger.error(f"All instrument name formats failed for {original_instrument}")
        logger.error(f"Tried formats: {possible_formats}")
        return False
    
    def sell_coin(self, instrument_name, quantity):
        """Sell a specified quantity of a coin using MARKET order"""
        try:
            # Follow trade_executor.py formatting logic
            original_instrument = instrument_name
            
            # Apply trade_executor.py symbol formatting first
            # Format for API: append _USDT if not already in pair format
            if '_' not in instrument_name and '/' not in instrument_name:
                formatted_pair = f"{instrument_name}_USDT"
            elif '/' in instrument_name:
                formatted_pair = instrument_name.replace('/', '_')
            else:
                formatted_pair = instrument_name
            
            # Now apply currency-specific formatting based on trading currency
            if hasattr(self, 'trading_currency') and self.trading_currency == "USD":
                # For USD balance, try USD spot formats FIRST
                if "_USDT" in formatted_pair:
                    base_currency = formatted_pair.split("_")[0]
                    # Try USD formats FIRST (highest priority)
                    possible_formats = [
                        f"{base_currency}_USD",     # SOL_USD (with underscore) - PRIORITY
                        f"{base_currency}USD",      # SOLUSD (no underscore) - PRIORITY
                        f"{base_currency}_USDT",    # Original USDT format as fallback
                    ]
                else:
                    base_currency = formatted_pair.replace('USD', '').replace('USDT', '')
                    possible_formats = [formatted_pair]
            else:
                # For USDT, use the formatted pair
                base_currency = formatted_pair.split('_')[0]
                possible_formats = [formatted_pair]
            
            logger.info(f"Creating market sell order: SELL {quantity} (trying {len(possible_formats)} formats)")
            
            # Format quantity based on coin requirements
            if base_currency in ["SUI", "BONK", "SHIB", "DOGE", "PEPE"]:
                formatted_quantity = int(float(quantity))
            elif base_currency in ["BTC", "ETH", "SOL"]:
                formatted_quantity = "{:.6f}".format(float(quantity)).rstrip('0').rstrip('.')
            else:
                formatted_quantity = "{:.2f}".format(float(quantity))
            
            # Try each format until one works
            for format_attempt in possible_formats:
                logger.info(f"Trying sell with format: {format_attempt}")
                
                method = "private/create-order"
                params = {
                    "instrument_name": format_attempt,
                    "side": "SELL",
                    "type": "MARKET",
                    "quantity": str(formatted_quantity)
                }
                
                response = self.send_request(method, params)
                
                if response.get("code") == 0:
                    order_id = response.get("result", {}).get("order_id")
                    logger.info(f"✅ SELL order successful with format: {format_attempt}")
                    if order_id:
                        logger.info(f"SELL order successfully created! Order ID: {order_id}")
                        return order_id
                    else:
                        logger.warning(f"SELL order successful, but couldn't find order ID in response")
                        return True
                elif response.get("code") == 209:  # Invalid instrument_name
                    logger.warning(f"Format {format_attempt} not valid, trying next format...")
                    continue
                else:
                    error_code = response.get("code")
                    error_msg = response.get("message", "Unknown error")
                    logger.error(f"Failed to create SELL order with format {format_attempt}. Error {error_code}: {error_msg}")
                    # Don't continue for non-format errors
                    return False
            
            # If all formats failed
            logger.error(f"All instrument name formats failed for {original_instrument}")
            logger.error(f"Tried formats: {possible_formats}")
            return False
                
        except Exception as e:
            logger.error(f"Error in sell_coin for {instrument_name}: {str(e)}")
            return False
    
    def get_order_status(self, order_id):
        """Get the status of an order"""
        try:
            method = "private/get-order-detail"
            params = {"order_id": order_id}
            
            response = self.send_request(method, params)
            
            if response.get("code") == 0:
                order_detail = response.get("result", {})
                status = order_detail.get("status")
                logger.debug(f"Order {order_id} status: {status}")
                return status
            else:
                error_code = response.get("code")
                error_msg = response.get("message", "Unknown error")
                logger.error(f"API error: {error_code} - {error_msg}")
                return None
        except Exception as e:
            logger.error(f"Error in get_order_status: {str(e)}")
            return None
    
    def get_current_price(self, instrument_name):
        """Get current price for a symbol"""
        try:
            # Follow trade_executor.py formatting logic
            original_instrument = instrument_name
            
            # Apply trade_executor.py symbol formatting first
            # Format for API: append _USDT if not already in pair format
            if '_' not in instrument_name and '/' not in instrument_name:
                formatted_pair = f"{instrument_name}_USDT"
            elif '/' in instrument_name:
                formatted_pair = instrument_name.replace('/', '_')
            else:
                formatted_pair = instrument_name
            
            # Now apply currency-specific formatting based on trading currency
            if hasattr(self, 'trading_currency') and self.trading_currency == "USD":
                # For USD balance, try USD spot formats FIRST
                if "_USDT" in formatted_pair:
                    base_currency = formatted_pair.split("_")[0]
                    # Try USD formats FIRST (highest priority)
                    possible_formats = [
                        f"{base_currency}_USD",     # SOL_USD (with underscore) - PRIORITY
                        f"{base_currency}USD",      # SOLUSD (no underscore) - PRIORITY
                        f"{base_currency}_USDT",    # Original USDT format as fallback
                    ]
                else:
                    possible_formats = [formatted_pair]
            else:
                # For USDT, use the formatted pair
                possible_formats = [formatted_pair]
            
            url = f"{self.account_base_url}public/get-ticker"
            
            # Try each format until one works
            for format_attempt in possible_formats:
                logger.debug(f"Trying price format: {format_attempt}")
                params = {"instrument_name": format_attempt}
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("code") == 0:
                        result = response_data.get("result", {})
                        data = result.get("data", [])
                        if data:
                            latest_price = float(data[0].get("a", 0))
                            logger.debug(f"✅ Current price for {format_attempt}: {latest_price}")
                            return latest_price
                    else:
                        logger.debug(f"API error for {format_attempt}: {response_data.get('message', 'Unknown')}")
                        continue
                else:
                    logger.debug(f"HTTP error for {format_attempt}: {response.status_code}")
                    continue
            
            logger.warning(f"Could not get current price for any format of {original_instrument}")
            logger.warning(f"Tried formats: {possible_formats}")
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {instrument_name}: {str(e)}")
            return None
    
    def place_tp_sl_orders(self, symbol, quantity, take_profit_price, stop_loss_price):
        """Place Take Profit and Stop Loss orders"""
        try:
            # Follow trade_executor.py formatting logic
            original_symbol = symbol
            
            # Apply trade_executor.py symbol formatting first
            # Format for API: append _USDT if not already in pair format
            if '_' not in symbol and '/' not in symbol:
                formatted_pair = f"{symbol}_USDT"
            elif '/' in symbol:
                formatted_pair = symbol.replace('/', '_')
            else:
                formatted_pair = symbol
            
            # Now apply currency-specific formatting based on trading currency
            if hasattr(self, 'trading_currency') and self.trading_currency == "USD":
                # For USD balance, try USD spot formats FIRST
                if "_USDT" in formatted_pair:
                    base_currency = formatted_pair.split("_")[0]
                    # Try USD formats FIRST (highest priority)
                    possible_formats = [
                        f"{base_currency}_USD",     # SOL_USD (with underscore) - PRIORITY
                        f"{base_currency}USD",      # SOLUSD (no underscore) - PRIORITY
                        f"{base_currency}_USDT",    # Original USDT format as fallback
                    ]
                else:
                    possible_formats = [formatted_pair]
            else:
                # For USDT, use the formatted pair
                possible_formats = [formatted_pair]
            
            logger.info(f"Placing TP/SL orders for {original_symbol}: TP={take_profit_price}, SL={stop_loss_price}")
            
            base_currency = original_symbol.split('_')[0] if '_' in original_symbol else original_symbol.replace('USD', '').replace('USDT', '')
            
            # Format quantity
            if base_currency in ["SUI", "BONK", "SHIB", "DOGE", "PEPE"]:
                formatted_quantity = str(int(float(quantity)))
            else:
                formatted_quantity = "{:.6f}".format(float(quantity)).rstrip('0').rstrip('.')
            
            tp_order_id = None
            sl_order_id = None
            
            # Try each format for TP/SL orders
            for format_attempt in possible_formats:
                logger.info(f"Trying TP/SL with format: {format_attempt}")
                
                # Take Profit Order
                tp_params = {
                    "instrument_name": format_attempt,
                    "side": "SELL",
                    "type": "LIMIT",
                    "price": "{:.8f}".format(float(take_profit_price)).rstrip('0').rstrip('.'),
                    "quantity": formatted_quantity
                }
            
                tp_response = self.send_request("private/create-order", tp_params)
                if tp_response and tp_response.get("code") == 0:
                    tp_order_id = tp_response["result"]["order_id"]
                    logger.info(f"✅ TP order placed with format {format_attempt}: {tp_order_id}")
                elif tp_response and tp_response.get("code") == 209:
                    logger.warning(f"Format {format_attempt} not valid for TP order, trying next...")
                    continue
                else:
                    logger.error(f"❌ Failed to place TP order with {format_attempt}: {tp_response}")
                    continue
                
                # Stop Loss Order (using same format that worked for TP)
                sl_params = {
                    "instrument_name": format_attempt,
                    "side": "SELL",
                    "type": "LIMIT",
                    "price": "{:.8f}".format(float(stop_loss_price)).rstrip('0').rstrip('.'),
                    "quantity": formatted_quantity
                }
                
                sl_response = self.send_request("private/create-order", sl_params)
                if sl_response and sl_response.get("code") == 0:
                    sl_order_id = sl_response["result"]["order_id"]
                    logger.info(f"✅ SL order placed with format {format_attempt}: {sl_order_id}")
                else:
                    logger.error(f"❌ Failed to place SL order with {format_attempt}: {sl_response}")
                
                # If we got here, we found a working format - break out of loop
                break
            
            if not tp_order_id and not sl_order_id:
                logger.error(f"All instrument name formats failed for TP/SL orders: {possible_formats}")
            
            return tp_order_id, sl_order_id
            
        except Exception as e:
            logger.error(f"Error placing TP/SL orders: {str(e)}")
            return None, None
    
    def cancel_order(self, order_id):
        """Cancel an order"""
        try:
            method = "private/cancel-order"
            params = {"order_id": order_id}
            
            response = self.send_request(method, params)
            
            if response.get("code") == 0:
                logger.info(f"✅ Order {order_id} cancelled successfully")
                return True
            else:
                error_code = response.get("code")
                error_msg = response.get("message", "Unknown error")
                logger.error(f"❌ Failed to cancel order {order_id}: {error_code} - {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False
    
    def execute_trade(self, trade_signal: Dict[str, Any]) -> bool:
        """Execute a trade based on signal data"""
        try:
            symbol = trade_signal.get('symbol')
            action = trade_signal.get('action')
            price = trade_signal.get('price', 0)
            confidence = trade_signal.get('confidence', 0)
            
            logger.info(f"🔄 Executing {action} for {symbol} at ${price} (confidence: {confidence}%)")
            
            # Check if auto trading is enabled
            if not self.config.trading.enable_auto_trading:
                logger.info(f"Auto trading disabled, skipping {symbol} {action}")
                return False
            
            # Execute real trade only
            return self._execute_real_trade(trade_signal)
                
        except Exception as e:
            logger.error(f"❌ Error executing trade: {str(e)}")
            return False
    
    def _execute_real_trade(self, trade_signal: Dict[str, Any]) -> bool:
        """Execute REAL trade with Crypto.com Exchange"""
        try:
            symbol = trade_signal.get('symbol')
            action = trade_signal.get('action')
            price = trade_signal.get('price', 0)
            amount = self.trade_amount
            
            logger.info(f"💰 REAL TRADE: {action} {symbol}")
            logger.info(f"   💲 Entry Price: ${price}")
            logger.info(f"   💵 Amount: ${amount} USDT")
            
            # Check sufficient balance
            if not self.has_sufficient_balance():
                logger.error(f"❌ Insufficient USDT balance for ${amount} trade")
                return False
            
            # Execute the order based on action
            order_id = None
            if action == "BUY":
                order_id = self.buy_coin(symbol, amount)
            elif action == "SELL":
                # For SELL, we need to get the quantity from current holdings
                base_currency = symbol.split('_')[0]
                balance = self.get_balance(base_currency)
                if balance <= 0:
                    logger.error(f"❌ No {base_currency} balance to sell")
                    return False
                order_id = self.sell_coin(symbol, balance)
            
            if not order_id:
                logger.error(f"❌ Failed to place {action} order for {symbol}")
                return False
            
            # Calculate TP/SL prices
            if action == "BUY":
                take_profit_price = price * (1 + self.config.trading.take_profit_percentage / 100)
                stop_loss_price = price * (1 - self.config.trading.stop_loss_percentage / 100)
            else:  # SELL
                take_profit_price = price * (1 - self.config.trading.take_profit_percentage / 100)
                stop_loss_price = price * (1 + self.config.trading.stop_loss_percentage / 100)
            
            logger.info(f"✅ {action} order placed: {order_id}")
            
            # Wait for order to be filled
            filled = self._wait_for_order_fill(order_id, symbol)
            if not filled:
                logger.error(f"❌ Order {order_id} was not filled")
                return False
            
            # Get actual executed details
            order_details = self._get_order_details(order_id)
            if order_details:
                actual_price = order_details.get('avg_price', price)
                actual_quantity = order_details.get('cumulative_quantity', 0)
                logger.info(f"📊 Actual execution: {actual_quantity} at ${actual_price}")
            else:
                actual_price = price
                actual_quantity = amount / price if action == "BUY" else amount
            
            # Place TP/SL orders only for BUY trades
            if action == "BUY" and actual_quantity > 0:
                tp_order_id, sl_order_id = self.place_tp_sl_orders(
                    symbol, actual_quantity, take_profit_price, stop_loss_price
                )
                
                # Add to active positions for monitoring
                position_data = {
                    'symbol': symbol,
                    'action': action,
                    'entry_price': actual_price,
                    'quantity': actual_quantity,
                    'take_profit': take_profit_price,
                    'stop_loss': stop_loss_price,
                    'main_order_id': order_id,
                    'tp_order_id': tp_order_id,
                    'sl_order_id': sl_order_id,
                    'timestamp': datetime.now(),
                    'status': 'ACTIVE'
                }
                
                self.active_positions[symbol] = position_data
                logger.info(f"📊 Position added to monitoring: {symbol}")
                
                # Start TP/SL monitoring if not already running
                self._start_tp_sl_monitoring()
            
            # Save to database
            trade_id = self._save_trade_to_db(trade_signal, 'EXECUTED')
            logger.info(f"✅ Real trade saved to database: ID {trade_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in real trade execution: {str(e)}")
            return False
    
    def _wait_for_order_fill(self, order_id: str, symbol: str, timeout: int = 60) -> bool:
        """Wait for order to be filled"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_order_status(order_id)
            if status == "FILLED":
                logger.info(f"✅ Order {order_id} filled for {symbol}")
                return True
            elif status in ["CANCELED", "REJECTED", "EXPIRED"]:
                logger.error(f"❌ Order {order_id} failed with status: {status}")
                return False
            
            time.sleep(2)  # Check every 2 seconds
        
        logger.warning(f"⏰ Order {order_id} fill timeout after {timeout}s")
        return False
    
    def _get_order_details(self, order_id: str) -> Optional[Dict]:
        """Get detailed order information"""
        try:
            method = "private/get-order-detail"
            params = {"order_id": order_id}
            
            response = self.send_request(method, params)
            
            if response.get("code") == 0:
                return response.get("result", {})
            else:
                logger.error(f"Failed to get order details: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting order details: {str(e)}")
            return None
    
    def _save_trade_to_db(self, trade_signal: Dict[str, Any], status: str) -> Optional[int]:
        """Save trade to database"""
        try:
            # Prepare trade data
            trade_data = {
                'symbol': trade_signal.get('symbol'),
                'side': trade_signal.get('action'),
                'amount': self.config.trading.trade_amount,
                'price': trade_signal.get('price', 0),
                'status': status,
                'confidence': trade_signal.get('confidence', 0),
                'reasoning': trade_signal.get('reasoning', ''),
                'created_at': datetime.now().isoformat()
            }
            
            # Insert into database (using schema columns)
            query = """
                INSERT INTO trade_history 
                (symbol, formatted_symbol, action, price, quantity, execution_type, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            result = self.db.execute_query(
                query, 
                (
                    trade_data['symbol'],
                    trade_data['symbol'],  # formatted_symbol same as symbol
                    trade_data['side'],    # action
                    trade_data['price'],
                    trade_data['amount'],  # quantity
                    trade_data['status'],  # execution_type
                    f"Confidence: {trade_data['confidence']}% | {trade_data['reasoning']}", # notes
                    trade_data['created_at']  # timestamp
                )
            )
            
            if result:
                logger.debug(f"Trade saved to database: {trade_data['symbol']} {trade_data['side']}")
                return 1
            else:
                logger.error(f"Failed to save trade to database")
                return None
                
        except Exception as e:
            logger.error(f"Error saving trade to database: {str(e)}")
            return None
    
    def _start_tp_sl_monitoring(self):
        """Start TP/SL monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._tp_sl_monitor_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info("🎯 TP/SL monitoring started")
    
    def _stop_tp_sl_monitoring(self):
        """Stop TP/SL monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("🛑 TP/SL monitoring stopped")
    
    def _tp_sl_monitor_loop(self):
        """Main TP/SL monitoring loop"""
        logger.info("🔄 TP/SL monitoring loop started")
        
        while self.monitoring_active:
            try:
                if not self.active_positions:
                    time.sleep(10)  # No positions to monitor
                    continue
                
                positions_to_remove = []
                
                for symbol, position in self.active_positions.items():
                    try:
                        # Get current price
                        current_price = self._get_current_price(symbol)
                        if not current_price:
                            continue
                        
                        # Check TP/SL conditions
                        should_close, reason = self._check_tp_sl_conditions(position, current_price)
                        
                        if should_close:
                            # Close position
                            self._close_position(position, current_price, reason)
                            positions_to_remove.append(symbol)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring {symbol}: {str(e)}")
                
                # Remove closed positions
                for symbol in positions_to_remove:
                    del self.active_positions[symbol]
                
                # Sleep between checks
                time.sleep(self.tp_sl_check_interval)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in TP/SL monitoring loop: {str(e)}")
                time.sleep(60)  # Wait longer on error
        
        logger.info("🏁 TP/SL monitoring loop ended")
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            # Try to use exchange API if available
            if self.exchange_api and hasattr(self.exchange_api, 'get_current_price'):
                return self.exchange_api.get_current_price(symbol)
            
            # Fallback: Use signal engine's market data provider
            try:
                from signals.signal_engine import get_signal_engine
                signal_engine = get_signal_engine(self.config, self.db)
                market_data = signal_engine.market_data_provider.get_market_data(symbol)
                if market_data:
                    return market_data.price
            except Exception as e:
                logger.debug(f"Could not get price via signal engine: {str(e)}")
            
            logger.warning(f"Could not get current price for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def _check_tp_sl_conditions(self, position: Dict[str, Any], current_price: float) -> tuple[bool, str]:
        """Check if TP or SL conditions are met"""
        try:
            action = position['action']
            entry_price = position['entry_price']
            take_profit = position['take_profit']
            stop_loss = position['stop_loss']
            
            if action == "BUY":
                # BUY position: TP above entry, SL below entry
                if current_price >= take_profit:
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    return True, f"Take Profit hit (+{profit_pct:.2f}%)"
                elif current_price <= stop_loss:
                    loss_pct = ((entry_price - current_price) / entry_price) * 100
                    return True, f"Stop Loss hit (-{loss_pct:.2f}%)"
            
            else:  # SELL position
                # SELL position: TP below entry, SL above entry
                if current_price <= take_profit:
                    profit_pct = ((entry_price - current_price) / entry_price) * 100
                    return True, f"Take Profit hit (+{profit_pct:.2f}%)"
                elif current_price >= stop_loss:
                    loss_pct = ((current_price - entry_price) / entry_price) * 100
                    return True, f"Stop Loss hit (-{loss_pct:.2f}%)"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking TP/SL conditions: {str(e)}")
            return False, ""
    
    def _close_position(self, position: Dict[str, Any], current_price: float, reason: str):
        """Close a position and cancel remaining TP/SL orders"""
        try:
            symbol = position['symbol']
            action = position['action']
            entry_price = position['entry_price']
            quantity = position.get('quantity', position.get('amount', 0))
            tp_order_id = position.get('tp_order_id')
            sl_order_id = position.get('sl_order_id')
            
            # Calculate P&L
            if action == "BUY":
                pnl_amount = (current_price - entry_price) * quantity
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:  # SELL
                pnl_amount = (entry_price - current_price) * quantity
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
            
            # Log position close
            logger.info(f"🔒 POSITION CLOSED: {symbol} {action}")
            logger.info(f"   📈 Entry: ${entry_price} → Exit: ${current_price}")
            logger.info(f"   💰 P&L: ${pnl_amount:.2f} ({pnl_percentage:+.2f}%)")
            logger.info(f"   🎯 Reason: {reason}")
            
            # Cancel remaining TP/SL orders
            cancelled_orders = []
            if tp_order_id:
                if self.cancel_order(tp_order_id):
                    cancelled_orders.append(f"TP:{tp_order_id}")
                    logger.info(f"✅ Cancelled TP order: {tp_order_id}")
                else:
                    logger.warning(f"⚠️ Failed to cancel TP order: {tp_order_id}")
            
            if sl_order_id:
                if self.cancel_order(sl_order_id):
                    cancelled_orders.append(f"SL:{sl_order_id}")
                    logger.info(f"✅ Cancelled SL order: {sl_order_id}")
                else:
                    logger.warning(f"⚠️ Failed to cancel SL order: {sl_order_id}")
            
            # Execute market sell if needed (for BUY positions)
            if action == "BUY" and quantity > 0:
                sell_order_id = self.sell_coin(symbol, quantity)
                if sell_order_id:
                    logger.info(f"✅ Market sell executed: {sell_order_id}")
                else:
                    logger.error(f"❌ Failed to execute market sell for {symbol}")
            
            # Save close trade to database
            close_trade_signal = {
                'symbol': symbol,
                'action': 'CLOSE_' + action,
                'price': current_price,
                'confidence': 100,
                'reasoning': f"{reason} | P&L: {pnl_percentage:+.2f}% | Cancelled: {', '.join(cancelled_orders)}"
            }
            
            self._save_trade_to_db(close_trade_signal, 'POSITION_CLOSED')
            
            # Update active_positions status
            position['status'] = 'CLOSED'
            position['close_price'] = current_price
            position['pnl'] = pnl_amount
            position['close_reason'] = reason
            position['cancelled_orders'] = cancelled_orders
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
    
    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active positions"""
        return self.active_positions.copy()
    
    def get_position_count(self) -> int:
        """Get number of active positions"""
        return len(self.active_positions)

# Global function for REAL trading
def execute_trade(trade_signal: Dict[str, Any]) -> bool:
    """Global execute_trade function for REAL trading with Crypto.com Exchange"""
    try:
        # Import here to avoid circular imports
        from config.config import ConfigManager
        from database.database_manager import DatabaseManager
        from config.dynamic_settings import DynamicSettingsManager
        
        config = ConfigManager()
        db = DatabaseManager(config.database.db_path)
        
        # Apply dynamic settings from database
        dynamic_settings = DynamicSettingsManager(config, db)
        dynamic_settings.apply_runtime_settings(config)
        
        # Verify that we have API credentials for real trading
        if not hasattr(config.exchange, 'api_key') or not config.exchange.api_key:
            logger.error("❌ No API key configured - Real trading requires exchange credentials")
            return False
        
        if not hasattr(config.exchange, 'api_secret') or not config.exchange.api_secret:
            logger.error("❌ No API secret configured - Real trading requires exchange credentials")
            return False
        
        # Create real trade executor
        executor = SimpleTradeExecutor(config, db)
        
        logger.info(f"🚀 Executing REAL trade via SimpleTradeExecutor")
        
        # Execute real trade
        result = executor.execute_trade(trade_signal)
        
        logger.info(f"✅ REAL trade execution result for {trade_signal.get('symbol')}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in global execute_trade function: {str(e)}")
        return False
