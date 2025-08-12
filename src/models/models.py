#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义

包含股票数据、交易记录等核心数据结构
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from dataclasses import dataclass


Base = declarative_base()


class TradeAction(Enum):
    """交易动作枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AlertLevel(Enum):
    """预警级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Stock(Base):
    """股票基本信息表"""
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    exchange = Column(String(10), nullable=False, comment='交易所')
    sector = Column(String(50), comment='行业')
    market_cap = Column(Float, comment='市值')
    is_active = Column(Boolean, default=True, comment='是否活跃')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    price_data = relationship("StockPrice", back_populates="stock")
    trades = relationship("Trade", back_populates="stock")
    alerts = relationship("Alert", back_populates="stock")
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}')>"


class StockPrice(Base):
    """股票价格数据表"""
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    open_price = Column(Float, nullable=False, comment='开盘价')
    high_price = Column(Float, nullable=False, comment='最高价')
    low_price = Column(Float, nullable=False, comment='最低价')
    close_price = Column(Float, nullable=False, comment='收盘价')
    volume = Column(Integer, nullable=False, comment='成交量')
    amount = Column(Float, comment='成交额')
    turnover_rate = Column(Float, comment='换手率')
    pe_ratio = Column(Float, comment='市盈率')
    pb_ratio = Column(Float, comment='市净率')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    stock = relationship("Stock", back_populates="price_data")
    
    # 索引
    __table_args__ = (
        Index('idx_stock_timestamp', 'stock_id', 'timestamp'),
        UniqueConstraint('stock_id', 'timestamp', name='uq_stock_price_timestamp')
    )
    
    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, timestamp='{self.timestamp}', close={self.close_price})>"


class Trade(Base):
    """交易记录表"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    action = Column(SQLEnum(TradeAction), nullable=False, comment='交易动作')
    quantity = Column(Integer, nullable=False, comment='交易数量')
    price = Column(Float, nullable=False, comment='交易价格')
    amount = Column(Float, nullable=False, comment='交易金额')
    commission = Column(Float, default=0.0, comment='手续费')
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, comment='订单状态')
    strategy_name = Column(String(50), comment='策略名称')
    signal_reason = Column(Text, comment='信号原因')
    executed_at = Column(DateTime, comment='执行时间')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    stock = relationship("Stock", back_populates="trades")
    
    # 索引
    __table_args__ = (
        Index('idx_stock_action_time', 'stock_id', 'action', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Trade(stock_id={self.stock_id}, action='{self.action.value}', quantity={self.quantity}, price={self.price})>"


class Position(Base):
    """持仓表"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    quantity = Column(Integer, nullable=False, comment='持仓数量')
    avg_cost = Column(Float, nullable=False, comment='平均成本')
    total_cost = Column(Float, nullable=False, comment='总成本')
    current_price = Column(Float, comment='当前价格')
    market_value = Column(Float, comment='市值')
    unrealized_pnl = Column(Float, comment='未实现盈亏')
    realized_pnl = Column(Float, default=0.0, comment='已实现盈亏')
    is_active = Column(Boolean, default=True, comment='是否活跃')
    opened_at = Column(DateTime, default=datetime.utcnow, comment='开仓时间')
    closed_at = Column(DateTime, comment='平仓时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    stock = relationship("Stock")
    
    def __repr__(self):
        return f"<Position(stock_id={self.stock_id}, quantity={self.quantity}, avg_cost={self.avg_cost})>"


class Alert(Base):
    """预警记录表"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    alert_type = Column(String(50), nullable=False, comment='预警类型')
    level = Column(SQLEnum(AlertLevel), nullable=False, comment='预警级别')
    message = Column(Text, nullable=False, comment='预警消息')
    trigger_value = Column(Float, comment='触发值')
    threshold_value = Column(Float, comment='阈值')
    is_processed = Column(Boolean, default=False, comment='是否已处理')
    processed_at = Column(DateTime, comment='处理时间')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    stock = relationship("Stock", back_populates="alerts")
    
    # 索引
    __table_args__ = (
        Index('idx_stock_level_time', 'stock_id', 'level', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Alert(stock_id={self.stock_id}, type='{self.alert_type}', level='{self.level.value}')>"


class StrategyPerformance(Base):
    """策略性能表"""
    __tablename__ = 'strategy_performance'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(50), nullable=False, comment='策略名称')
    date = Column(DateTime, nullable=False, comment='日期')
    total_trades = Column(Integer, default=0, comment='总交易次数')
    winning_trades = Column(Integer, default=0, comment='盈利交易次数')
    losing_trades = Column(Integer, default=0, comment='亏损交易次数')
    total_pnl = Column(Float, default=0.0, comment='总盈亏')
    win_rate = Column(Float, default=0.0, comment='胜率')
    avg_win = Column(Float, default=0.0, comment='平均盈利')
    avg_loss = Column(Float, default=0.0, comment='平均亏损')
    max_drawdown = Column(Float, default=0.0, comment='最大回撤')
    sharpe_ratio = Column(Float, comment='夏普比率')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_strategy_date', 'strategy_name', 'date'),
    )
    
    def __repr__(self):
        return f"<StrategyPerformance(strategy='{self.strategy_name}', date='{self.date}', pnl={self.total_pnl})>"


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(10), nullable=False, comment='日志级别')
    module = Column(String(50), nullable=False, comment='模块名称')
    message = Column(Text, nullable=False, comment='日志消息')
    details = Column(Text, comment='详细信息')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_level_module_time', 'level', 'module', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SystemLog(level='{self.level}', module='{self.module}', time='{self.created_at}')>"


# 数据传输对象 (DTO)
@dataclass
class StockData:
    """股票数据传输对象"""
    symbol: str
    name: str
    current_price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    high: Optional[float] = None
    low: Optional[float] = None
    open_price: Optional[float] = None
    

@dataclass
class TradeSignal:
    """交易信号传输对象"""
    symbol: str
    action: TradeAction
    price: float
    quantity: int
    confidence: float
    reason: str
    timestamp: datetime
    strategy: str
    

@dataclass
class MarketAlert:
    """市场预警传输对象"""
    symbol: str
    alert_type: str
    level: AlertLevel
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    

@dataclass
class PortfolioSummary:
    """投资组合摘要"""
    total_value: float
    total_cost: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    positions_count: int
    cash_balance: float
    timestamp: datetime