#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np
import ccxt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Technical analysis indicators"""
    rsi: Optional[float] = None
    atr: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    ema_10: Optional[float] = None
    ema_12: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_middle: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    volume_sma: Optional[float] = None
    current_price: Optional[float] = None
    # Volume analysis
    volume_ratio: Optional[float] = None
    volume_average: Optional[float] = None
    # Support/Resistance
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None

@dataclass
class MarketData:
    """Piyasa verisi"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None

@dataclass
class TradingSignal:
    """Trading sinyali"""
    symbol: str
    signal_type: str  # BUY, SELL, WAIT
    confidence: float  # 0.0 - 1.0
    price: float
    timestamp: datetime
    indicators: TechnicalIndicators
    market_data: MarketData
    reasoning: List[str]  # Sinyal gerekçeleri
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'ye dönüştür"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'indicators': {
                'rsi': self.indicators.rsi,
                'atr': self.indicators.atr,
                'ma_20': self.indicators.ma_20,
                'ma_50': self.indicators.ma_50,
                'ma_200': self.indicators.ma_200,
                'ema_10': self.indicators.ema_10,
                'ema_12': self.indicators.ema_12,
                'bollinger_upper': self.indicators.bollinger_upper,
                'bollinger_lower': self.indicators.bollinger_lower,
                'macd_line': self.indicators.macd_line,
                'macd_signal': self.indicators.macd_signal,
                'stoch_k': self.indicators.stoch_k,
                'stoch_d': self.indicators.stoch_d,
                'volume_ratio': self.indicators.volume_ratio,
                'volume_average': self.indicators.volume_average,
                'support_level': self.indicators.support_level,
                'resistance_level': self.indicators.resistance_level
            },
            'market_data': {
                'volume': self.market_data.volume,
                'high_24h': self.market_data.high_24h,
                'low_24h': self.market_data.low_24h,
                'change_24h': self.market_data.change_24h
            },
            'reasoning': self.reasoning,
            'risk_level': self.risk_level
        }

class TechnicalAnalyzer:
    """Teknik analiz hesaplayıcısı"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """RSI hesapla"""
        try:
            if len(prices) < period + 1:
                return None
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[:period])
            avg_loss = np.mean(losses[:period])
            
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return None
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], 
                     period: int = 14) -> Optional[float]:
        """ATR hesapla"""
        try:
            if len(highs) < period or len(lows) < period or len(closes) < period:
                return None
            
            true_ranges = []
            for i in range(1, len(closes)):
                high_low = highs[i] - lows[i]
                high_close_prev = abs(highs[i] - closes[i-1])
                low_close_prev = abs(lows[i] - closes[i-1])
                
                true_range = max(high_low, high_close_prev, low_close_prev)
                true_ranges.append(true_range)
            
            if len(true_ranges) < period:
                return None
            
            atr = np.mean(true_ranges[-period:])
            return float(atr)
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            return None
    
    @staticmethod
    def calculate_moving_average(prices: List[float], period: int) -> Optional[float]:
        """Basit hareketli ortalama"""
        try:
            if len(prices) < period:
                return None
            
            ma = np.mean(prices[-period:])
            return float(ma)
            
        except Exception as e:
            logger.error(f"Error calculating MA: {str(e)}")
            return None
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        try:
            if len(prices) < period:
                return None
            
            multiplier = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return float(ema)
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            return None
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, 
                                 std_dev: int = 2) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Bollinger Bands"""
        try:
            if len(prices) < period:
                return None, None, None
            
            middle = np.mean(prices[-period:])
            std = np.std(prices[-period:])
            
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return float(upper), float(middle), float(lower)
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            return None, None, None
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """MACD hesapla"""
        try:
            if len(prices) < slow:
                return None, None, None
            
            ema_fast = TechnicalAnalyzer.calculate_ema(prices, fast)
            ema_slow = TechnicalAnalyzer.calculate_ema(prices, slow)
            
            if ema_fast is None or ema_slow is None:
                return None, None, None
            
            macd_line = ema_fast - ema_slow
            
            # Signal line için MACD line'ın EMA'sını hesapla (basitleştirilmiş)
            signal_line = macd_line  # Gerçek hesaplama için MACD line'ın geçmişi gerekli
            histogram = macd_line - signal_line
            
            return float(macd_line), float(signal_line), float(histogram)
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return None, None, None
    
    @staticmethod
    def calculate_stochastic(highs: List[float], lows: List[float], closes: List[float],
                           k_period: int = 14, d_period: int = 3) -> Tuple[Optional[float], Optional[float]]:
        """Stochastic Oscillator"""
        try:
            if len(highs) < k_period or len(lows) < k_period or len(closes) < k_period:
                return None, None
            
            high_max = max(highs[-k_period:])
            low_min = min(lows[-k_period:])
            close_current = closes[-1]
            
            if high_max == low_min:
                k_percent = 50.0
            else:
                k_percent = ((close_current - low_min) / (high_max - low_min)) * 100
            
            # %D basit hareketli ortalama (basitleştirilmiş)
            d_percent = k_percent
            
            return float(k_percent), float(d_percent)
            
        except Exception as e:
            logger.error(f"Error calculating Stochastic: {str(e)}")
            return None, None

class MarketDataProvider:
    """Piyasa verisi sağlayıcısı (CCXT kullanarak)"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # CCXT exchange instance
        try:
            self.exchange = ccxt.binance({
                'sandbox': False,
                'rateLimit': 1200,
                'enableRateLimit': True,
            })
            logger.info("Market data provider initialized with Binance")
        except Exception as e:
            logger.error(f"Failed to initialize market data provider: {str(e)}")
            self.exchange = None
    
    def get_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 200) -> Optional[List[List]]:
        """OHLCV verilerini getir"""
        try:
            if not self.exchange:
                return None
            
            # Symbol formatını düzelt (BTC -> BTCUSDT -> BTC/USDT)
            # Eğer symbol sadece coin ismi ise USDT ekle
            if '/' not in symbol and '_' not in symbol:
                symbol = f"{symbol}USDT"
            
            # Symbol formatını düzelt (BTC_USDT veya BTCUSDT -> BTC/USDT)
            if '_' in symbol:
                formatted_symbol = symbol.replace('_', '/')
            elif 'USDT' in symbol and symbol != 'USDT':
                # BTCUSDT -> BTC/USDT
                base = symbol.replace('USDT', '')
                formatted_symbol = f"{base}/USDT"
            else:
                formatted_symbol = symbol
            
            logger.debug(f"Fetching OHLCV for symbol: {symbol} -> formatted: {formatted_symbol}")
            ohlcv = self.exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Güncel fiyat getir"""
        try:
            if not self.exchange:
                return None
            
            # Symbol formatını düzelt (BTC -> BTCUSDT -> BTC/USDT)
            # Eğer symbol sadece coin ismi ise USDT ekle
            if '/' not in symbol and '_' not in symbol:
                symbol = f"{symbol}USDT"
            
            # Symbol formatını düzelt (BTC_USDT veya BTCUSDT -> BTC/USDT)
            if '_' in symbol:
                formatted_symbol = symbol.replace('_', '/')
            elif 'USDT' in symbol and symbol != 'USDT':
                # BTCUSDT -> BTC/USDT
                base = symbol.replace('USDT', '')
                formatted_symbol = f"{base}/USDT"
            else:
                formatted_symbol = symbol
            
            logger.debug(f"Fetching price for symbol: {symbol} -> formatted: {formatted_symbol}")
            ticker = self.exchange.fetch_ticker(formatted_symbol)
            
            return float(ticker['last'])
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Detaylı piyasa verisi"""
        try:
            if not self.exchange:
                return None
            
            # Symbol formatını düzelt (BTC -> BTCUSDT -> BTC/USDT)
            # Eğer symbol sadece coin ismi ise USDT ekle
            if '/' not in symbol and '_' not in symbol:
                symbol = f"{symbol}USDT"
            
            # Symbol formatını düzelt (BTC_USDT veya BTCUSDT -> BTC/USDT)
            if '_' in symbol:
                formatted_symbol = symbol.replace('_', '/')
            elif 'USDT' in symbol and symbol != 'USDT':
                # BTCUSDT -> BTC/USDT
                base = symbol.replace('USDT', '')
                formatted_symbol = f"{base}/USDT"
            else:
                formatted_symbol = symbol
            
            logger.debug(f"Fetching market data for symbol: {symbol} -> formatted: {formatted_symbol}")
            ticker = self.exchange.fetch_ticker(formatted_symbol)
            
            market_data = MarketData(
                symbol=symbol,
                price=float(ticker['last']),
                volume=float(ticker['baseVolume']),
                timestamp=datetime.now(timezone.utc),
                high_24h=float(ticker['high']),
                low_24h=float(ticker['low']),
                change_24h=float(ticker['percentage'])
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            return None

class SignalEngine:
    """Ana sinyal üretim motoru"""
    
    def __init__(self, config_manager, database_manager):
        self.config = config_manager
        self.db = database_manager
        self.trading_config = config_manager.trading
        
        # Market data provider
        self.market_data_provider = MarketDataProvider(config_manager)
        
        # Technical analyzer
        self.analyzer = TechnicalAnalyzer()
        
        # Cache for market data
        self._price_cache = {}
        self._data_cache = {}
        self._cache_timeout = 60  # seconds
        
        # Volume tracking system (YF.py style)
        self._volume_history = {}  # {symbol: [volume1, volume2, ...]}
        self._volume_history_size = 14  # Keep last 14 periods
        
        logger.info("Signal engine initialized with volume tracking")
    
    async def get_technical_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """Get technical indicators for a symbol"""
        try:
            logger.debug(f"Getting technical indicators for: {symbol}")
            
            # Get market data
            market_data = self.market_data_provider.get_market_data(symbol)
            if not market_data:
                logger.warning(f"Could not get market data for {symbol}")
                return None
            
            # Get OHLCV data
            ohlcv_data = self.market_data_provider.get_ohlcv_data(symbol)
            if not ohlcv_data or len(ohlcv_data) < 50:
                logger.warning(f"Insufficient OHLCV data for {symbol}")
                return None
            
            # Create price lists
            opens = [float(candle[1]) for candle in ohlcv_data]
            highs = [float(candle[2]) for candle in ohlcv_data]
            lows = [float(candle[3]) for candle in ohlcv_data]
            closes = [float(candle[4]) for candle in ohlcv_data]
            volumes = [float(candle[5]) for candle in ohlcv_data]
            
            # Calculate technical indicators (with symbol for volume tracking)
            indicators = self._calculate_indicators(symbol, opens, highs, lows, closes, volumes)
            
            # Add current price to indicators
            indicators.current_price = market_data.price
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error getting technical indicators for {symbol}: {str(e)}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            market_data = self.market_data_provider.get_market_data(symbol)
            return market_data.price if market_data else None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def analyze_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Bir symbol için teknik analiz yap ve sinyal üret"""
        try:
            logger.debug(f"Analyzing symbol: {symbol}")
            
            # Market data getir
            market_data = self.market_data_provider.get_market_data(symbol)
            if not market_data:
                logger.warning(f"Could not get market data for {symbol}")
                return None
            
            # OHLCV data getir
            ohlcv_data = self.market_data_provider.get_ohlcv_data(symbol)
            if not ohlcv_data or len(ohlcv_data) < 50:
                logger.warning(f"Insufficient OHLCV data for {symbol}")
                return None
            
            # Fiyat listeleri oluştur
            opens = [float(candle[1]) for candle in ohlcv_data]
            highs = [float(candle[2]) for candle in ohlcv_data]
            lows = [float(candle[3]) for candle in ohlcv_data]
            closes = [float(candle[4]) for candle in ohlcv_data]
            volumes = [float(candle[5]) for candle in ohlcv_data]
            
            # Teknik göstergeleri hesapla (volume history içinde güncellenecek)
            indicators = self._calculate_indicators(symbol, opens, highs, lows, closes, volumes)
            
            # Update volume history for next calculation (after calculating ratio)
            current_volume = volumes[-1] if volumes else 0
            self._update_volume_history(symbol, current_volume)
            
            # Sinyal üret
            signal = self._generate_signal(symbol, market_data, indicators)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing symbol {symbol}: {str(e)}")
            return None
    
    def _calculate_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """Calculate volume ratio (current/average)"""
        try:
            # Normalize symbol for consistent tracking
            normalized_symbol = symbol.replace('/', '_').replace('-', '_')
            
            # Get volume history for this symbol
            if normalized_symbol not in self._volume_history:
                # First time seeing this symbol
                self._volume_history[normalized_symbol] = []
                return 1.0  # Default ratio
            
            volume_history = self._volume_history[normalized_symbol]
            
            if len(volume_history) == 0:
                return 1.0
            
            # Calculate average volume
            average_volume = sum(volume_history) / len(volume_history)
            
            if average_volume <= 0:
                return 1.0
            
            # Calculate ratio
            volume_ratio = current_volume / average_volume
            
            logger.debug(f"Volume ratio for {symbol}: {volume_ratio:.2f} (current: {current_volume}, avg: {average_volume})")
            
            return volume_ratio
            
        except Exception as e:
            logger.error(f"Error calculating volume ratio for {symbol}: {str(e)}")
            return 1.0
    
    def _update_volume_history(self, symbol: str, current_volume: float):
        """Update volume history for a symbol (YF.py style)"""
        try:
            # Normalize symbol for consistent tracking
            normalized_symbol = symbol.replace('/', '_').replace('-', '_')
            
            # Initialize if not exists
            if normalized_symbol not in self._volume_history:
                self._volume_history[normalized_symbol] = []
            
            # Add current volume to history
            self._volume_history[normalized_symbol].append(current_volume)
            
            # Keep only last N volumes
            if len(self._volume_history[normalized_symbol]) > self._volume_history_size:
                self._volume_history[normalized_symbol] = self._volume_history[normalized_symbol][-self._volume_history_size:]
            
            logger.debug(f"Volume history updated for {symbol}: {len(self._volume_history[normalized_symbol])} periods")
            
        except Exception as e:
            logger.error(f"Error updating volume history for {symbol}: {str(e)}")
    
    def _calculate_support_resistance(self, highs: List[float], lows: List[float]) -> Tuple[float, float]:
        """Calculate support and resistance levels"""
        try:
            if len(highs) < 10 or len(lows) < 10:
                return 0.0, 0.0
            
            # Simple support/resistance calculation
            # Support: Average of recent lows
            support = np.mean(lows[-10:]) * 0.98  # 2% buffer
            
            # Resistance: Average of recent highs  
            resistance = np.mean(highs[-10:]) * 1.02  # 2% buffer
            
            return float(support), float(resistance)
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            return 0.0, 0.0
    
    def _calculate_indicators(self, symbol: str, opens: List[float], highs: List[float], 
                            lows: List[float], closes: List[float], 
                            volumes: List[float]) -> TechnicalIndicators:
        """Tüm teknik göstergeleri hesapla"""
        try:
            indicators = TechnicalIndicators()
            
            # RSI
            indicators.rsi = self.analyzer.calculate_rsi(closes, self.trading_config.rsi_period)
            
            # ATR
            indicators.atr = self.analyzer.calculate_atr(highs, lows, closes, self.trading_config.atr_period)
            
            # Moving Averages (YF.py style)
            indicators.ma_20 = self.analyzer.calculate_moving_average(closes, self.trading_config.ma_period)
            indicators.ma_50 = self.analyzer.calculate_moving_average(closes, 50)
            indicators.ma_200 = self.analyzer.calculate_moving_average(closes, 200)
            indicators.ema_10 = self.analyzer.calculate_ema(closes, 10)
            indicators.ema_12 = self.analyzer.calculate_ema(closes, self.trading_config.ema_period)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.analyzer.calculate_bollinger_bands(closes)
            indicators.bollinger_upper = bb_upper
            indicators.bollinger_middle = bb_middle
            indicators.bollinger_lower = bb_lower
            
            # MACD
            macd_line, macd_signal, macd_hist = self.analyzer.calculate_macd(closes)
            indicators.macd_line = macd_line
            indicators.macd_signal = macd_signal
            indicators.macd_histogram = macd_hist
            
            # Stochastic
            stoch_k, stoch_d = self.analyzer.calculate_stochastic(highs, lows, closes)
            indicators.stoch_k = stoch_k
            indicators.stoch_d = stoch_d
            
            # Volume SMA
            indicators.volume_sma = self.analyzer.calculate_moving_average(volumes, 20)
            
            # Volume ratio calculation (now with correct symbol)
            current_volume = volumes[-1] if volumes else 0
            indicators.volume_ratio = self._calculate_volume_ratio(symbol, current_volume)
            indicators.volume_average = indicators.volume_sma
            
            # Support/Resistance levels
            support, resistance = self._calculate_support_resistance(highs, lows)
            indicators.support_level = support
            indicators.resistance_level = resistance
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return TechnicalIndicators()
    
    def _generate_signal(self, symbol: str, market_data: MarketData, 
                        indicators: TechnicalIndicators) -> TradingSignal:
        """YF.py tarzı gelişmiş sinyal üretim sistemi"""
        try:
            current_price = market_data.price
            signal_type = "WAIT"
            confidence = 0.5
            reasoning = []
            risk_level = "MEDIUM"
            
            # YF.py EXACT LOGIC - Moving Average conditions count
            ma200_valid = indicators.ma_200 is not None and current_price > indicators.ma_200
            ma50_valid = indicators.ma_50 is not None and current_price > indicators.ma_50
            ema10_valid = indicators.ema_10 is not None and current_price > indicators.ema_10
            
            # Count how many MA conditions are valid (YF.py exact)
            valid_ma_count = sum([ma200_valid, ma50_valid, ema10_valid])
            
            # Add reasoning for MA conditions
            if ma200_valid:
                reasoning.append("Price above MA200")
            if ma50_valid:
                reasoning.append("Price above MA50")
            if ema10_valid:
                reasoning.append("Price above EMA10")
            
            # IMPROVED BUY LOGIC - More balanced conditions
            buy_signal = False
            volume_ratio = indicators.volume_ratio or 1.0
            
            # Condition 1: RSI < 35 and at least 2 MA conditions (Strong oversold)
            if (indicators.rsi is not None and indicators.rsi < 35 and valid_ma_count >= 2):
                buy_signal = True
                reasoning.append(f"Strong BUY: RSI oversold ({indicators.rsi:.1f}) + {valid_ma_count} MA conditions")
                confidence = 0.85
            
            # Condition 2: RSI < 40 and at least 1 MA condition (Moderate oversold)
            elif (indicators.rsi is not None and indicators.rsi < 40 and valid_ma_count >= 1):
                buy_signal = True
                reasoning.append(f"Moderate BUY: RSI ({indicators.rsi:.1f}) + {valid_ma_count} MA conditions")
                confidence = 0.75
            
            # Condition 3: RSI 40-50 and all 3 MA conditions and high volume
            elif (indicators.rsi is not None and 40 <= indicators.rsi <= 50 and 
                  valid_ma_count == 3 and volume_ratio >= 1.5):
                buy_signal = True
                reasoning.append(f"Volume BUY: RSI ({indicators.rsi:.1f}) + All MA conditions + High volume ({volume_ratio:.2f}x)")
                confidence = 0.70
            
            # IMPROVED SELL LOGIC - More balanced conditions
            sell_signal = False
            
            # Condition 1: RSI > 70 (Strong overbought)
            if (indicators.rsi is not None and indicators.rsi > 70):
                sell_signal = True
                reasoning.append(f"Strong SELL: RSI overbought ({indicators.rsi:.1f})")
                confidence = 0.80
            
            # Condition 2: RSI > 65 and at least 1 MA condition violated (price below MA)
            elif (indicators.rsi is not None and indicators.rsi > 65 and valid_ma_count < 2):
                sell_signal = True
                reasoning.append(f"Moderate SELL: RSI ({indicators.rsi:.1f}) + Price below MAs ({3 - valid_ma_count} violated)")
                confidence = 0.70
            
            # Condition 3: RSI > 60 and price above resistance with high volume
            elif (indicators.rsi is not None and indicators.rsi > 60 and
                  indicators.resistance_level is not None and 
                  current_price > indicators.resistance_level and volume_ratio >= 1.3):
                sell_signal = True
                reasoning.append(f"Resistance SELL: RSI ({indicators.rsi:.1f}) + Price above resistance + Volume ({volume_ratio:.2f}x)")
                confidence = 0.75
            
            # YF.py EXACT ACTION DETERMINATION
            if buy_signal:
                signal_type = "BUY"
            elif sell_signal:
                signal_type = "SELL"
            else:
                signal_type = "WAIT"
            
            # Set proper reasoning message
            if signal_type == "WAIT" and not reasoning:
                if indicators.rsi is not None:
                    reasoning.append(f"No signal conditions met - RSI: {indicators.rsi:.1f}, MA conditions: {valid_ma_count}, Volume ratio: {volume_ratio:.2f}")
                else:
                    reasoning.append("Insufficient data for signal generation")
            
            # Set risk level based on confidence
            if signal_type in ["BUY", "SELL"]:
                risk_level = "LOW" if confidence >= 0.8 else "MEDIUM"
            else:
                risk_level = "MEDIUM"
            
            # Create signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=datetime.now(timezone.utc),
                indicators=indicators,
                market_data=market_data,
                reasoning=reasoning,
                risk_level=risk_level
            )
            
            logger.info(f"Generated YF.py-style signal for {symbol}: {signal_type} "
                       f"(confidence: {confidence:.2f}, RSI: {indicators.rsi}, MA count: {valid_ma_count}, volume_ratio: {volume_ratio:.2f})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {str(e)}")
            # Return a default WAIT signal
            return TradingSignal(
                symbol=symbol,
                signal_type="WAIT",
                confidence=0.5,
                price=current_price,
                timestamp=datetime.now(timezone.utc),
                indicators=indicators,
                market_data=market_data,
                reasoning=["Error in signal generation"],
                risk_level="HIGH"
            )
    
    def analyze_multiple_symbols(self, symbols: List[str]) -> List[TradingSignal]:
        """Çoklu symbol analizi (paralel işleme)"""
        try:
            signals = []
            
            # ThreadPoolExecutor ile paralel analiz
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {
                    executor.submit(self.analyze_symbol, symbol): symbol 
                    for symbol in symbols
                }
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        signal = future.result(timeout=30)  # 30 second timeout
                        if signal:
                            signals.append(signal)
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}: {str(e)}")
            
            # Sinyalleri confidence'a göre sırala
            signals.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Analyzed {len(signals)} symbols successfully")
            return signals
            
        except Exception as e:
            logger.error(f"Error in multiple symbol analysis: {str(e)}")
            return []
    
    def save_signal_to_db(self, signal: TradingSignal) -> bool:
        """Sinyali veritabanına kaydet"""
        try:
            signal_id = self.db.add_signal(
                symbol=signal.symbol,
                formatted_symbol=signal.symbol,
                signal_type=signal.signal_type,
                price=signal.price,
                confidence=signal.confidence,
                rsi_value=signal.indicators.rsi,
                atr_value=signal.indicators.atr,
                ma_signal="bullish" if signal.indicators.ma_20 and signal.price > signal.indicators.ma_20 else "bearish",
                ema_signal="bullish" if signal.indicators.ema_12 and signal.price > signal.indicators.ema_12 else "bearish",
                indicators=signal.to_dict(),
                notes="; ".join(signal.reasoning)
            )
            
            if signal_id > 0:
                logger.debug(f"Signal saved to database: {signal.symbol} {signal.signal_type}")
                return True
            else:
                logger.error(f"Failed to save signal to database: {signal.symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving signal to database: {str(e)}")
            return False
    
    def get_recent_signals(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """Son sinyalleri getir"""
        try:
            return self.db.get_recent_signals(symbol=symbol, limit=limit)
        except Exception as e:
            logger.error(f"Error getting recent signals: {str(e)}")
            return []
    
    def validate_signal_conditions(self, signal: TradingSignal) -> Tuple[bool, List[str]]:
        """Sinyal koşullarını doğrula"""
        try:
            issues = []
            
            # Confidence threshold
            if signal.confidence < 0.6:
                issues.append(f"Low confidence: {signal.confidence:.2f}")
            
            # Risk level check
            if signal.risk_level == "HIGH":
                issues.append("High risk signal")
            
            # Price validation
            if signal.price <= 0:
                issues.append("Invalid price")
            
            # Indicator validation
            if signal.indicators.rsi is None:
                issues.append("Missing RSI data")
            
            # Volume check
            if signal.market_data.volume <= 0:
                issues.append("No volume data")
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            logger.error(f"Error validating signal: {str(e)}")
            return False, [f"Validation error: {str(e)}"]
    
    def cleanup_old_signals(self, days: int = 7) -> bool:
        """Eski sinyalleri temizle"""
        try:
            # Bu işlevi database manager'da implement edebiliriz
            logger.info(f"Cleaning up signals older than {days} days")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up old signals: {str(e)}")
            return False

# Signal engine singleton
_signal_engine_instance = None

def get_signal_engine(config_manager, database_manager):
    """Signal engine singleton getter"""
    global _signal_engine_instance
    if _signal_engine_instance is None:
        _signal_engine_instance = SignalEngine(config_manager, database_manager)
    return _signal_engine_instance
