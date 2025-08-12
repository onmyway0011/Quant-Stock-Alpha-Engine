#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM提供商管理器

支持多种大语言模型提供商：阿里百炼、DeepSeek、Google AI、OpenRouter等
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False

from ...utils.logger import get_logger


class LLMProvider(Enum):
    """LLM提供商枚举"""
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"
    GOOGLE_AI = "google"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    extra_params: Dict[str, Any] = None


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class LLMProviderManager:
    """LLM提供商管理器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.providers = {}
        self.default_configs = self._init_default_configs()
        
    def _init_default_configs(self) -> Dict[LLMProvider, Dict[str, Any]]:
        """初始化默认配置"""
        return {
            LLMProvider.DASHSCOPE: {
                'models': {
                    'qwen-turbo': {'max_tokens': 8000, 'cost_per_1k': 0.003},
                    'qwen-plus': {'max_tokens': 32000, 'cost_per_1k': 0.008},
                    'qwen-max': {'max_tokens': 8000, 'cost_per_1k': 0.02},
                    'qwen-long': {'max_tokens': 1000000, 'cost_per_1k': 0.0005}
                },
                'base_url': 'https://dashscope.aliyuncs.com/api/v1',
                'description': '阿里百炼 - 中文优化，成本效益高'
            },
            LLMProvider.DEEPSEEK: {
                'models': {
                    'deepseek-chat': {'max_tokens': 4096, 'cost_per_1k': 0.0014},
                    'deepseek-coder': {'max_tokens': 4096, 'cost_per_1k': 0.0014}
                },
                'base_url': 'https://api.deepseek.com/v1',
                'description': 'DeepSeek - 工具调用，性价比极高'
            },
            LLMProvider.GOOGLE_AI: {
                'models': {
                    'gemini-2.0-flash-exp': {'max_tokens': 8192, 'cost_per_1k': 0.0},
                    'gemini-1.5-pro': {'max_tokens': 2097152, 'cost_per_1k': 0.0035},
                    'gemini-1.5-flash': {'max_tokens': 1048576, 'cost_per_1k': 0.00015}
                },
                'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                'description': 'Google AI - 多模态支持，推理能力强'
            },
            LLMProvider.OPENROUTER: {
                'models': {
                    'anthropic/claude-3.5-sonnet': {'max_tokens': 8192, 'cost_per_1k': 0.003},
                    'openai/gpt-4o': {'max_tokens': 4096, 'cost_per_1k': 0.005},
                    'openai/gpt-4o-mini': {'max_tokens': 16384, 'cost_per_1k': 0.00015},
                    'meta-llama/llama-3.1-405b-instruct': {'max_tokens': 4096, 'cost_per_1k': 0.003},
                    'google/gemini-2.0-flash-exp': {'max_tokens': 8192, 'cost_per_1k': 0.0}
                },
                'base_url': 'https://openrouter.ai/api/v1',
                'description': 'OpenRouter - 60+模型选择，统一API'
            },
            LLMProvider.OPENAI: {
                'models': {
                    'gpt-4o': {'max_tokens': 4096, 'cost_per_1k': 0.005},
                    'gpt-4o-mini': {'max_tokens': 16384, 'cost_per_1k': 0.00015},
                    'gpt-4-turbo': {'max_tokens': 4096, 'cost_per_1k': 0.01},
                    'gpt-3.5-turbo': {'max_tokens': 4096, 'cost_per_1k': 0.0005}
                },
                'base_url': 'https://api.openai.com/v1',
                'description': 'OpenAI - 原生GPT模型'
            }
        }
    
    def register_provider(self, config: LLMConfig) -> bool:
        """注册LLM提供商
        
        Args:
            config: LLM配置
            
        Returns:
            注册是否成功
        """
        try:
            provider_key = f"{config.provider.value}_{config.model_name}"
            
            if config.provider == LLMProvider.DASHSCOPE:
                if not DASHSCOPE_AVAILABLE:
                    self.logger.error("dashscope库未安装")
                    return False
                dashscope.api_key = config.api_key
                
            elif config.provider == LLMProvider.DEEPSEEK:
                if not OPENAI_AVAILABLE:
                    self.logger.error("openai库未安装")
                    return False
                
            elif config.provider == LLMProvider.GOOGLE_AI:
                if not GOOGLE_AI_AVAILABLE:
                    self.logger.error("google-generativeai库未安装")
                    return False
                genai.configure(api_key=config.api_key)
                
            elif config.provider in [LLMProvider.OPENROUTER, LLMProvider.OPENAI]:
                if not OPENAI_AVAILABLE:
                    self.logger.error("openai库未安装")
                    return False
            
            self.providers[provider_key] = config
            self.logger.info(f"注册LLM提供商成功: {provider_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册LLM提供商失败: {e}")
            return False
    
    async def generate_response(self, provider_key: str, prompt: str, 
                              system_prompt: str = None,
                              **kwargs) -> LLMResponse:
        """生成响应
        
        Args:
            provider_key: 提供商键值
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 额外参数
            
        Returns:
            LLM响应
        """
        if provider_key not in self.providers:
            return LLMResponse(
                content="",
                provider=provider_key,
                model="unknown",
                usage={},
                timestamp=datetime.now(),
                success=False,
                error="提供商未注册"
            )
        
        config = self.providers[provider_key]
        
        try:
            if config.provider == LLMProvider.DASHSCOPE:
                return await self._generate_dashscope_response(config, prompt, system_prompt, **kwargs)
            elif config.provider == LLMProvider.DEEPSEEK:
                return await self._generate_deepseek_response(config, prompt, system_prompt, **kwargs)
            elif config.provider == LLMProvider.GOOGLE_AI:
                return await self._generate_google_response(config, prompt, system_prompt, **kwargs)
            elif config.provider in [LLMProvider.OPENROUTER, LLMProvider.OPENAI]:
                return await self._generate_openai_compatible_response(config, prompt, system_prompt, **kwargs)
            else:
                return LLMResponse(
                    content="",
                    provider=config.provider.value,
                    model=config.model_name,
                    usage={},
                    timestamp=datetime.now(),
                    success=False,
                    error="不支持的提供商"
                )
                
        except Exception as e:
            self.logger.error(f"生成响应失败: {e}")
            return LLMResponse(
                content="",
                provider=config.provider.value,
                model=config.model_name,
                usage={},
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )
    
    async def _generate_dashscope_response(self, config: LLMConfig, prompt: str, 
                                         system_prompt: str = None, **kwargs) -> LLMResponse:
        """生成阿里百炼响应"""
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope库未安装")
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        response = await asyncio.to_thread(
            dashscope.Generation.call,
            model=config.model_name,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **kwargs
        )
        
        if response.status_code == 200:
            content = response.output.text
            usage = response.usage
            return LLMResponse(
                content=content,
                provider=config.provider.value,
                model=config.model_name,
                usage={
                    'prompt_tokens': usage.input_tokens,
                    'completion_tokens': usage.output_tokens,
                    'total_tokens': usage.total_tokens
                },
                timestamp=datetime.now(),
                success=True
            )
        else:
            raise Exception(f"DashScope API错误: {response.message}")
    
    async def _generate_deepseek_response(self, config: LLMConfig, prompt: str, 
                                        system_prompt: str = None, **kwargs) -> LLMResponse:
        """生成DeepSeek响应"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai库未安装")
        
        client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url or "https://api.deepseek.com/v1"
        )
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        response = await client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **kwargs
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=config.provider.value,
            model=config.model_name,
            usage={
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            },
            timestamp=datetime.now(),
            success=True
        )
    
    async def _generate_google_response(self, config: LLMConfig, prompt: str, 
                                      system_prompt: str = None, **kwargs) -> LLMResponse:
        """生成Google AI响应"""
        if not GOOGLE_AI_AVAILABLE:
            raise ImportError("google-generativeai库未安装")
        
        model = genai.GenerativeModel(config.model_name)
        
        # 构建提示
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens
            )
        )
        
        return LLMResponse(
            content=response.text,
            provider=config.provider.value,
            model=config.model_name,
            usage={
                'prompt_tokens': response.usage_metadata.prompt_token_count,
                'completion_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': response.usage_metadata.total_token_count
            },
            timestamp=datetime.now(),
            success=True
        )
    
    async def _generate_openai_compatible_response(self, config: LLMConfig, prompt: str, 
                                                 system_prompt: str = None, **kwargs) -> LLMResponse:
        """生成OpenAI兼容响应"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai库未安装")
        
        client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        response = await client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **kwargs
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=config.provider.value,
            model=config.model_name,
            usage={
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            },
            timestamp=datetime.now(),
            success=True
        )
    
    def get_available_providers(self) -> Dict[str, Dict]:
        """获取可用提供商
        
        Returns:
            可用提供商字典
        """
        available = {}
        
        for provider, config in self.default_configs.items():
            provider_info = {
                'name': provider.value,
                'description': config['description'],
                'models': list(config['models'].keys()),
                'available': self._check_provider_availability(provider)
            }
            available[provider.value] = provider_info
        
        return available
    
    def _check_provider_availability(self, provider: LLMProvider) -> bool:
        """检查提供商可用性"""
        if provider == LLMProvider.DASHSCOPE:
            return DASHSCOPE_AVAILABLE
        elif provider == LLMProvider.DEEPSEEK:
            return OPENAI_AVAILABLE
        elif provider == LLMProvider.GOOGLE_AI:
            return GOOGLE_AI_AVAILABLE
        elif provider in [LLMProvider.OPENROUTER, LLMProvider.OPENAI]:
            return OPENAI_AVAILABLE
        return False
    
    def get_model_info(self, provider: str, model: str) -> Optional[Dict]:
        """获取模型信息
        
        Args:
            provider: 提供商名称
            model: 模型名称
            
        Returns:
            模型信息字典
        """
        try:
            provider_enum = LLMProvider(provider)
            if provider_enum in self.default_configs:
                models = self.default_configs[provider_enum]['models']
                if model in models:
                    return models[model]
        except ValueError:
            pass
        return None
    
    def estimate_cost(self, provider: str, model: str, 
                     prompt_tokens: int, completion_tokens: int) -> float:
        """估算成本
        
        Args:
            provider: 提供商名称
            model: 模型名称
            prompt_tokens: 提示词token数
            completion_tokens: 完成token数
            
        Returns:
            估算成本（美元）
        """
        model_info = self.get_model_info(provider, model)
        if not model_info or 'cost_per_1k' not in model_info:
            return 0.0
        
        cost_per_1k = model_info['cost_per_1k']
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * cost_per_1k
    
    def get_registered_providers(self) -> List[str]:
        """获取已注册的提供商列表
        
        Returns:
            已注册提供商列表
        """
        return list(self.providers.keys())
    
    def remove_provider(self, provider_key: str) -> bool:
        """移除提供商
        
        Args:
            provider_key: 提供商键值
            
        Returns:
            移除是否成功
        """
        if provider_key in self.providers:
            del self.providers[provider_key]
            self.logger.info(f"移除LLM提供商: {provider_key}")
            return True
        return False
    
    async def test_provider(self, provider_key: str) -> Dict[str, Any]:
        """测试提供商连接
        
        Args:
            provider_key: 提供商键值
            
        Returns:
            测试结果
        """
        test_prompt = "请回复'测试成功'四个字。"
        
        start_time = datetime.now()
        response = await self.generate_response(provider_key, test_prompt)
        end_time = datetime.now()
        
        return {
            'success': response.success,
            'response_time': (end_time - start_time).total_seconds(),
            'content': response.content[:50] if response.content else '',
            'error': response.error,
            'usage': response.usage
        }
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """获取提供商统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_providers': len(self.providers),
            'available_providers': len([p for p in LLMProvider if self._check_provider_availability(p)]),
            'registered_by_provider': {},
            'total_models': 0
        }
        
        for provider_key, config in self.providers.items():
            provider_name = config.provider.value
            if provider_name not in stats['registered_by_provider']:
                stats['registered_by_provider'][provider_name] = 0
            stats['registered_by_provider'][provider_name] += 1
            stats['total_models'] += 1
        
        return stats