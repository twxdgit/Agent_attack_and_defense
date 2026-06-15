"""
大模型配置模块
支持本地Ollama + 在线API的灵活切换
"""

import os
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


class ModelProvider(Enum):
    """支持的模型提供商"""
    OLLAMA_LOCAL = "ollama_local"      # 本地Ollama
    DASHSCOPE = "dashscope"            # 通义千问
    WENXIN = "wenxin"                  # 文心一言
    DEEPSEEK = "deepseek"              # DeepSeek


@dataclass
class ProviderConfig:
    """单个模型提供商配置"""
    model_name: str
    base_url: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 1024
    enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled
        }


class ModelConfig:
    """模型配置管理"""
    
    # 默认模型名称
    DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
    DEFAULT_DASHSCOPE_MODEL = "qwen-plus"
    DEFAULT_WENXIN_MODEL = "ernie-4.0-8k-latest"
    DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
    
    def __init__(self):
        # 通义千问
        dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.dashscope = ProviderConfig(
            model_name=self.DEFAULT_DASHSCOPE_MODEL,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=dashscope_key,
            enabled=bool(dashscope_key)
        )
        
        # 文心一言
        wenxin_key = os.getenv("WENXIN_API_KEY", "")
        wenxin_secret = os.getenv("WENXIN_SECRET_KEY", "")
        self.wenxin = ProviderConfig(
            model_name=self.DEFAULT_WENXIN_MODEL,
            base_url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
            api_key=wenxin_key,
            enabled=bool(wenxin_key)
        )
        self.wenxin_secret = wenxin_secret
        
        # DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek = ProviderConfig(
            model_name=self.DEFAULT_DEEPSEEK_MODEL,
            base_url="https://api.deepseek.com/v1",
            api_key=deepseek_key,
            enabled=bool(deepseek_key)
        )
        
        # Ollama本地
        self.ollama = ProviderConfig(
            model_name=self.DEFAULT_OLLAMA_MODEL,
            base_url="http://localhost:11434",
            api_key="ollama",  # Ollama不需要真实key
            enabled=True  # 本地Ollama默认启用
        )
    
    def get_config(self, provider: ModelProvider) -> Optional[ProviderConfig]:
        """获取指定provider的配置"""
        config_map = {
            ModelProvider.OLLAMA_LOCAL: self.ollama,
            ModelProvider.DASHSCOPE: self.dashscope,
            ModelProvider.WENXIN: self.wenxin,
            ModelProvider.DEEPSEEK: self.deepseek
        }
        
        config = config_map.get(provider)
        if config and config.enabled:
            return config
        return None
    
    def get_available_providers(self) -> List[ModelProvider]:
        """获取所有可用的模型提供商"""
        return [p for p in ModelProvider 
                if self.get_config(p) is not None]
    
    def get_primary_model(self) -> Optional[tuple]:
        """获取主模型（优先本地Ollama）"""
        # 优先本地Ollama
        if self.ollama.enabled:
            return (ModelProvider.OLLAMA_LOCAL, self.ollama)
        
        # 依次尝试其他在线API
        for provider in [ModelProvider.DASHSCOPE, ModelProvider.DEEPSEEK, ModelProvider.WENXIN]:
            config = self.get_config(provider)
            if config:
                return (provider, config)
        
        return None
    
    def is_ollama_available(self) -> bool:
        """检查Ollama是否可用"""
        try:
            import ollama
            ollama.list()
            return True
        except:
            return False
    
    def get_wenxin_token(self) -> Optional[str]:
        """获取文心一言Access Token（需要额外OAuth流程）"""
        # 简化版本：直接从环境变量获取
        return os.getenv("WENXIN_ACCESS_TOKEN", "")


# 全局配置实例
model_config = ModelConfig()
