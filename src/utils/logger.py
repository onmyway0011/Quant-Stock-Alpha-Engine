#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块

提供统一的日志配置和管理
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(config, log_file: Optional[str] = None):
    """设置日志配置
    
    Args:
        config: 配置对象
        log_file: 日志文件路径（可选）
    """
    # 移除默认处理器
    logger.remove()
    
    # 获取日志配置
    log_config = getattr(config, 'logging', {}) or {}
    level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', 
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}")
    rotation = log_config.get('rotation', '1 day')
    retention = log_config.get('retention', '30 days')
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 计算日志目录与文件名
    # 优先 1) 参数 log_file，2) logging.dir/log_dir/logs_dir，3) 默认项目根 logs 目录 + 默认文件名
    project_root = Path(__file__).resolve().parents[2]
    default_log_dir = project_root / 'logs'
    cfg_log_dir = log_config.get('dir') or log_config.get('log_dir') or log_config.get('logs_dir')
    cfg_log_file_name = log_config.get('file', 'trading.log')

    # 文件输出
    if log_file:
        log_path = Path(log_file)
    else:
        log_dir = Path(cfg_log_dir) if cfg_log_dir else default_log_dir
        if not log_dir.is_absolute():
            log_dir = (project_root / log_dir).resolve()
        log_path = log_dir / cfg_log_file_name
    
    # 确保日志目录存在
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        str(log_path),
        format=log_format,
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    # 错误日志单独文件
    error_log_path = log_path.parent / "error.log"
    logger.add(
        str(error_log_path),
        format=log_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    logger.info(f"日志系统初始化完成，日志文件: {log_path}")


def get_logger(name: str):
    """获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logger: 日志器实例
    """
    return logger.bind(name=name)


class LoggerMixin:
    """日志混入类
    
    为其他类提供日志功能
    """
    
    @property
    def logger(self):
        """获取当前类的日志器"""
        return get_logger(self.__class__.__name__)


# 导出常用的日志函数
def log_trade_signal(symbol: str, action: str, price: float, quantity: int, reason: str):
    """记录交易信号"""
    logger.info(
        f"📈 交易信号 | {symbol} | {action} | 价格: {price:.2f} | 数量: {quantity} | 原因: {reason}"
    )


def log_trade_execution(symbol: str, action: str, price: float, quantity: int, status: str):
    """记录交易执行"""
    if status == "success":
        logger.success(
            f"✅ 交易执行成功 | {symbol} | {action} | 价格: {price:.2f} | 数量: {quantity}"
        )
    else:
        logger.error(
            f"❌ 交易执行失败 | {symbol} | {action} | 价格: {price:.2f} | 数量: {quantity} | 状态: {status}"
        )


def log_market_alert(symbol: str, current_price: float, volatility: float, threshold: float):
    """记录市场预警"""
    logger.warning(
        f"⚠️  市场预警 | {symbol} | 当前价格: {current_price:.2f} | "
        f"波动率: {volatility:.2%} | 阈值: {threshold:.2%}"
    )


def log_strategy_analysis(symbol: str, action: str, analysis_result: dict):
    """记录策略分析结果"""
    logger.info(
        f"🔍 策略分析 | {symbol} | 建议: {action} | 分析结果: {analysis_result}"
    )


def log_risk_check(symbol: str, risk_level: str, details: dict):
    """记录风险检查"""
    if risk_level == "high":
        logger.warning(
            f"⚠️  高风险警告 | {symbol} | 风险等级: {risk_level} | 详情: {details}"
        )
    else:
        logger.info(
            f"🛡️  风险检查 | {symbol} | 风险等级: {risk_level} | 详情: {details}"
        )


def log_notification_sent(channel: str, message: str, status: str):
    """记录通知发送"""
    if status == "success":
        logger.info(f"📱 通知发送成功 | {channel} | 消息: {message[:50]}...")
    else:
        logger.error(f"📱 通知发送失败 | {channel} | 消息: {message[:50]}... | 状态: {status}")


def log_system_status(component: str, status: str, details: str = ""):
    """记录系统状态"""
    if status == "running":
        logger.info(f"🟢 系统状态 | {component} | 状态: {status} | {details}")
    elif status == "stopped":
        logger.warning(f"🟡 系统状态 | {component} | 状态: {status} | {details}")
    else:
        logger.error(f"🔴 系统状态 | {component} | 状态: {status} | {details}")


def log_performance_metrics(metrics: dict):
    """记录性能指标"""
    logger.info(f"📊 性能指标 | {metrics}")


def log_data_update(source: str, symbol: str, timestamp: str, status: str):
    """记录数据更新"""
    if status == "success":
        logger.debug(f"📥 数据更新 | {source} | {symbol} | {timestamp} | 成功")
    else:
        logger.warning(f"📥 数据更新 | {source} | {symbol} | {timestamp} | 失败: {status}")


def log_error_with_context(error: Exception, context: dict):
    """记录带上下文的错误"""
    logger.error(
        f"💥 系统错误 | {type(error).__name__}: {str(error)} | 上下文: {context}"
    )