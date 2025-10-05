#!/usr/bin/env python3
"""
SMC Trading Bot v2.0 - Main Entry Point
Clean, Production-Ready Architecture
"""
import os
import sys

# Add src to path
sys.path.append(os.path.dirname(__file__))

from src.trading_bot import create_bot_from_env
from src.monitoring.logger import TradingLogger

def main():
    """Main entry point cho production bot"""
    logger = TradingLogger("Main")
    
    try:
        logger.info("🚀 Starting SMC Trading Bot v2.0")
        
        # Create bot từ environment variables
        bot = create_bot_from_env()
        
        if not bot:
            logger.error("❌ Failed to create bot - check .env configuration")
            return
        
        logger.info("✅ Bot created successfully - starting trading loop")
        
        # Start bot (this will run indefinitely)
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        logger.info("🏁 Bot shutdown complete")

if __name__ == "__main__":
    main()
