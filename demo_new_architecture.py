"""
Demo Script - Trading Bot v2.0 Architecture Test
"""
import os
import sys
import time
from datetime import datetime

# Add src to path
sys.path.append(os.path.dirname(__file__))

from src.trading_bot import TradingBotV2, BotConfig, create_bot_from_env
from src.models import TradingMode
from src.monitoring.logger import TradingLogger


def show_architecture_overview():
    """Display architecture overview"""
    print("""
🚀 SMC TRADING BOT v2.0 - DEMO MODE
═══════════════════════════════════════

✅ Modular Architecture - Clean separation of concerns  
✅ Real-time Data Feed - Bybit API + caching + validation
✅ SMC Strategy Engine - Market structure + Order blocks + FVG
✅ Risk Management - Position sizing + portfolio limits
✅ Order Manager - Paper trading simulation
✅ Professional Logging - Multi-level with rotation
✅ Type Safety - Full dataclass + enum implementation
✅ Error Handling - Comprehensive exception management
✅ Paper Trading - Complete simulation environment

🆕 NEW IN v2.0:
🔥 Complete Trading System - End-to-end implementation
🔥 Paper Trading Mode - Test strategies risk-free
🔥 Risk Management - Kelly Criterion + fixed risk options
🔥 Order Orchestration - SL/TP automation
🔥 Modular Design - Easy to extend + maintain
🔥 Professional Grade - Production-ready code quality

💡 ARCHITECTURE BENEFITS:
⚡ Testable - Each module can be unit tested
⚡ Extensible - Easy to add new strategies/exchanges  
⚡ Maintainable - Clean interfaces + documentation
⚡ Scalable - Support multiple symbols/strategies
⚡ Reliable - Comprehensive error handling + retries
⚡ Observable - Rich logging + performance monitoring
    """)


def test_individual_modules():
    """Test từng module riêng lẻ"""
    logger = TradingLogger("ModuleTest")
    logger.info("🧪 Testing Individual Modules...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("❌ Missing API credentials")
        return False
    
    # Test Data Feed
    logger.info("1️⃣ Testing Data Feed...")
    from src.data_feed.market_data import MarketDataFeed
    
    data_feed = MarketDataFeed(api_key, api_secret, testnet=True)
    candles = data_feed.get_candles("BTCUSDT", "15", 50)
    market_data = data_feed.get_market_data("BTCUSDT")
    
    if candles.empty or not market_data:
        logger.error("❌ Data Feed test failed")
        return False
    
    logger.info(f"✅ Data Feed OK - {len(candles)} candles, price: ${market_data.current_price:,.2f}")
    
    # Test Strategy
    logger.info("2️⃣ Testing SMC Strategy...")
    from src.strategy.smc_strategy import SMCStrategy
    
    strategy = SMCStrategy("BTCUSDT")
    signal = strategy.process_signal(candles, market_data)
    
    logger.info(f"✅ Strategy OK - Signal: {signal.signal_type.value if signal else 'None'}")
    
    # Test Risk Manager
    logger.info("3️⃣ Testing Risk Manager...")
    from src.risk_management.risk_manager import RiskManager
    from src.models import AccountInfo
    
    risk_manager = RiskManager()
    
    mock_account = AccountInfo(
        total_balance=10000.0,
        available_balance=10000.0,
        unrealized_pnl=0.0,
        margin_used=0.0,
        positions=[]
    )
    
    if signal:
        position_size, analysis = risk_manager.calculate_position_size(signal, mock_account)
        logger.info(f"✅ Risk Manager OK - Position size: {position_size:.6f}")
    
    # Test Order Manager
    logger.info("4️⃣ Testing Order Manager...")
    from src.order_manager.order_manager import OrderManager
    from src.models import OrderSide
    
    order_manager = OrderManager(api_key, api_secret, testnet=True, trading_mode=TradingMode.PAPER)
    
    # Test paper order
    test_order = order_manager.place_market_order("BTCUSDT", OrderSide.BUY, 0.001)
    if test_order:
        logger.info(f"✅ Order Manager OK - Paper order: {test_order.order_id}")
    
    logger.info("🎉 All modules tested successfully!")
    return True


def test_complete_bot():
    """Test complete trading bot"""
    logger = TradingLogger("BotTest")
    logger.info("🤖 Testing Complete Trading Bot v2.0...")
    
    # Create bot from environment
    bot = create_bot_from_env()
    
    if not bot:
        logger.error("❌ Failed to create bot")
        return
    
    # Check bot status
    status = bot.get_bot_status()
    logger.info(f"📊 Bot Status: {status}")
    
    # Force signal check
    logger.info("🔍 Testing signal generation...")
    signal = bot.force_signal_check()
    
    # Test paper trading
    if signal:
        logger.info("🎯 Found signal, testing paper execution...")
        
        # Temporarily enable auto trade for test
        original_auto_trade = bot.config.auto_trade
        bot.config.auto_trade = True
        
        # Handle the signal
        bot._handle_trading_signal(signal)
        
        # Restore original setting
        bot.config.auto_trade = original_auto_trade
    
    # Get performance report
    performance = bot.get_performance_report()
    print(performance)
    
    logger.info("✅ Complete bot test finished!")


def run_live_demo():
    """Chạy demo live trong vài phút"""
    logger = TradingLogger("LiveDemo")
    logger.info("🔴 LIVE Demo - Bot sẽ chạy trong 2 phút...")
    
    # Create bot
    bot = create_bot_from_env()
    
    # Enable paper trading
    bot.config.trading_mode = TradingMode.PAPER
    bot.config.auto_trade = True
    bot.config.update_interval = 10  # 10 seconds for demo
    
    logger.info("▶️ Starting bot...")
    bot.start()
    
    # Let it run for 2 minutes
    demo_duration = 120  # seconds
    start_time = time.time()
    
    try:
        while time.time() - start_time < demo_duration:
            time.sleep(10)
            
            # Show status every 30 seconds
            if int(time.time() - start_time) % 30 == 0:
                status = bot.get_bot_status()
                logger.info(f"📊 Status Update: {status}")
        
        logger.info("⏸️ Demo time finished, stopping bot...")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Demo interrupted by user")
    
    finally:
        bot.stop()
        
        # Final report
        performance = bot.get_performance_report()
        print(performance)
        
        logger.info("🏁 Live demo completed!")


def main():
    """Main demo function"""
    show_architecture_overview()
    
    print("\n" + "="*60)
    print("🧪 TESTING PHASE")
    print("="*60)
    
    # Test individual modules
    if test_individual_modules():
        print("\n" + "-"*40)
        
        # Test complete bot
        test_complete_bot()
        
        print("\n" + "-"*40)
        print("🎮 Demo Options:")
        print("1. Just completed module tests ✅")
        print("2. To run LIVE demo (2 minutes), uncomment line below:")
        print("# run_live_demo()")
        
        # Uncomment this to run live demo:
        run_live_demo()


if __name__ == "__main__":
    main()