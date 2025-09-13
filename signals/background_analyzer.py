#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Background Analysis Task
7/24 sürekli çalışan coin analiz sistemi
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from .signal_engine import SignalEngine, TradingSignal
from database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class AnalysisStats:
    """Analiz istatistikleri"""
    total_coins: int = 0
    analyzed_coins: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    failed_analysis: int = 0
    last_run_time: Optional[datetime] = None
    average_analysis_time: float = 0.0

class BackgroundAnalyzer:
    """7/24 sürekli çalışan background analiz sistemi"""
    
    def __init__(self, config_manager, database_manager: DatabaseManager, telegram_bot=None):
        self.config = config_manager
        self.db = database_manager
        self.telegram_bot = telegram_bot
        self.signal_engine = SignalEngine(config_manager, database_manager)
        
        # Analiz ayarları
        self.analysis_interval = config_manager.monitoring.signal_check_interval  # 30 saniye
        self.batch_size = 5  # Aynı anda analiz edilecek coin sayısı
        
        # Cache ve takip sistemleri
        self._last_analysis_times = {}  # {symbol: timestamp}
        self._previous_signals = {}     # {symbol: signal_type}
        self._last_signal_times = {}    # {symbol: {signal_type: timestamp}} - Cooldown için
        self._failed_symbols = set()    # Başarısız analiz edilen symboller
        self._new_coins_detected = set()  # Yeni tespit edilen coinler
        
        # Cooldown ayarları
        self.signal_cooldown_minutes = 60  # Aynı yöndeki sinyal için 60 dakika cooldown
        
        # Trade execution import
        self._trade_executor_module = None
        self._load_trade_executor()
        
        # İstatistikler
        self.stats = AnalysisStats()
        
        # Control flags
        self.is_running = False
        self._stop_event = asyncio.Event()
        
        logger.info(f"Background Analyzer initialized - Analysis interval: {self.analysis_interval}s, Signal cooldown: {self.signal_cooldown_minutes}min")
    
    async def start(self):
        """Background analyzer'ı başlat"""
        if self.is_running:
            logger.warning("Background analyzer is already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        logger.info("🚀 Starting Background Analysis System - 7/24 continuous monitoring")
        
        # Başlangıç bildirimi gönder
        if self.telegram_bot:
            await self._send_startup_notification()
        
        # Ana analiz döngüsünü başlat
        await self._main_analysis_loop()
    
    async def stop(self):
        """Background analyzer'ı durdur"""
        logger.info("🛑 Stopping Background Analysis System...")
        self.is_running = False
        self._stop_event.set()
        
        # Kapanış bildirimi gönder
        if self.telegram_bot:
            await self._send_shutdown_notification()
    
    async def _main_analysis_loop(self):
        """Ana sürekli analiz döngüsü"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_running and not self._stop_event.is_set():
            cycle_start_time = time.time()
            
            try:
                # Watchlist coinlerini al
                watched_coins = self._get_watched_coins()
                
                if not watched_coins:
                    logger.debug("No coins in watchlist, waiting...")
                    await asyncio.sleep(self.analysis_interval)
                    continue
                
                self.stats.total_coins = len(watched_coins)
                logger.info(f"🔄 Starting analysis cycle for {len(watched_coins)} coins")
                
                # Yeni coinleri tespit et
                await self._detect_new_coins(watched_coins)
                
                # Coinleri analiz et (batch'ler halinde)
                await self._analyze_coins_batch(watched_coins)
                
                # İstatistikleri güncelle
                self.stats.last_run_time = datetime.now()
                cycle_time = time.time() - cycle_start_time
                self.stats.average_analysis_time = cycle_time
                
                # İstatistik mesajları kaldırıldı - sadece sinyal bildirimları gönderilecek
                
                # Başarılı döngü - error counter'ı sıfırla
                consecutive_errors = 0
                
                logger.info(f"✅ Analysis cycle completed in {cycle_time:.2f}s - Next cycle in {self.analysis_interval}s")
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ Error in analysis cycle (#{consecutive_errors}): {str(e)}")
                
                # Çok fazla hata varsa sistem durdurmayı değerlendirin
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"🚨 Too many consecutive errors ({consecutive_errors}), stopping analyzer")
                    await self._send_error_notification(f"Background analyzer stopped due to {consecutive_errors} consecutive errors")
                    break
                
                # Hata durumunda biraz daha bekle
                await asyncio.sleep(min(self.analysis_interval * 2, 60))
                continue
            
            # Bir sonraki döngüye kadar bekle
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.analysis_interval)
                break  # Stop event set edildi
            except asyncio.TimeoutError:
                continue  # Normal timeout, bir sonraki döngüye geç
        
        logger.info("🏁 Background analysis loop ended")
    
    def _get_watched_coins(self) -> List[Dict]:
        """Watchlist'teki coinleri al"""
        try:
            return self.db.get_watched_coins()
        except Exception as e:
            logger.error(f"Error getting watched coins: {str(e)}")
            return []
    
    async def _detect_new_coins(self, current_coins: List[Dict]):
        """Yeni eklenen coinleri tespit et"""
        try:
            current_symbols = {coin['symbol'] for coin in current_coins}
            
            # İlk çalıştırmada mevcut coinleri kaydet
            if not hasattr(self, '_previous_coin_set'):
                self._previous_coin_set = current_symbols
                logger.info(f"Initial watchlist loaded with {len(current_symbols)} coins")
                return
            
            # Yeni coinleri tespit et
            new_coins = current_symbols - self._previous_coin_set
            removed_coins = self._previous_coin_set - current_symbols
            
            if new_coins:
                self._new_coins_detected.update(new_coins)
                logger.info(f"🆕 New coins detected: {', '.join(new_coins)}")
                
                # Yeni coin bildirimi gönder
                if self.telegram_bot:
                    await self._send_new_coins_notification(new_coins)
            
            if removed_coins:
                logger.info(f"🗑️ Coins removed from watchlist: {', '.join(removed_coins)}")
                # Kaldırılan coinleri temizle
                for symbol in removed_coins:
                    self._last_analysis_times.pop(symbol, None)
                    self._previous_signals.pop(symbol, None)
                    self._new_coins_detected.discard(symbol)
            
            # Önceki listeyi güncelle
            self._previous_coin_set = current_symbols
            
        except Exception as e:
            logger.error(f"Error detecting new coins: {str(e)}")
    
    async def _analyze_coins_batch(self, coins: List[Dict]):
        """Coinleri batch'ler halinde analiz et"""
        self.stats.analyzed_coins = 0
        self.stats.buy_signals = 0
        self.stats.sell_signals = 0
        self.stats.failed_analysis = 0
        
        # Yeni coinleri öncelikli analiz et
        priority_coins = [coin for coin in coins if coin['symbol'] in self._new_coins_detected]
        regular_coins = [coin for coin in coins if coin['symbol'] not in self._new_coins_detected]
        
        # Önce yeni coinleri analiz et
        if priority_coins:
            logger.info(f"🎯 Analyzing {len(priority_coins)} new coins with priority")
            await self._process_coin_batch(priority_coins, is_priority=True)
        
        # Sonra diğer coinleri batch'ler halinde analiz et
        for i in range(0, len(regular_coins), self.batch_size):
            batch = regular_coins[i:i + self.batch_size]
            await self._process_coin_batch(batch, is_priority=False)
            
            # Batch'ler arası kısa bekleme
            if i + self.batch_size < len(regular_coins):
                await asyncio.sleep(1)
    
    async def _process_coin_batch(self, batch: List[Dict], is_priority: bool = False):
        """Bir batch coin'i analiz et"""
        batch_symbols = [coin['symbol'] for coin in batch]
        logger.debug(f"Processing batch: {', '.join(batch_symbols)} (Priority: {is_priority})")
        
        # Paralel analiz
        tasks = []
        for coin in batch:
            task = asyncio.create_task(self._analyze_single_coin(coin, is_priority))
            tasks.append(task)
        
        # Tüm analiz taskları için sonuçları bekle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları işle
        for coin, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error(f"Error analyzing {coin['symbol']}: {str(result)}")
                self.stats.failed_analysis += 1
                self._failed_symbols.add(coin['symbol'])
            elif result:
                self.stats.analyzed_coins += 1
                # Başarılı analiz - failed symbols'dan çıkar
                self._failed_symbols.discard(coin['symbol'])
    
    async def _analyze_single_coin(self, coin: Dict, is_priority: bool = False) -> bool:
        """Tek bir coin'i analiz et"""
        symbol = coin['symbol']
        
        try:
            # Çok sık başarısız olan coinleri atla (yeni coinler hariç)
            if not is_priority and symbol in self._failed_symbols:
                last_attempt = self._last_analysis_times.get(symbol, 0)
                if time.time() - last_attempt < 300:  # 5 dakika bekle
                    return False
            
            # Sinyal analizi yap
            signal = self.signal_engine.analyze_symbol(symbol)
            
            if not signal:
                logger.warning(f"No signal generated for {symbol}")
                return False
            
            # Analiz zamanını kaydet
            self._last_analysis_times[symbol] = time.time()
            
            # Önceki sinyal ile karşılaştır
            previous_signal = self._previous_signals.get(symbol)
            signal_changed = previous_signal != signal.signal_type
            
            # BUY veya SELL sinyali varsa bildir
            if signal.signal_type in ["BUY", "SELL"]:
                if signal.signal_type == "BUY":
                    self.stats.buy_signals += 1
                else:
                    self.stats.sell_signals += 1
                
                # Sinyal gönderilmesi kontrolü (cooldown + değişiklik)
                should_send = False
                send_reason = ""
                
                # 1. Sinyal değişti mi? (WAIT->BUY, BUY->SELL, etc.)
                if signal_changed:
                    should_send = True
                    send_reason = "Signal changed"
                # 2. Yeni coin mi?
                elif is_priority:
                    should_send = True
                    send_reason = "New coin"
                # 3. Aynı sinyal ama cooldown geçti mi?
                elif self._can_send_signal(symbol, signal.signal_type):
                    should_send = True
                    send_reason = "Cooldown expired"
                
                if should_send:
                    # Send signal notification
                    await self._send_signal_notification(signal, is_new_coin=is_priority)
                    self._record_signal_sent(symbol, signal.signal_type)
                    logger.info(f"📡 {signal.signal_type} signal sent for {symbol} ({send_reason})")
                    
                    # Execute trade if it's BUY or SELL signal
                    if signal.signal_type in ["BUY", "SELL"]:
                        trade_result = await self._execute_trade(signal)
                        if trade_result:
                            logger.info(f"💰 {signal.signal_type} trade executed for {symbol}")
                        else:
                            logger.debug(f"💤 Trade execution skipped/failed for {symbol}")
                else:
                    logger.debug(f"🔇 {signal.signal_type} signal for {symbol} suppressed (cooldown active)")
            
            # Önceki sinyali güncelle
            self._previous_signals[symbol] = signal.signal_type
            
            # Yeni coin işaretini kaldır
            if is_priority and symbol in self._new_coins_detected:
                self._new_coins_detected.remove(symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            return False
    
    def _can_send_signal(self, symbol: str, signal_type: str) -> bool:
        """Check if signal can be sent (cooldown control)"""
        try:
            current_time = time.time()
            
            # Yeni coin ise her zaman gönder
            if symbol in self._new_coins_detected:
                return True
            
            # Bu symbol için daha önce bu sinyal gönderildi mi?
            if symbol not in self._last_signal_times:
                return True
            
            symbol_signals = self._last_signal_times[symbol]
            if signal_type not in symbol_signals:
                return True
            
            # Cooldown süresini kontrol et
            last_signal_time = symbol_signals[signal_type]
            cooldown_seconds = self.signal_cooldown_minutes * 60
            time_since_last = current_time - last_signal_time
            
            if time_since_last >= cooldown_seconds:
                return True
            
            # Cooldown aktif
            remaining_minutes = (cooldown_seconds - time_since_last) / 60
            logger.debug(f"Signal cooldown active for {symbol} {signal_type}: {remaining_minutes:.1f} minutes remaining")
            return False
            
        except Exception as e:
            logger.error(f"Error checking signal cooldown for {symbol}: {str(e)}")
            return True  # Hata durumunda gönder
    
    def _record_signal_sent(self, symbol: str, signal_type: str):
        """Record that a signal was sent"""
        try:
            current_time = time.time()
            
            if symbol not in self._last_signal_times:
                self._last_signal_times[symbol] = {}
            
            self._last_signal_times[symbol][signal_type] = current_time
            logger.debug(f"Recorded signal sent: {symbol} {signal_type}")
            
        except Exception as e:
            logger.error(f"Error recording signal sent for {symbol}: {str(e)}")
    
    def _load_trade_executor(self):
        """Load trade executor module"""
        try:
            # Try to import simple trade executor first
            try:
                import simple_trade_executor
                self._trade_executor_module = simple_trade_executor
                logger.info("✅ Simple trade executor loaded successfully")
                return
            except ImportError:
                logger.warning("Simple trade executor not found, trying original...")
            
            # Fallback to original trade executor
            try:
                import trade_executor
                if hasattr(trade_executor, 'execute_trade'):
                    self._trade_executor_module = trade_executor
                    logger.info("✅ Original trade executor loaded successfully")
                else:
                    logger.warning("❌ execute_trade function not found in trade_executor.py")
                    self._trade_executor_module = None
            except Exception as e:
                logger.error(f"❌ Failed to load original trade executor: {str(e)}")
                self._trade_executor_module = None
                
        except Exception as e:
            logger.error(f"❌ Failed to setup trade executor: {str(e)}")
            self._trade_executor_module = None
    
    async def _execute_trade(self, signal: TradingSignal):
        """Execute trade based on signal"""
        try:
            # Check if auto trading is enabled
            if not self.config.trading.enable_auto_trading:
                logger.debug(f"Auto trading disabled for {signal.symbol}")
                return False
            
            # Check if trade executor is available
            if not self._trade_executor_module:
                logger.warning(f"Trade executor not available for {signal.symbol}")
                return False
            
            # Check if execute_trade function exists
            if not hasattr(self._trade_executor_module, 'execute_trade'):
                logger.error(f"execute_trade function not found in trade_executor module")
                return False
            
            # Prepare trade signal data
            trade_data = {
                'symbol': signal.symbol,
                'action': signal.signal_type,
                'price': signal.price,
                'confidence': signal.confidence,
                'original_symbol': signal.symbol,
                'row_index': 1,
                'take_profit': signal.price * (1.1 if signal.signal_type == 'BUY' else 0.9),
                'stop_loss': signal.price * (0.95 if signal.signal_type == 'BUY' else 1.05),
                'reasoning': '; '.join(signal.reasoning)
            }
            
            # Execute the trade
            logger.info(f"🔄 Executing {signal.signal_type} trade for {signal.symbol} at ${signal.price}")
            result = self._trade_executor_module.execute_trade(trade_data)
            
            if result:
                logger.info(f"✅ Trade executed successfully: {signal.symbol} {signal.signal_type}")
                
                # Send trade success notification to Telegram
                await self._send_trade_notification(signal, trade_data, success=True)
                return True
            else:
                logger.warning(f"❌ Trade execution failed: {signal.symbol} {signal.signal_type}")
                
                # Send trade failure notification to Telegram  
                await self._send_trade_notification(signal, trade_data, success=False)
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing trade for {signal.symbol}: {str(e)}")
            return False
    
    async def _send_signal_notification(self, signal: TradingSignal, is_new_coin: bool = False):
        """Sinyal bildirimi gönder"""
        if not self.telegram_bot:
            return
        
        try:
            # Signal dictionary formatına çevir
            signal_dict = {
                'action': signal.signal_type,
                'symbol': signal.symbol,
                'current_price': signal.price,
                'confidence': signal.confidence,
                'reasoning': "; ".join(signal.reasoning),
                'indicators': {
                    'rsi': signal.indicators.rsi,
                    'atr': signal.indicators.atr,
                    'volume_ratio': signal.indicators.volume_ratio
                },
                'is_new_coin': is_new_coin
            }
            
            await self.telegram_bot._send_signal_notification(signal_dict)
            
        except Exception as e:
            logger.error(f"Error sending signal notification: {str(e)}")
    
    async def _send_trade_notification(self, signal: TradingSignal, trade_data: Dict, success: bool):
        """Trade execution result notification"""
        if not self.telegram_bot:
            return
        
        try:
            # Prepare trade notification message
            action = trade_data['action']
            symbol = trade_data['symbol']
            price = trade_data['price']
            confidence = trade_data['confidence']
            take_profit = trade_data.get('take_profit', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            reasoning = trade_data.get('reasoning', 'Automated signal')
            
            if success:
                message = f"""✅ <b>Trade Executed Successfully</b>

💰 <b>{action} {symbol}</b>
• Price: ${price:.4f}
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
            
            # Send to all telegram chats
            await self._send_to_signal_chats(message)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {str(e)}")
    
    async def _send_startup_notification(self):
        """Başlangıç bildirimi"""
        try:
            message = """🚀 <b>Background Analysis Started</b>

7/24 automatic signal monitoring is now active."""
            
            await self._send_to_signal_chats(message)
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {str(e)}")
    
    async def _send_shutdown_notification(self):
        """Kapanış bildirimi"""
        try:
            message = """🛑 <b>Background Analysis Stopped</b>

Automatic signal monitoring has been stopped."""
            
            await self._send_to_signal_chats(message)
            
        except Exception as e:
            logger.error(f"Error sending shutdown notification: {str(e)}")
    
    async def _send_new_coins_notification(self, new_coins: Set[str]):
        """Yeni coin bildirimi"""
        try:
            coins_list = ", ".join(sorted(new_coins))
            message = f"""🆕 <b>New Coins Added</b>

{coins_list} - analyzing with priority..."""
            
            await self._send_to_signal_chats(message)
            
        except Exception as e:
            logger.error(f"Error sending new coins notification: {str(e)}")
    
# İstatistik güncelleme mesajları kaldırıldı - sadece sinyal bildirimları
    
    async def _send_to_signal_chats(self, message: str):
        """Send message to all configured signal chats"""
        try:
            signal_chat_ids = self.config.telegram.signal_chat_ids
            successful_sends = 0
            
            for chat_id in signal_chat_ids:
                try:
                    await self.telegram_bot.application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    successful_sends += 1
                    logger.debug(f"Message sent to signal chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send message to signal chat {chat_id}: {str(e)}")
            
            logger.info(f"Signal message sent to {successful_sends}/{len(signal_chat_ids)} chats")
            return successful_sends > 0
            
        except Exception as e:
            logger.error(f"Error in _send_to_signal_chats: {str(e)}")
            return False

    async def _send_error_notification(self, error_message: str):
        """Hata bildirimi"""
        try:
            message = f"""🚨 <b>Background Analysis Error</b>

<b>Error:</b> {error_message}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs for more details."""
            
            await self._send_to_signal_chats(message)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
    
    def get_status(self) -> Dict:
        """Background analyzer durumunu döndür"""
        return {
            'is_running': self.is_running,
            'analysis_interval': self.analysis_interval,
            'batch_size': self.batch_size,
            'stats': {
                'total_coins': self.stats.total_coins,
                'analyzed_coins': self.stats.analyzed_coins,
                'buy_signals': self.stats.buy_signals,
                'sell_signals': self.stats.sell_signals,
                'failed_analysis': self.stats.failed_analysis,
                'last_run_time': self.stats.last_run_time.isoformat() if self.stats.last_run_time else None,
                'average_analysis_time': self.stats.average_analysis_time
            },
            'failed_symbols_count': len(self._failed_symbols),
            'new_coins_pending': len(self._new_coins_detected),
            'signal_cooldown_minutes': self.signal_cooldown_minutes,
            'cooldown_active_count': len(self._last_signal_times)
        }
