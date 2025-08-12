#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web配置界面启动脚本

启动统一的配置管理Web界面
"""

import sys
import argparse
import webbrowser
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web.config_server import ConfigServer
from src.utils.logger import setup_logger
from src.core.config import Config
from loguru import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动量化交易系统Web配置界面')
    parser.add_argument('--host', default='127.0.0.1', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    try:
        # 初始化日志
        try:
            config = Config()
            setup_logger(config)
        except Exception as e:
            # 如果配置加载失败，使用基本日志配置
            logger.add(sys.stdout, level="INFO")
            logger.warning(f"配置加载失败，使用默认日志配置: {e}")
        
        logger.info("🌐 启动Web配置界面...")
        
        # 创建配置服务器
        server = ConfigServer(host=args.host, port=args.port)
        
        # 启动服务器
        success = server.start()
        
        if not success:
            logger.error("❌ 服务器启动失败")
            sys.exit(1)
        
        server_url = server.get_url()
        logger.success(f"✅ Web配置界面已启动: {server_url}")
        
        # 自动打开浏览器
        if not args.no_browser:
            try:
                webbrowser.open(server_url)
                logger.info("🌐 已自动打开浏览器")
            except Exception as e:
                logger.warning(f"无法自动打开浏览器: {e}")
        
        print("\n" + "=" * 60)
        print("🎯 量化股票交易系统 - Web配置界面")
        print("=" * 60)
        print(f"📍 访问地址: {server_url}")
        print(f"🖥️  主机地址: {args.host}")
        print(f"🔌 端口号: {args.port}")
        print("\n📋 功能说明:")
        print("   • 统一配置管理 - 所有系统配置集中管理")
        print("   • 实时配置验证 - 配置修改即时验证")
        print("   • 连接测试 - 数据源和通知连接测试")
        print("   • 日志查看 - 实时系统日志监控")
        print("\n⚠️  注意事项:")
        print("   • 请妥善保管API密钥等敏感信息")
        print("   • 配置修改后需要重启交易系统生效")
        print("   • 建议在安全的网络环境中使用")
        print("\n🔧 操作指南:")
        print("   1. 在配置页面修改系统参数")
        print("   2. 使用连接测试验证配置")
        print("   3. 保存配置并重启交易系统")
        print("   4. 在日志页面监控系统运行状态")
        print("\n按 Ctrl+C 停止服务器")
        print("=" * 60)
        
        try:
            # 保持服务器运行
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 收到停止信号，正在关闭服务器...")
            server.stop()
            logger.success("✅ Web配置界面已停止")
            
    except Exception as e:
        logger.error(f"❌ 启动Web配置界面失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()