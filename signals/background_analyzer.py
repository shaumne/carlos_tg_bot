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
        self._failed_symbols = set()    # Başarısız analiz edilen symboller
        self._new_coins_detected = set()  # Yeni tespit edilen coinler
        
        # İstatistikler
        self.stats = AnalysisStats()
        
        # Control flags
        self.is_running = False
        self._stop_event = asyncio.Event()
        
        logger.info(f"Background Analyzer initialized - Analysis interval: {self.analysis_interval}s")
    
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
                
                # Her 10 döngüde bir istatistik gönder
                if hasattr(self, '_cycle_count'):
                    self._cycle_count += 1
                else:
                    self._cycle_count = 1
                
                if self._cycle_count % 10 == 0:  # Her 10 döngüde bir (yaklaşık 5 dakikada)
                    await self._send_stats_update()
                
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
            signal = await self.signal_engine.analyze_symbol(symbol)
            
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
                
                # Sinyal değişti mi veya yeni coin mi?
                if signal_changed or is_priority:
                    await self._send_signal_notification(signal, is_new_coin=is_priority)
                    logger.info(f"📡 {signal.signal_type} signal sent for {symbol} (New: {is_priority}, Changed: {signal_changed})")
            
            # Önceki sinyali güncelle
            self._previous_signals[symbol] = signal.signal_type
            
            # Yeni coin işaretini kaldır
            if is_priority and symbol in self._new_coins_detected:
                self._new_coins_detected.remove(symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
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
    
    async def _send_startup_notification(self):
        """Başlangıç bildirimi"""
        try:
            message = """🚀 <b>Background Analysis System Started</b>

• <b>Status:</b> 7/24 Continuous Monitoring Active
• <b>Analysis Interval:</b> {interval} seconds
• <b>Batch Size:</b> {batch_size} coins
• <b>Start Time:</b> {time}

The system will now automatically analyze watchlist coins and send BUY/SELL signals.""".format(
                interval=self.analysis_interval,
                batch_size=self.batch_size,
                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            await self.telegram_bot._send_response_to_all_users(message)
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {str(e)}")
    
    async def _send_shutdown_notification(self):
        """Kapanış bildirimi"""
        try:
            message = f"""🛑 <b>Background Analysis System Stopped</b>

• <b>Stop Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• <b>Total Coins Analyzed:</b> {self.stats.analyzed_coins}
• <b>BUY Signals Generated:</b> {self.stats.buy_signals}
• <b>SELL Signals Generated:</b> {self.stats.sell_signals}

System monitoring has been stopped."""
            
            await self.telegram_bot._send_response_to_all_users(message)
            
        except Exception as e:
            logger.error(f"Error sending shutdown notification: {str(e)}")
    
    async def _send_new_coins_notification(self, new_coins: Set[str]):
        """Yeni coin bildirimi"""
        try:
            coins_list = ", ".join(sorted(new_coins))
            message = f"""🆕 <b>New Coins Added to Watchlist</b>

<b>Coins:</b> {coins_list}

These coins will be analyzed with priority in the next cycle."""
            
            await self.telegram_bot._send_response_to_all_users(message)
            
        except Exception as e:
            logger.error(f"Error sending new coins notification: {str(e)}")
    
    async def _send_stats_update(self):
        """İstatistik güncelleme bildirimi"""
        try:
            runtime = datetime.now() - (self.stats.last_run_time or datetime.now())
            
            message = f"""📊 <b>Analysis Statistics Update</b>

• <b>Total Coins:</b> {self.stats.total_coins}
• <b>Successfully Analyzed:</b> {self.stats.analyzed_coins}
• <b>BUY Signals:</b> {self.stats.buy_signals}
• <b>SELL Signals:</b> {self.stats.sell_signals}
• <b>Failed Analysis:</b> {self.stats.failed_analysis}
• <b>Avg Analysis Time:</b> {self.stats.average_analysis_time:.2f}s
• <b>Last Update:</b> {(self.stats.last_run_time or datetime.now()).strftime('%H:%M:%S')}

System is running continuously..."""
            
            await self.telegram_bot._send_response_to_all_users(message)
            
        except Exception as e:
            logger.error(f"Error sending stats update: {str(e)}")
    
    async def _send_error_notification(self, error_message: str):
        """Hata bildirimi"""
        try:
            message = f"""🚨 <b>Background Analysis Error</b>

<b>Error:</b> {error_message}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs for more details."""
            
            await self.telegram_bot._send_response_to_all_users(message)
            
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
            'new_coins_pending': len(self._new_coins_detected)
        }
