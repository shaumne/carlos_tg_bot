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
    
    def __init__(self, config_manager, database_manager, exchange_api=None, telegram_bot=None):
        self.config = config_manager
        self.db = database_manager
        self.exchange_api = exchange_api
        self.telegram_bot = telegram_bot
        
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
            
            # Format quantity with buffer for SL orders (reduce by 0.1% to avoid balance issues)
            available_quantity = float(quantity) * 0.999  # 0.1% buffer for fees/rounding
            
            if base_currency in ["SUI", "BONK", "SHIB", "DOGE", "PEPE"]:
                formatted_quantity = str(int(available_quantity))
            else:
                formatted_quantity = "{:.6f}".format(available_quantity).rstrip('0').rstrip('.')
            
            logger.info(f"TP/SL orders: Original quantity: {quantity}, Adjusted quantity: {formatted_quantity}")
            
            tp_order_id = None
            sl_order_id = None
            
            # Get current market price for validation
            current_market_price = self.get_current_price(original_symbol)
            if not current_market_price:
                logger.error(f"Cannot get current price for {original_symbol}, skipping TP/SL orders")
                return None, None
            
            # Validate TP/SL prices against market price (min 0.5% difference)
            min_tp_price = current_market_price * 1.005  # At least 0.5% above current
            max_tp_price = current_market_price * 1.05   # At most 5% above current
            min_sl_price = current_market_price * 0.95   # At least 5% below current  
            max_sl_price = current_market_price * 0.995  # At most 0.5% below current
            
            # Adjust TP if too close or too far
            if take_profit_price < min_tp_price:
                take_profit_price = min_tp_price
                logger.warning(f"Adjusted TP price to minimum allowed: {take_profit_price}")
            elif take_profit_price > max_tp_price:
                take_profit_price = max_tp_price
                logger.warning(f"Adjusted TP price to maximum allowed range: {take_profit_price}")
            
            # Adjust SL if too close or too far
            if stop_loss_price > max_sl_price:
                stop_loss_price = max_sl_price
                logger.warning(f"Adjusted SL price to maximum allowed: {stop_loss_price}")
            elif stop_loss_price < min_sl_price:
                stop_loss_price = min_sl_price
                logger.warning(f"Adjusted SL price to minimum allowed range: {stop_loss_price}")
            
            # Try each format for TP/SL orders
            for format_attempt in possible_formats:
                logger.info(f"Trying TP/SL with format: {format_attempt}")
                logger.info(f"Current price: {current_market_price}, TP: {take_profit_price}, SL: {stop_loss_price}")
                
                # Take Profit Order - Clean price formatting
                clean_tp_price = "{:.2f}".format(float(take_profit_price))
                tp_params = {
                    "instrument_name": format_attempt,
                    "side": "SELL",
                    "type": "LIMIT",
                    "price": clean_tp_price,
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
                
                # Stop Loss Order - Clean price formatting  
                clean_sl_price = "{:.2f}".format(float(stop_loss_price))
                sl_params = {
                    "instrument_name": format_attempt,
                    "side": "SELL",
                    "type": "LIMIT",  # Use LIMIT for now (more compatible)
                    "price": clean_sl_price,
                    "quantity": formatted_quantity
                }
                
                logger.info(f"SL Order params: {sl_params}")
                
                # Check available balance before placing SL order
                current_balance = self.get_balance(base_currency)
                logger.info(f"Available {base_currency} balance: {current_balance}, Required: {formatted_quantity}")
                
                if float(current_balance) < float(formatted_quantity):
                    logger.warning(f"❌ Insufficient {base_currency} balance for SL order: {current_balance} < {formatted_quantity}")
                    # Try with smaller quantity
                    reduced_quantity = float(formatted_quantity) * 0.95  # Reduce by 5%
                    if base_currency in ["SUI", "BONK", "SHIB", "DOGE", "PEPE"]:
                        sl_params["quantity"] = str(int(reduced_quantity))
                    else:
                        sl_params["quantity"] = "{:.6f}".format(reduced_quantity).rstrip('0').rstrip('.')
                    logger.info(f"Retrying SL with reduced quantity: {sl_params['quantity']}")
                
                sl_response = self.send_request("private/create-order", sl_params)
                if sl_response and sl_response.get("code") == 0:
                    sl_order_id = sl_response["result"]["order_id"]
                    logger.info(f"✅ SL order placed with format {format_attempt}: {sl_order_id}")
                else:
                    logger.error(f"❌ Failed to place SL order with {format_attempt}: {sl_response}")
                    # If it's still a balance issue, skip remaining formats
                    if sl_response and sl_response.get("code") == 306:  # INSUFFICIENT_AVAILABLE_BALANCE
                        logger.error(f"Balance issue persists, skipping SL order creation")
                        break
                
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
            
            # Save signal to database first
            self._save_signal_to_db(trade_signal, executed=True)
            
            # Execute real trade only
            result = self._execute_real_trade(trade_signal)
            
            # Update signal execution status in database
            if result:
                self._update_signal_execution_status(trade_signal, True, price)
            
            return result
                
        except Exception as e:
            logger.error(f"❌ Error executing trade: {str(e)}")
            # Save failed execution to database
            self._save_signal_to_db(trade_signal, executed=False)
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
                if float(balance) <= 0:
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
            
            # Wait for order to be filled with detailed logging
            logger.info(f"📋 BUY ORDER CONFIRMATION:")
            logger.info(f"   🆔 Order ID: {order_id}")
            logger.info(f"   💱 Symbol: {symbol}")
            logger.info(f"   💰 Amount: ${amount}")
            logger.info(f"   ⏳ Status: WAITING FOR FILL...")
            
            filled = self._wait_for_order_fill(order_id, symbol)
            
            if not filled:
                logger.error(f"❌ BUY ORDER FAILED:")
                logger.error(f"   🆔 Order ID: {order_id}")
                logger.error(f"   ❌ Status: NOT FILLED")
                return False
            else:
                logger.info(f"✅ BUY ORDER SUCCESS:")
                logger.info(f"   🆔 Order ID: {order_id}")
                logger.info(f"   ✅ Status: FILLED")
            
            # Get actual executed details
            order_details = self._get_order_details(order_id)
            if order_details:
                actual_price = float(order_details.get('avg_price', price))
                actual_quantity = float(order_details.get('cumulative_quantity', 0))
                logger.info(f"📊 Actual execution: {actual_quantity} at ${actual_price}")
            else:
                actual_price = float(price)
                actual_quantity = float(amount / price if action == "BUY" else amount)
            
            # Place TP/SL orders only for BUY trades
            if action == "BUY" and actual_quantity > 0:
                logger.info(f"🎯 Placing TP/SL orders for {symbol} position...")
                tp_order_id, sl_order_id = self.place_tp_sl_orders(
                    symbol, actual_quantity, take_profit_price, stop_loss_price
                )
                
                # Log TP/SL order results with confirmation
                tp_status = "✅ CREATED" if tp_order_id else "❌ FAILED"
                sl_status = "✅ CREATED" if sl_order_id else "❌ FAILED"
                logger.info(f"📋 TP/SL ORDER RESULTS:")
                logger.info(f"   🟢 Take Profit Order: {tp_status} (ID: {tp_order_id or 'None'})")
                logger.info(f"   🔴 Stop Loss Order: {sl_status} (ID: {sl_order_id or 'None'})")
                
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
                
                # Save position to active_positions table in database
                position_saved = self._save_active_position_to_db(position_data)
                if position_saved:
                    logger.info(f"💾 Position saved to database successfully")
                else:
                    logger.error(f"❌ Failed to save position to database")
                
                # Start TP/SL monitoring if not already running
                self._start_tp_sl_monitoring()
            
            # Save to database with complete information
            trade_signal_with_details = trade_signal.copy()
            trade_signal_with_details.update({
                'actual_price': actual_price,
                'actual_quantity': actual_quantity,
                'order_id': order_id,
                'take_profit': take_profit_price,
                'stop_loss': stop_loss_price
            })
            
            trade_id = self._save_trade_to_db(trade_signal_with_details, 'EXECUTED')
            logger.info(f"✅ Real trade saved to database: ID {trade_id}")
            
            # Send trade notification to Telegram if bot is available
            self._send_trade_notification_sync(trade_signal_with_details, success=True)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in real trade execution: {str(e)}")
            
            # Send failure notification
            self._send_trade_notification_sync(trade_signal, success=False)
            return False
    
    def _send_trade_notification_sync(self, trade_data: Dict[str, Any], success: bool):
        """Send trade notification to Telegram (sync version)"""
        if not self.telegram_bot:
            logger.debug("No Telegram bot available for trade notification")
            # Fallback: Log the notification that would have been sent
            action = trade_data.get('action', trade_data.get('side', 'UNKNOWN'))
            symbol = trade_data.get('symbol', 'UNKNOWN')
            price = trade_data.get('price', trade_data.get('actual_price', 0))
            
            if success:
                logger.info(f"📱 NOTIFICATION (would send to Telegram): ✅ {action} {symbol} executed at ${price}")
            else:
                logger.info(f"📱 NOTIFICATION (would send to Telegram): ❌ {action} {symbol} failed")
            return
        
        try:
            import asyncio
            import threading
            
            # Prepare notification message
            action = trade_data.get('action', trade_data.get('side', 'UNKNOWN'))
            symbol = trade_data.get('symbol', 'UNKNOWN')
            price = trade_data.get('price', trade_data.get('actual_price', 0))
            confidence = trade_data.get('confidence', 0)
            take_profit = trade_data.get('take_profit', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            reasoning = trade_data.get('reasoning', 'Direct trade execution')
            actual_quantity = trade_data.get('actual_quantity', trade_data.get('amount', 0))
            
            if success:
                message = f"""✅ <b>Trade Executed Successfully</b>

💰 <b>{action} {symbol}</b>
• Price: ${price:.4f}
• Quantity: {actual_quantity}
• Confidence: {confidence:.1f}%
• Take Profit: ${take_profit:.4f}
• Stop Loss: ${stop_loss:.4f}

📝 <b>Reasoning:</b>
{reasoning}

🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            else:
                message = f"""❌ <b>Trade Execution Failed</b>

💰 <b>{action} {symbol}</b>
• Price: ${price:.4f}
• Confidence: {confidence:.1f}%

📝 <b>Reasoning:</b>
{reasoning}

⚠️ <b>Check logs for details</b>

🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            # Send notification asynchronously
            def send_notification():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._send_telegram_message(message))
                    loop.close()
                except Exception as e:
                    logger.error(f"Error in notification thread: {str(e)}")
            
            # Run in separate thread to avoid blocking
            notification_thread = threading.Thread(target=send_notification, daemon=True)
            notification_thread.start()
            
        except Exception as e:
            logger.error(f"Error preparing trade notification: {str(e)}")
    
    async def _send_telegram_message(self, message: str):
        """Send message to Telegram chats"""
        try:
            if hasattr(self.config.telegram, 'signal_chat_ids'):
                signal_chat_ids = self.config.telegram.signal_chat_ids
                for chat_id in signal_chat_ids:
                    try:
                        await self.telegram_bot.application.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send message to chat {chat_id}: {str(e)}")
            else:
                logger.warning("No signal_chat_ids configured for notifications")
                
        except Exception as e:
            logger.error(f"Error sending telegram message: {str(e)}")
    
    def _wait_for_order_fill(self, order_id: str, symbol: str, timeout: int = 150) -> bool:
        """Wait for order to be filled (following trade_executor.py approach)"""
        logger.info(f"Starting to monitor order fill for {symbol} with order ID {order_id}")
        
        max_checks = 30  # Same as trade_executor.py
        checks = 0
        
        while checks < max_checks:
            # Get detailed order information (like trade_executor.py)
            method = "private/get-order-detail"
            params = {"order_id": order_id}
            order_detail = self.send_request(method, params)
            
            if order_detail and order_detail.get("code") == 0:
                result = order_detail.get("result", {})
                status = result.get("status")
                cumulative_quantity = float(result.get("cumulative_quantity", 0))
                
                logger.info(f"Order {order_id} status: {status}, cumulative_quantity: {cumulative_quantity}")
                
                # Order FILLED or partially executed (quantity > 0)
                if status == "FILLED":
                    logger.info(f"✅ Order {order_id} fully filled for {symbol}")
                    return True
                elif status in ["CANCELED", "REJECTED", "EXPIRED"] and cumulative_quantity > 0:
                    logger.info(f"✅ Order {order_id} partially filled: {cumulative_quantity} for {symbol}")
                    return True  # Accept partial fills like trade_executor.py
                elif status in ["CANCELED", "REJECTED", "EXPIRED"] and cumulative_quantity == 0:
                    logger.error(f"❌ Order {order_id} failed with status: {status} (no execution)")
                    return False
                else:
                    logger.debug(f"Order {order_id} status: {status}, continuing to monitor...")
            else:
                logger.warning(f"Could not get order details for {order_id}")
            
            # Wait 5 seconds between checks (like trade_executor.py)
            time.sleep(5)
            checks += 1
        
        logger.warning(f"⏰ Order {order_id} monitoring timeout after {max_checks} checks")
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
            
            # Insert into database (using schema columns) with enhanced data
            query = """
                INSERT INTO trade_history 
                (symbol, formatted_symbol, action, price, quantity, order_id, execution_type, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Use actual values if available, fallback to original
            actual_price = trade_signal.get('actual_price', trade_data['price'])
            actual_quantity = trade_signal.get('actual_quantity', trade_data['amount'])
            order_id = trade_signal.get('order_id', '')
            take_profit = trade_signal.get('take_profit', '')
            stop_loss = trade_signal.get('stop_loss', '')
            
            # Enhanced notes with all details
            notes_parts = [f"Confidence: {trade_data['confidence']}%"]
            if trade_data['reasoning']:
                notes_parts.append(trade_data['reasoning'])
            if take_profit:
                notes_parts.append(f"TP: {take_profit}")
            if stop_loss:
                notes_parts.append(f"SL: {stop_loss}")
            enhanced_notes = " | ".join(notes_parts)
            
            # Debug log the query parameters
            params = (
                trade_data['symbol'],
                trade_data['symbol'],  # formatted_symbol same as symbol
                trade_data['side'],    # action
                actual_price,          # Use actual execution price
                actual_quantity,       # Use actual executed quantity
                order_id,              # Order ID from exchange
                trade_data['status'],  # execution_type
                enhanced_notes,        # Enhanced notes with TP/SL
                trade_data['created_at']  # timestamp
            )
            
            logger.debug(f"Executing trade DB query with params: {params}")
            
            try:
                # Use execute_update for INSERT operations
                result = self.db.execute_update(query, params)
                
                if result > 0:
                    logger.debug(f"Trade saved to database: {trade_data['symbol']} {trade_data['side']}")
                    return result
                else:
                    logger.error(f"Failed to save trade to database - no rows affected: {result}")
                    return None
            except Exception as e:
                logger.error(f"Database query exception: {str(e)}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving trade to database: {str(e)}")
            return None
    
    def _save_active_position_to_db(self, position_data: Dict[str, Any]) -> Optional[int]:
        """Save active position to database"""
        try:
            # First ensure the coin exists in watched_coins table (for foreign key)
            symbol = position_data['symbol']
            self._ensure_coin_in_watched_coins(symbol)
            
            query = """
                INSERT INTO active_positions 
                (symbol, formatted_symbol, side, entry_price, quantity, stop_loss, take_profit, 
                 order_id, tp_order_id, sl_order_id, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            notes = f"Created by SimpleTradeExecutor | Status: {position_data['status']}"
            
            # Debug log the query parameters
            params = (
                position_data['symbol'],
                position_data['symbol'],  # formatted_symbol same as symbol
                position_data['action'],   # side
                position_data['entry_price'],
                position_data['quantity'],
                position_data.get('stop_loss', 0),
                position_data.get('take_profit', 0),
                position_data.get('main_order_id', ''),
                position_data.get('tp_order_id', ''),
                position_data.get('sl_order_id', ''),
                position_data['status'],
                notes
            )
            
            logger.debug(f"Executing active position DB query with params: {params}")
            
            try:
                # Use execute_update for INSERT operations
                result = self.db.execute_update(query, params)
                
                logger.info(f"Database insert result for active position: {result}")
                
                if result and result > 0:
                    logger.info(f"✅ Active position saved to database: {position_data['symbol']} (rows affected: {result})")
                    return result
                else:
                    logger.error(f"❌ Failed to save active position to database - execute_update returned: {result}")
                    logger.error(f"Query: {query}")
                    logger.error(f"Params: {params}")
                    return None
            except Exception as e:
                logger.error(f"Active position database query exception: {str(e)}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving active position to database: {str(e)}")
            return None
    
    def _ensure_coin_in_watched_coins(self, symbol: str):
        """Ensure coin exists in watched_coins table for foreign key"""
        try:
            # Check if coin already exists
            check_query = "SELECT id FROM watched_coins WHERE symbol = ?"
            result = self.db.execute_query(check_query, (symbol,))
            
            if not result:
                # Add coin to watched_coins table
                insert_query = """
                    INSERT OR IGNORE INTO watched_coins 
                    (symbol, formatted_symbol, is_active, created_by)
                    VALUES (?, ?, ?, ?)
                """
                self.db.execute_update(insert_query, (symbol, symbol, True, 'SimpleTradeExecutor'))
                logger.debug(f"Added {symbol} to watched_coins table")
            
        except Exception as e:
            logger.error(f"Error ensuring coin in watched_coins: {str(e)}")
    
    def _save_signal_to_db(self, trade_signal: Dict[str, Any], executed: bool = False) -> Optional[int]:
        """Save signal to database"""
        try:
            query = """
                INSERT INTO signals 
                (symbol, formatted_symbol, signal_type, price, confidence, executed, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            notes = f"Reasoning: {trade_signal.get('reasoning', '')}"
            
            # Debug log the query parameters
            params = (
                trade_signal.get('symbol'),
                trade_signal.get('symbol'),  # formatted_symbol same as symbol
                trade_signal.get('action'),   # signal_type
                trade_signal.get('price', 0),
                trade_signal.get('confidence', 0),
                executed,
                notes,
                datetime.now().isoformat()
            )
            
            logger.debug(f"Executing signal DB query with params: {params}")
            
            try:
                # Use execute_update for INSERT operations
                result = self.db.execute_update(query, params)
                
                if result > 0:
                    logger.debug(f"Signal saved to database: {trade_signal.get('symbol')} {trade_signal.get('action')}")
                    return result
                else:
                    logger.error(f"Failed to save signal to database - no rows affected: {result}")
                    return None
            except Exception as e:
                logger.error(f"Signal database query exception: {str(e)}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving signal to database: {str(e)}")
            return None
    
    def _update_signal_execution_status(self, trade_signal: Dict[str, Any], success: bool, execution_price: float):
        """Update signal execution status in database"""
        try:
            # This would need the signal ID, for now just log
            logger.debug(f"Signal execution updated: {trade_signal.get('symbol')} {trade_signal.get('action')} - Success: {success}")
        except Exception as e:
            logger.error(f"Error updating signal execution status: {str(e)}")
    
    def _start_tp_sl_monitoring(self):
        """Start TP/SL monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._tp_sl_monitor_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info(f"🔄 TP/SL monitoring loop started")
            logger.info(f"🎯 TP/SL monitoring started")
        else:
            logger.info(f"🎯 TP/SL monitoring already active")
    
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
            entry_price = float(position['entry_price'])
            take_profit = float(position['take_profit'])
            stop_loss = float(position['stop_loss'])
            
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
            entry_price = float(position['entry_price'])
            quantity = float(position.get('quantity', position.get('amount', 0)))
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
            if action == "BUY" and float(quantity) > 0:
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
        
        # Try to get Telegram bot instance for notifications
        telegram_bot = None
        try:
            from telegram_bot.bot_core import TelegramBot
            telegram_bot = TelegramBot(config, db)
            logger.info("✅ Telegram bot initialized for notifications")
        except ImportError as e:
            logger.debug(f"Telegram bot module not available: {str(e)}")
        except Exception as e:
            logger.warning(f"Telegram bot init failed (notifications disabled): {str(e)}")
            logger.debug(f"Telegram error details: {type(e).__name__}: {str(e)}")
        
        # Create real trade executor
        executor = SimpleTradeExecutor(config, db, telegram_bot=telegram_bot)
        
        logger.info(f"🚀 Executing REAL trade via SimpleTradeExecutor")
        
        # Execute real trade
        result = executor.execute_trade(trade_signal)
        
        logger.info(f"✅ REAL trade execution result for {trade_signal.get('symbol')}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in global execute_trade function: {str(e)}")
        return False
