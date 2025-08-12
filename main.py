#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化股票交易系统主程序

功能：
1. 股票波动监控
2. 买卖策略执行
3. 企微消息通知

Author: Quant Team
Date: 2024
"""

import asyncio
import signal
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.engine import TradingEngine
from src.core.config import Config
from src.utils.logger import setup_logger
from loguru import logger


class QuantStockAlphaEngine:
    """量化股票Alpha引擎主类"""
    
    def __init__(self):
        self.config = Config()
        self.engine = None
        self.running = False
        
    async def start(self):
        """启动系统"""
        try:
            # 设置日志
            setup_logger(self.config)
            logger.info("🚀 启动量化股票交易系统...")
            
            # 初始化交易引擎
            self.engine = TradingEngine(self.config)
            await self.engine.initialize()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 启动引擎
            self.running = True
            logger.info("✅ 系统启动成功，开始监控股票市场...")
            
            await self.engine.run()
            
        except Exception as e:
            logger.error(f"❌ 系统启动失败: {e}")
            raise
    
    async def stop(self):
        """停止系统"""
        logger.info("🛑 正在停止系统...")
        self.running = False
        
        if self.engine:
            await self.engine.stop()
            
        logger.info("✅ 系统已安全停止")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备停止系统...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    engine = QuantStockAlphaEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
    finally:
        await engine.stop()


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 运行主程序
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        sys.exit(1)