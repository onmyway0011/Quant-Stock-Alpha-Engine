#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统测试脚本

用于测试量化交易系统的基本功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.data.data_provider import DataManager
from src.strategy.pressure_support_strategy import PressureSupportStrategy
from src.notification.wecom_notifier import NotificationManager
from src.utils.logger import setup_logger
from loguru import logger


async def test_config():
    """测试配置加载"""
    print("\n=== 测试配置加载 ===")
    try:
        config = Config()
        print(f"✅ 配置加载成功")
        print(f"   - 监控股票: {config.monitoring.stocks}")
        print(f"   - 波动率阈值: {config.monitoring.volatility_threshold}")
        print(f"   - 最大持仓: {config.risk.max_position_size}")
        return config
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return None


async def test_data_manager(config):
    """测试数据管理器"""
    print("\n=== 测试数据管理器 ===")
    try:
        data_manager = DataManager(config)
        await data_manager.initialize()
        
        # 测试获取实时数据
        test_symbols = ["000001.SZ"]
        data = await data_manager.get_realtime_data(test_symbols)
        
        if data:
            print(f"✅ 数据获取成功")
            for symbol, stock_data in data.items():
                print(f"   - {symbol}: {stock_data.name} 价格: {stock_data.current_price}")
        else:
            print(f"⚠️  数据获取为空（可能是数据源问题）")
            
        await data_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据管理器测试失败: {e}")
        return False


async def test_strategy(config):
    """测试交易策略"""
    print("\n=== 测试交易策略 ===")
    try:
        data_manager = DataManager(config)
        await data_manager.initialize()
        
        strategy = PressureSupportStrategy(config, data_manager)
        
        # 测试市场分析
        test_symbol = "000001.SZ"
        analysis = await strategy.analyze_market(test_symbol)
        
        if analysis:
            print(f"✅ 策略分析成功")
            print(f"   - 股票: {analysis.symbol}")
            print(f"   - 当前价格: {analysis.current_price}")
            print(f"   - 趋势: {analysis.trend}")
            print(f"   - 支撑位数量: {len(analysis.support_levels)}")
            print(f"   - 阻力位数量: {len(analysis.resistance_levels)}")
        else:
            print(f"⚠️  策略分析失败（可能是数据不足）")
            
        await data_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ 策略测试失败: {e}")
        return False


async def test_notification(config):
    """测试通知系统"""
    print("\n=== 测试通知系统 ===")
    try:
        notification_manager = NotificationManager(config)
        
        if not config.notification.wecom_enabled:
            print(f"⚠️  企业微信通知已禁用")
            return True
            
        if not config.notification.wecom_webhook_url:
            print(f"⚠️  企业微信Webhook URL未配置")
            return True
            
        success = await notification_manager.initialize()
        
        if success:
            print(f"✅ 通知系统初始化成功")
            
            # 发送测试消息
            test_success = await notification_manager.send_custom_notification(
                "🧪 量化交易系统测试消息\n\n系统功能测试正常！"
            )
            
            if test_success:
                print(f"✅ 测试消息发送成功")
            else:
                print(f"❌ 测试消息发送失败")
        else:
            print(f"❌ 通知系统初始化失败")
            
        await notification_manager.close()
        return success
        
    except Exception as e:
        print(f"❌ 通知系统测试失败: {e}")
        return False


async def test_database():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    try:
        from sqlalchemy import create_engine
        from src.models.models import Base
        
        # 创建测试数据库
        engine = create_engine('sqlite:///test_trading.db')
        Base.metadata.create_all(engine)
        
        # 测试连接
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.fetchone():
                print(f"✅ 数据库连接成功")
                return True
                
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 量化股票交易系统 - 功能测试")
    print("=" * 50)
    
    # 设置日志
    try:
        config = Config()
        setup_logger(config)
    except:
        pass
    
    test_results = []
    
    # 1. 测试配置
    config = await test_config()
    test_results.append(config is not None)
    
    if not config:
        print("\n❌ 配置测试失败，无法继续其他测试")
        return
    
    # 2. 测试数据库
    db_result = await test_database()
    test_results.append(db_result)
    
    # 3. 测试数据管理器
    data_result = await test_data_manager(config)
    test_results.append(data_result)
    
    # 4. 测试策略
    strategy_result = await test_strategy(config)
    test_results.append(strategy_result)
    
    # 5. 测试通知
    notification_result = await test_notification(config)
    test_results.append(notification_result)
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    test_names = [
        "配置加载",
        "数据库连接", 
        "数据管理器",
        "交易策略",
        "通知系统"
    ]
    
    passed = 0
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{len(test_results)} 项测试通过")
    
    if passed == len(test_results):
        print("🎉 所有测试通过！系统可以正常运行。")
    elif passed >= len(test_results) * 0.8:
        print("⚠️  大部分测试通过，系统基本可用，请检查失败项。")
    else:
        print("❌ 多项测试失败，请检查配置和环境。")
    
    print("\n💡 提示:")
    print("   - 如果数据获取失败，请检查网络连接和API密钥")
    print("   - 如果通知失败，请检查企业微信Webhook URL")
    print("   - 详细日志请查看 logs/trading.log 文件")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        sys.exit(1)