"""
模型管理器
统一调度本地Ollama和在线API
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from config.model_config import ModelProvider, ModelConfig, model_config

logger = logging.getLogger(__name__)


class ModelClient(ABC):
    """模型客户端基类"""
    
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送对话请求"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        pass


class OllamaClient(ModelClient):
    """本地Ollama客户端"""
    
    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self._client = None
        self._check_connection()
    
    def _check_connection(self):
        """检查Ollama连接"""
        try:
            import ollama
            self._client = ollama
            # 尝试列出模型
            self._client.list()
            logger.info("Ollama连接成功")
        except Exception as e:
            logger.warning(f"Ollama连接失败: {e}")
            self._client = None
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """通过Ollama API调用本地模型"""
        if self._client is None:
            return self._error_response("Ollama未连接")
        
        try:
            prompt = self._format_prompt(messages)
            
            response = self._client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 512)
                }
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama调用失败: {e}")
            return self._error_response(str(e))
    
    def _format_prompt(self, messages: List[Dict]) -> str:
        """将消息列表格式化为单个prompt"""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role}: {content}\n"
        return prompt
    
    def is_available(self) -> bool:
        """检查Ollama是否可用"""
        if self._client is None:
            return False
        try:
            self._client.list()
            return True
        except:
            return False


class OpenAICompatibleClient(ModelClient):
    """OpenAI兼容格式的API客户端"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.default_params = {
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"OpenAI兼容客户端初始化成功: {self.base_url}")
        except Exception as e:
            logger.warning(f"OpenAI兼容客户端初始化失败: {e}")
            self._client = None
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """通过OpenAI兼容API调用模型"""
        if self._client is None:
            return self._error_response("API客户端未初始化")
        
        try:
            params = {**self.default_params, **kwargs}
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 1024)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return self._error_response(str(e))
    
    def is_available(self) -> bool:
        """检查API是否可用"""
        return self._client is not None
    
    def _error_response(self, error: str) -> str:
        """生成错误响应"""
        return f"[Error: {error}]"


class WenxinClient(ModelClient):
    """文心一言客户端（特殊API格式）"""
    
    def __init__(self, api_key: str, secret_key: str, model_name: str = "ernie-4.0-8k-latest"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.model_name = model_name
        self._access_token = None
        self._client = None
    
    def _get_access_token(self) -> Optional[str]:
        """获取Access Token（简化版）"""
        if self._access_token:
            return self._access_token
        
        try:
            import requests
            import base64
            
            # 这里需要实现OAuth2.0流程获取access_token
            # 简化版本：直接使用API Key
            self._access_token = self.api_key
            return self._access_token
        except Exception as e:
            logger.error(f"获取Access Token失败: {e}")
            return None
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """调用文心一言API"""
        access_token = self._get_access_token()
        if not access_token:
            return self._error_response("获取Access Token失败")
        
        try:
            import requests
            
            url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"
            
            headers = {"Content-Type": "application/json"}
            data = {
                "messages": messages,
                "model": self.model_name,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1024)
            }
            
            response = requests.post(url, json=data, headers=headers)
            result = response.json()
            
            if "error_code" in result:
                return self._error_response(result.get("error_msg", "未知错误"))
            
            return result.get("result", "")
        except Exception as e:
            logger.error(f"文心一言API调用失败: {e}")
            return self._error_response(str(e))
    
    def is_available(self) -> bool:
        """检查文心一言是否可用"""
        return bool(self._get_access_token())
    
    def _error_response(self, error: str) -> str:
        return f"[Error: {error}]"


class ModelManager:
    """模型管理器 - 统一调度"""
    
    def __init__(self):
        self.clients: Dict[ModelProvider, ModelClient] = {}
        self.config = model_config
        self._init_clients()
    
    def _init_clients(self):
        """初始化所有可用的模型客户端"""
        # 初始化Ollama本地模型
        if self.config.ollama.enabled:
            try:
                ollama_client = OllamaClient(model_name=self.config.ollama.model_name)
                if ollama_client.is_available():
                    self.clients[ModelProvider.OLLAMA_LOCAL] = ollama_client
                    logger.info(f"Ollama客户端已就绪: {self.config.ollama.model_name}")
                else:
                    logger.warning("Ollama不可用，请确保Ollama服务已启动")
            except Exception as e:
                logger.warning(f"Ollama初始化失败: {e}")
        
        # 初始化在线API
        if self.config.dashscope.enabled:
            try:
                self.clients[ModelProvider.DASHSCOPE] = OpenAICompatibleClient(
                    base_url=self.config.dashscope.base_url,
                    api_key=self.config.dashscope.api_key,
                    model_name=self.config.dashscope.model_name,
                    temperature=self.config.dashscope.temperature,
                    max_tokens=self.config.dashscope.max_tokens
                )
                logger.info("通义千问客户端已就绪")
            except Exception as e:
                logger.warning(f"通义千问初始化失败: {e}")
        
        if self.config.deepseek.enabled:
            try:
                self.clients[ModelProvider.DEEPSEEK] = OpenAICompatibleClient(
                    base_url=self.config.deepseek.base_url,
                    api_key=self.config.deepseek.api_key,
                    model_name=self.config.deepseek.model_name,
                    temperature=self.config.deepseek.temperature,
                    max_tokens=self.config.deepseek.max_tokens
                )
                logger.info("DeepSeek客户端已就绪")
            except Exception as e:
                logger.warning(f"DeepSeek初始化失败: {e}")
        
        if self.config.wenxin.enabled:
            try:
                self.clients[ModelProvider.WENXIN] = WenxinClient(
                    api_key=self.config.wenxin.api_key,
                    secret_key=self.config.wenxin_secret,
                    model_name=self.config.wenxin.model_name
                )
                logger.info("文心一言客户端已就绪")
            except Exception as e:
                logger.warning(f"文心一言初始化失败: {e}")
    
    def chat(
        self,
        messages: List[Dict],
        provider: Optional[ModelProvider] = None,
        **kwargs
    ) -> str:
        """
        对话接口
        
        Args:
            messages: 消息列表
            provider: 指定模型提供商，None时自动选择
            **kwargs: 其他参数
            
        Returns:
            模型回复内容
        """
        if provider:
            client = self.clients.get(provider)
            if client and client.is_available():
                logger.debug(f"使用指定模型: {provider.value}")
                return client.chat(messages, **kwargs)
            else:
                logger.warning(f"指定模型 {provider.value} 不可用，自动选择其他模型")
        
        # 自动选择：优先本地Ollama，次选在线API
        priority_order = [
            ModelProvider.OLLAMA_LOCAL,
            ModelProvider.DASHSCOPE,
            ModelProvider.DEEPSEEK,
            ModelProvider.WENXIN
        ]
        
        for p in priority_order:
            client = self.clients.get(p)
            if client and client.is_available():
                logger.info(f"自动选择模型: {p.value}")
                return client.chat(messages, **kwargs)
        
        return self._error_response()
    
    def get_available_providers(self) -> List[ModelProvider]:
        """获取所有可用的模型提供商"""
        return [p for p, client in self.clients.items() if client.is_available()]
    
    def is_any_available(self) -> bool:
        """检查是否有任何模型可用"""
        return any(client.is_available() for client in self.clients.values())
    
    def _error_response(self) -> str:
        """无可用模型时的响应"""
        return "[Error: No available model. Please check your model configuration.]"
    
    def __repr__(self):
        available = [p.value for p in self.get_available_providers()]
        return f"ModelManager(available={available})"


# 全局模型管理器实例
model_manager = ModelManager()
