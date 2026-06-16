"""
智能体基类
定义博弈智能体的通用属性和方法
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.model_manager import model_manager
from config.model_config import ModelProvider


@dataclass
class AgentMemory:
    """智能体记忆"""
    history: List[Dict] = field(default_factory=list)
    
    def add(self, event_type: str, content: Any, metadata: Optional[Dict] = None):
        """添加记忆"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "content": content,
            "metadata": metadata or {}
        })
    
    def get_recent(self, n: int = 5) -> List[Dict]:
        """获取最近n条记忆"""
        return self.history[-n:] if self.history else []
    
    def get_by_type(self, event_type: str) -> List[Dict]:
        """按类型获取记忆"""
        return [m for m in self.history if m["type"] == event_type]
    
    def clear(self):
        """清空记忆"""
        self.history.clear()


class BaseGameAgent(ABC):
    """
    博弈智能体基类
    
    所有攻防智能体都继承此类
    """
    
    def __init__(
        self,
        name: str,
        role_description: str,
        model_provider: Optional[ModelProvider] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_llm: bool = True
    ):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            role_description: 角色描述（用于prompt）
            model_provider: 使用的模型提供商
            temperature: 温度参数
            max_tokens: 最大生成token数
            use_llm: 是否使用大模型
        """
        self.name = name
        self.role_description = role_description
        self.model_provider = model_provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_llm = use_llm
        
        # 记忆系统
        self.memory = AgentMemory()
        
        # 初始化prompt
        self.system_prompt = self._build_system_prompt()
        
        self.logger = logging.getLogger(f"Agent.{name}")
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """构建系统提示词（子类实现）"""
        pass
    
    def think(self, context: Dict[str, Any]) -> str:
        """
        智能思考
        
        Args:
            context: 当前上下文（网络状态、历史等）
            
        Returns:
            思考结果
        """
        if not self.use_llm:
            return self._rule_based_think(context)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_context(context)}
        ]
        
        response = model_manager.chat(
            messages=messages,
            provider=self.model_provider,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response
    
    @abstractmethod
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文信息（子类实现）"""
        pass
    
    @abstractmethod
    def _rule_based_think(self, context: Dict[str, Any]) -> str:
        """基于规则的思考（当不使用LLM时）"""
        pass
    
    def remember(self, event_type: str, content: Any, metadata: Optional[Dict] = None):
        """记录记忆"""
        self.memory.add(event_type, content, metadata)
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        recent = self.memory.get_recent(5)
        if not recent:
            return "（无历史记忆）"
        
        lines = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"{i}. [{entry['type']}] {entry['content']}")
        return "\n".join(lines)
    
    def reset(self):
        """重置智能体状态"""
        self.memory.clear()
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"