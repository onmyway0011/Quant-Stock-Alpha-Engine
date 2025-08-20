# 🚀 Quant Stock Alpha Engine · AI量化股票交易系统

简洁、可扩展的量化交易引擎：数据获取 → 技术/策略分析 → 实时监控与风控 → 企业微信与 n8n 通知 → Web 可视化配置。

—

## ✨ 主要特性
- 策略与技术分析
  - 支撑/阻力位、趋势、动量、成交量趋势分析（更敏感阈值）
  - 内置压力支撑策略 PressureSupportStrategy，生成买/卖/观望信号
- 实时监控与预警
  - 价格波动、成交量异常、RSI、MACD 等多类型预警
  - 监控冷却时间、防抖与阈值精细化配置
- 通知与自动化
  - 企业微信通知（支持@所有人）、自定义消息模板
  - 一键触发 n8n 工作流（Webhook / Workflow ID / API Key）
- Web 配置中心
  - 通过浏览器管理全局配置、股票监控列表与阈值
  - 一键测试：WeCom、n8n、数据库、数据源、AI分析、新闻RSS
- 风险管理
  - 最大仓位、持仓数量、止损/止盈、风险敞口与追踪止损
- 结构化配置
  - Pydantic 强类型配置，.env 环境变量注入，config.yaml 一站式管理

—

## 📂 目录结构（核心）
- src/core
  - config.py：主配置模型与加载
  - engine.py：交易引擎（整合数据/策略/监控/通知/风控）
  - stock_monitor.py / monitor.py：监控与预警
- src/strategy
  - pressure_support_strategy.py：策略与技术分析
- src/notification
  - wecom_notifier.py：企业微信与 n8n 通知
- src/web
  - config_server.py：Web 配置与 API
  - templates/：config.html、monitoring.html 等
- scripts
  - start.sh、start_web_config.py、run_tests.py 等
- tests：单元与集成测试

—

## 🚀 快速开始
1) 环境准备
- Python 3.10+
- 安装依赖：
  
  pip install -r requirements.txt

2) 配置
- 拷贝并编辑环境变量：
  
  cp .env.example .env

- 编辑配置文件：config.yaml（系统/数据源/风险/监控/通知/Web/AI/RSS）

3) 启动
- 启动 Web 配置中心（默认 127.0.0.1:8080）：
  
  python scripts/start_web_config.py

- 启动交易引擎：
  
  python main.py

4) 运行测试

  python -m pytest
  
  或
  
  python scripts/run_tests.py

—

## 🌐 Web 与 API 概览
- 页面：
  - / （首页）
  - /config（配置管理）
  - /monitoring（监控与连接测试）
- 典型 API：
  - GET /api/config（获取配置）、POST /api/config（保存配置）
  - 监控管理：/api/monitor/stocks、/api/monitor/start、/api/monitor/status 等
  - 连接测试：/api/test/wecom、/api/test/n8n、/api/test/db、/api/test/tushare、/api/test/ai、/api/test/rss

—

## 🔔 通知与工作流
- 企业微信（WeCom）
  - 启用、Webhook URL、是否@所有人（mention_all）
  - 支持交易信号、市场预警、系统状态、每日总结、自定义消息
- n8n 集成
  - 支持 base_url、api_key、webhook_url、workflow_id、timeout
  - 可从 Web UI 触发测试

—

## 📊 策略与监控要点
- 技术分析：支撑/阻力位、趋势判断、动量、成交量趋势
- 策略参数：分析周期、成交量阈值、止损/止盈、最大仓位等
- 监控阈值：价格变动、RSI、MACD、波动率、成交量倍数
- 冷却与去抖：notification_cooldown、检查/轮询间隔

—

## 🐳 部署
- Docker（示例）
  
  docker compose -f deployment/docker-compose.yml up -d

- 或直接运行脚本：
  
  bash scripts/start.sh

—

## 📄 许可证
MIT License