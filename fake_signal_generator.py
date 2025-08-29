#!/usr/bin/env python3
"""
🧪 FAKE SIGNAL GENERATOR FOR TESTING
=====================================
Bu script sahte sinyaller üretir ve trade execution'ı test eder
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
try:
    from config.config import ConfigManager
    from config.dynamic_settings import DynamicSettingsManager
    from database.database_manager import DatabaseManager
    from signals.signal_engine import TradingSignal
    import simple_trade_executor
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    sys.exit(1)

@dataclass
class FakeSignal:
    """Sahte sinyal için data class"""
    symbol: str
    signal_type: str  # 'BUY' or 'SELL'
    price: float
    confidence: float
    reasoning: list
    volume_ratio: float = 1.2
    rsi: float = 50.0
    atr: float = 0.5

class FakeSignalGenerator:
    """Sahte sinyal üretici"""
    
    def __init__(self):
        """Initialize the fake signal generator"""
        logger.info("🧪 Initializing Fake Signal Generator...")
        
        # Load configuration
        self.config = ConfigManager()
        
        # Initialize database
        self.db = DatabaseManager(self.config.database.db_path)
        
        # Apply dynamic settings
        dynamic_settings = DynamicSettingsManager(self.config, self.db)
        dynamic_settings.apply_runtime_settings(self.config)
        
        # Initialize trade executor
        self.trade_executor = simple_trade_executor.SimpleTradeExecutor(self.config, self.db)
        
        logger.info("✅ Fake Signal Generator ready!")
    
    def create_fake_signal(self, symbol: str, signal_type: str, price: Optional[float] = None) -> TradingSignal:
        """Create a fake trading signal"""
        
        # Get current price if not provided
        if price is None:
            try:
                current_price = self.trade_executor.get_current_price(symbol)
                if current_price:
                    price = current_price
                else:
                    # Fallback to a reasonable fake price
                    price_map = {
                        'BTC_USDT': 100000.0,
                        'ETH_USDT': 3500.0,
                        'SOL_USDT': 200.0,
                        'AVAX_USDT': 25.0,
                        'ADA_USDT': 0.5,
                        'TON_USDT': 5.0,
                        'ALGO_USDT': 0.3,
                        'APT_USDT': 10.0
                    }
                    price = price_map.get(symbol, 100.0)
            except Exception as e:
                logger.warning(f"⚠️ Could not get price for {symbol}: {e}")
                price = 100.0
        
        # Create fake reasoning based on signal type
        if signal_type == 'BUY':
            reasoning = [
                "🧪 FAKE BUY SIGNAL FOR TESTING",
                "RSI oversold condition",
                "Price above key support",
                "High volume confirmation"
            ]
            confidence = 85.0
            rsi = 25.0  # Oversold
        else:  # SELL
            reasoning = [
                "🧪 FAKE SELL SIGNAL FOR TESTING", 
                "RSI overbought condition",
                "Price at resistance level",
                "Volume spike detected"
            ]
            confidence = 80.0
            rsi = 75.0  # Overbought
        
        # Import required classes
        from signals.signal_engine import TechnicalIndicators, MarketData
        
        # Create fake technical indicators
        indicators = TechnicalIndicators(
            rsi=rsi,
            atr=0.5,
            ma_20=price * 0.98,
            ma_50=price * 0.96,
            ma_200=price * 0.92,
            volume_ratio=1.3,
            current_price=price
        )
        
        # Create fake market data
        market_data = MarketData(
            symbol=symbol,
            price=price,
            volume=1000000.0,
            timestamp=datetime.now()
        )
        
        # Create TradingSignal object with correct parameters
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence / 100.0,  # Convert to 0.0-1.0 range
            price=price,
            timestamp=datetime.now(),
            indicators=indicators,
            market_data=market_data,
            reasoning=reasoning,
            risk_level="MEDIUM"
        )
        
        logger.info(f"🧪 Created fake {signal_type} signal for {symbol} at ${price:.2f}")
        return signal
    
    def execute_fake_signal(self, symbol: str, signal_type: str, price: Optional[float] = None) -> bool:
        """Execute a fake signal and return success status"""
        
        try:
            # Create fake signal
            signal = self.create_fake_signal(symbol, signal_type, price)
            
            # Prepare trade data for executor
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
            
            logger.info(f"🔄 Executing fake {signal_type} signal for {symbol}...")
            logger.info(f"📊 Signal details:")
            logger.info(f"   • Price: ${signal.price:.6f}")
            logger.info(f"   • Confidence: {signal.confidence}%")
            logger.info(f"   • TP: ${trade_data['take_profit']:.6f}")
            logger.info(f"   • SL: ${trade_data['stop_loss']:.6f}")
            
            # Execute the trade using simple_trade_executor
            result = simple_trade_executor.execute_trade(trade_data)
            
            if result:
                logger.info(f"✅ Fake signal executed successfully: {symbol} {signal_type}")
                return True
            else:
                logger.warning(f"❌ Fake signal execution failed: {symbol} {signal_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing fake signal for {symbol}: {str(e)}")
            return False
    
    def test_multiple_signals(self, test_coins: list, signal_types: list = ['BUY', 'SELL']):
        """Test multiple fake signals"""
        
        logger.info(f"🧪 Testing multiple fake signals...")
        logger.info(f"📊 Coins to test: {test_coins}")
        logger.info(f"📈 Signal types: {signal_types}")
        
        results = []
        
        for coin in test_coins:
            for signal_type in signal_types:
                logger.info(f"\n{'='*60}")
                logger.info(f"🎯 Testing {signal_type} signal for {coin}")
                logger.info(f"{'='*60}")
                
                success = self.execute_fake_signal(coin, signal_type)
                results.append({
                    'coin': coin,
                    'signal_type': signal_type,
                    'success': success
                })
                
                # Wait between signals
                logger.info("⏳ Waiting 3 seconds before next signal...")
                time.sleep(3)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📋 TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        logger.info(f"✅ Successful signals: {success_count}/{total_count}")
        logger.info(f"❌ Failed signals: {total_count - success_count}/{total_count}")
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            logger.info(f"{status} {result['coin']} {result['signal_type']}")
        
        return results
    
    def check_active_positions(self):
        """Check active positions in database"""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 CHECKING ACTIVE POSITIONS")
        logger.info(f"{'='*60}")
        
        try:
            # Get active positions from database
            positions = self.db.execute_query(
                "SELECT * FROM active_positions WHERE status = 'open' ORDER BY created_at DESC"
            )
            
            if not positions:
                logger.info("📭 No active positions found")
                return []
            
            logger.info(f"📈 Found {len(positions)} active positions:")
            
            for i, pos in enumerate(positions, 1):
                logger.info(f"Position {i}:")
                logger.info(f"  • Symbol: {pos['symbol']}")
                logger.info(f"  • Side: {pos['side']}")
                logger.info(f"  • Quantity: {pos['quantity']}")
                logger.info(f"  • Entry Price: ${pos['entry_price']:.6f}")
                logger.info(f"  • TP Price: ${pos['take_profit']:.6f}")
                logger.info(f"  • SL Price: ${pos['stop_loss']:.6f}")
                logger.info(f"  • Status: {pos['status']}")
                logger.info(f"  • Created: {pos['created_at']}")
                logger.info("")
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error checking active positions: {e}")
            return []
    
    def check_trade_history(self, limit: int = 10):
        """Check recent trade history"""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📈 CHECKING RECENT TRADE HISTORY")
        logger.info(f"{'='*60}")
        
        try:
            # Get recent trades from database
            trades = self.db.execute_query(
                "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            
            if not trades:
                logger.info("📭 No trades found in history")
                return []
            
            logger.info(f"💰 Found {len(trades)} recent trades:")
            
            for i, trade in enumerate(trades, 1):
                logger.info(f"Trade {i}:")
                logger.info(f"  • Symbol: {trade['symbol']}")
                logger.info(f"  • Action: {trade['action']}")
                logger.info(f"  • Quantity: {trade['quantity']}")
                logger.info(f"  • Price: ${trade['price']:.6f}")
                logger.info(f"  • Execution Type: {trade['execution_type']}")
                logger.info(f"  • PnL: ${trade['pnl']:.6f}")
                logger.info(f"  • Timestamp: {trade['timestamp']}")
                logger.info("")
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error checking trade history: {e}")
            return []

def main():
    """Main function"""
    
    print(f"""
{'='*80}
🧪 FAKE SIGNAL GENERATOR FOR TESTING
{'='*80}
⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    try:
        # Initialize fake signal generator
        generator = FakeSignalGenerator()
        
        # Check current system status
        logger.info(f"🔧 Current Configuration:")
        logger.info(f"  • Auto trading: {generator.config.trading.enable_auto_trading}")
        logger.info(f"  • Trade amount: ${generator.config.trading.trade_amount}")
        logger.info(f"  • Max positions: {generator.config.trading.max_positions}")
        logger.info(f"  • TP percentage: {generator.config.trading.take_profit_percentage}%")
        logger.info(f"  • SL percentage: {generator.config.trading.stop_loss_percentage}%")
        
        # Check current balance
        try:
            balance = generator.trade_executor.get_balance()
            logger.info(f"💰 Current balance: ${balance}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get balance: {e}")
        
        # Test coins from watchlist
        test_coins = ['SOL_USDT', 'BTC_USDT', 'ETH_USDT']
        
        # Show menu
        print(f"""
🎯 TEST OPTIONS:
1. Execute single BUY signal
2. Execute single SELL signal  
3. Test multiple signals
4. Check active positions only
5. Check trade history only
6. Full test (signals + check positions)
""")
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            coin = input(f"Enter coin symbol (default: SOL_USDT): ").strip() or 'SOL_USDT'
            generator.execute_fake_signal(coin, 'BUY')
            
        elif choice == '2':
            coin = input(f"Enter coin symbol (default: SOL_USDT): ").strip() or 'SOL_USDT'
            generator.execute_fake_signal(coin, 'SELL')
            
        elif choice == '3':
            generator.test_multiple_signals(test_coins)
            
        elif choice == '4':
            generator.check_active_positions()
            
        elif choice == '5':
            generator.check_trade_history()
            
        elif choice == '6':
            # Full test
            logger.info("🚀 Starting full test...")
            
            # Execute some signals
            generator.execute_fake_signal('SOL_USDT', 'BUY')
            time.sleep(2)
            generator.execute_fake_signal('BTC_USDT', 'SELL') 
            time.sleep(2)
            
            # Check results
            generator.check_active_positions()
            generator.check_trade_history()
            
        else:
            logger.error("❌ Invalid choice")
            return
        
        print(f"""
{'='*80}
🏁 FAKE SIGNAL TEST COMPLETE
{'='*80}
""")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
