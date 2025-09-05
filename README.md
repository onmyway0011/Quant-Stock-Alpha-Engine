# 🚀 Quant Stock Alpha Engine · AI量化股票交易系统

简洁、可扩展的量化交易引擎：数据获取 → 技术/策略分析 → 实时监控与风控 → 企业微信与 n8n 通知 → Web 可视化配置。

—

## ✨ 主要特性
- 策略与技术分析
  - 支撑/阻力位、趋势、动量、成交量趋势分析（更敏感阈值）
  - 内置 PressureSupportStrategy，自动生成买/卖/观望信号
- 实时监控与预警
  - 价格波动、成交量异常、RSI、MACD 等多类型预警
  - 冷却时间、防抖与阈值精细化配置
- 通知与自动化
  - 企业微信通知（支持@所有人）、自定义消息模板
  - 一键触发 n8n 工作流（Webhook / Workflow ID / API Key）
- Web 配置中心
  - 浏览器管理全局配置、股票监控列表与阈值
  - 一键测试：WeCom、n8n、数据库、数据源、AI 分析、新闻 RSS
- 风险管理
  - 最大仓位、最大持仓数量、止损/止盈、风险敞口与追踪止损
- 结构化配置
  - Pydantic 强类型配置，.env 环境变量注入，config.yaml 一站式管理

—

## 📂 目录结构（核心）
- src/core
  - config.py：主配置模型与加载（Pydantic + YAML + .env）
  - engine.py：交易引擎（整合数据/策略/监控/通知/风控）
  - stock_monitor.py / monitor.py：监控与预警
- src/strategy
  - pressure_support_strategy.py：策略与技术分析
- src/notification
  - wecom_notifier.py：企业微信与 n8n 通知（异步 aiohttp 桩）
- src/web
  - config_server.py：Web 配置与 API（Flask）
  - templates/：index.html / config.html / monitoring.html / base.html / logs.html
  - static/：样式与脚本
- src/models
  - models.py：核心数据模型（信号、预警、订单状态等）
- src/utils
  - logger.py / cache.py / security.py / exceptions.py 等
- src/aiohttp
  - __init__.py：轻量 aiohttp 测试桩（ClientSession/ClientError/ClientTimeout）
- src/schedule.py
  - 轻量 schedule 测试桩，避免真实定时副作用
- scripts
  - start.sh、start_web_config.py、run_tests.py、diagnose_data_sources.py 等
- tests：单元与集成测试（pytest）
- examples：使用示例（basic_usage.py）

注：
- 为保证测试稳定，src/aiohttp 与 src/schedule 提供最小可用“测试桩”，与 tests 的 patch/导入路径对齐。
- 空目录 src/workflow 已移除（无引用）。

—

## 🚀 快速开始
1) 环境准备
- Python 3.10+
- 安装依赖：
  
  pip install -r requirements.txt

2) 配置
- 拷贝并编辑环境变量：
  
  cp .env.example .env

- 编辑配置文件：config.yaml（系统/数据源/风控/监控/通知/Web/AI/RSS）

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

## ⚙️ 配置概览
- 系统：名称、版本、时区
- 数据源：tushare、akshare、sina 等（primary/backup/realtime）
- 监控：股票列表、波动阈值、检查频率、冷却/去抖配置
- 风险管理：最大仓位、最大持仓数量、止损/止盈、追踪止损、风险容忍度
- 通知：
  - 企业微信（webhook_url、mention_all、启用开关）
  - n8n（base_url、api_key、webhook_url、workflow_id、timeout、启用开关）
- 策略：PressureSupportStrategy（短长均线、量能倍数等）
- Web：host/port
- AI 分析与新闻 RSS：可选配置

支持：
- 从 .env 注入敏感参数（如 TUSHARE_TOKEN、N8N_API_KEY 等）
- ConfigManager 管理加载/保存（Web 配置已集成）

—

## 🌐 Web 与 API
- 页面
  - /：首页
  - /config：配置管理（加载/验证/保存）
  - /monitoring：监控与连接测试
- API（典型）
  - GET /api/config：获取配置
  - POST /api/config：保存配置
  - 监控管理：/api/monitoring/stocks（GET/POST/PATCH/DELETE）
  - 连接测试：/api/test/wecom、/api/test/n8n、/api/test/db、/api/test/tushare、/api/test/ai、/api/test/rss

说明：
- /api/monitoring/test-n8n 与 /api/test/n8n 行为对齐，返回格式统一
- 监控股票 API 强化了输入校验与返回码
- 内置 _save_current_config，优先通过 ConfigManager 落盘，兜底写入 CONFIG_FILE

—

## 🔔 通知与工作流
- 企业微信（WeCom）
  - 支持交易信号、市场预警、系统状态、每日总结、自定义消息
  - 支持 @所有人（mention_all），错误处理与超时控制
- n8n 集成
  - 支持 base_url、api_key、webhook_url、workflow_id、timeout
  - 可从 Web UI 一键触发测试

—

## 📊 策略与监控要点
- 技术分析：支撑/阻力位、趋势判断、动量、成交量趋势等
- 策略参数：分析周期、量能阈值、止损/止盈、最大仓位等
- 监控阈值：价格变动、RSI、MACD、波动率、成交量倍数
- 冷却与去抖：notification_cooldown、检查/轮询间隔

—

## 🧪 测试
- 全量执行：

  python -m pytest

- 常用单测文件：
  - tests/test_web.py：Web 配置/接口
  - tests/test_notification.py：WeCom 与 NotificationManager
  - tests/test_engine.py：引擎、风控、执行器
  - tests/test_monitor.py / tests/test_stock_monitoring.py：监控与预警
  - tests/test_integration.py：端到端集成

说明：
- 测试默认使用 src/aiohttp 与 src/schedule 本地桩，确保无外部网络/调度副作用
- 如需上线使用真实 aiohttp/schedule，请替换本地桩并补充集成测试

—

## 🐳 部署
- Docker（示例）

  docker compose -f deployment/docker-compose.yml up -d

- 或直接运行脚本：

  bash scripts/start.sh

—

## ❓常见问题
- 导入 aiohttp/schedule 行为与线上不同？
  - 为保证测试稳定，本项目在 src 提供轻量“测试桩”。若线上使用真实依赖，请移除/改名本地桩并在 requirements 中保留真实库。
- Web 配置保存后未落盘？
  - 已内置 _save_current_config 优先通过 ConfigManager 持久化，若无则回写至 CONFIG_FILE。请确认写权限。
- n8n/WeCom 测试失败？
  - 使用 Web 配置中心检查 URL/key 与网络连通；日志查看 src/utils/logger 输出。

—

## 📝 规划与建议
- 将 aiohttp/schedule 桩替换为真实依赖（分支隔离 + 集成测试）
- 拆分 Web 层为更清晰的蓝图/模块化结构
- 引入任务队列（如 Celery/RQ）处理耗时通知/分析
- 增强指标与可视化（Prometheus/Grafana）

—

## 📄 许可证
MIT License