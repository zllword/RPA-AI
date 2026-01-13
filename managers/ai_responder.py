#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI回复管理器 - 负责LLM调用和回复生成
支持多种AI模型: OpenAI, DeepSeek, 通义千问等
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """AI响应数据类"""
    content: str
    model: str
    tokens_used: int = 0
    cached: bool = False
    error: Optional[str] = None


class RateLimiter:
    """API速率限制器"""

    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()
        # 移除超出时间窗口的请求记录
        self.requests = [t for t in self.requests if now - t < self.time_window]

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

    def wait_if_needed(self):
        """如果需要则等待"""
        while not self.is_allowed():
            time.sleep(1)


class SmartResponder:
    """智能AI回复器"""

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """你是一个智能客服助手,请根据用户消息生成合适的回复。

规则:
1. 回复要简洁友好,不超过100字
2. 如果是问候,简单回应
3. 如果是问题,尽力回答
4. 如果无法处理,礼貌地建议人工客服
5. 保持自然对话的语气
6. 避免重复相同的回答
"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI回复器

        Args:
            config: 配置字典,包含:
                - ai_model: 模型名称
                - ai_api_key: API密钥
                - ai_base_url: API基础URL
                - system_prompt: 自定义系统提示词(可选)
                - max_tokens: 最大token数(可选)
                - temperature: 温度参数(可选)
                - enable_cache: 是否启用缓存(可选)
                - rate_limit: 速率限制(可选)
        """
        self.config = config
        self.model = config.get('ai_model', 'deepseek-chat')
        self.api_key = config.get('ai_api_key', '')
        self.base_url = config.get('ai_base_url', 'https://api.deepseek.com/v1')

        # 从环境变量读取API密钥(优先级更高)
        env_api_key = os.getenv('WECHAT_BOT_API_KEY') or os.getenv('AI_API_KEY')
        if env_api_key:
            self.api_key = env_api_key
            logger.info("使用环境变量中的API密钥")

        # 模型参数
        self.max_tokens = config.get('max_tokens', 200)
        self.temperature = config.get('temperature', 0.7)
        self.system_prompt = config.get('system_prompt', self.DEFAULT_SYSTEM_PROMPT)

        # 功能开关
        self.enable_cache = config.get('enable_cache', True)
        self.enable_rate_limit = config.get('enable_rate_limit', True)

        # 初始化速率限制器
        if self.enable_rate_limit:
            max_requests = config.get('rate_limit_max_requests', 60)
            time_window = config.get('rate_limit_time_window', 60)
            self.rate_limiter = RateLimiter(max_requests, time_window)

        # 会话历史 {session_id: [messages]}
        self.session_history: Dict[str, List[Dict]] = {}

        # 初始化OpenAI客户端(延迟加载)
        self._client = None

        logger.info(f"AI回复器初始化完成: model={self.model}")

    @property
    def client(self):
        """延迟加载OpenAI客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info("OpenAI客户端初始化成功")
            except ImportError:
                logger.error("OpenAI库未安装,请运行: pip install openai")
                raise
            except Exception as e:
                logger.error(f"OpenAI客户端初始化失败: {e}")
                raise
        return self._client

    def _get_cache_key(self, message: str, context: Optional[Dict] = None) -> str:
        """生成缓存键"""
        content = message
        if context:
            content += str(sorted(context.items()))
        return hashlib.md5(content.encode()).hexdigest()

    @lru_cache(maxsize=100)
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """从缓存获取响应(使用LRU缓存)"""
        return None

    def _cache_response(self, cache_key: str, response: str):
        """缓存响应(实际实现可使用Redis)"""
        if self.enable_cache:
            # 这里可以使用Redis等持久化缓存
            pass

    def get_session_history(self, session_id: str, max_turns: int = 3) -> List[Dict]:
        """
        获取会话历史

        Args:
            session_id: 会话ID
            max_turns: 最大轮数

        Returns:
            历史消息列表
        """
        history = self.session_history.get(session_id, [])
        return history[-max_turns * 2:] if history else []  # 每轮包含user和assistant

    def update_session_history(self, session_id: str, user_message: str, assistant_message: str):
        """更新会话历史"""
        if session_id not in self.session_history:
            self.session_history[session_id] = []

        self.session_history[session_id].extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ])

        # 限制历史长度(避免token浪费)
        max_history = self.config.get('max_history_turns', 10) * 2
        if len(self.session_history[session_id]) > max_history:
            self.session_history[session_id] = self.session_history[session_id][-max_history:]

    def clear_session(self, session_id: str):
        """清除会话历史"""
        if session_id in self.session_history:
            del self.session_history[session_id]
            logger.info(f"会话 {session_id} 已清除")

    def generate_response(
        self,
        message: str,
        sender_id: str = "default",
        context: Optional[Dict] = None,
        use_history: bool = True
    ) -> AIResponse:
        """
        生成AI回复

        Args:
            message: 用户消息
            sender_id: 发送者ID(用于会话管理)
            context: 额外上下文信息
            use_history: 是否使用历史对话

        Returns:
            AIResponse对象
        """
        # 检查缓存
        cache_key = self._get_cache_key(message, context) if self.enable_cache else None
        if cache_key:
            cached = self._get_cached_response(cache_key)
            if cached:
                logger.debug("使用缓存响应")
                return AIResponse(content=cached, model=self.model, cached=True)

        # 速率限制
        if self.enable_rate_limit:
            self.rate_limiter.wait_if_needed()

        # 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加历史对话
        if use_history and sender_id:
            history = self.get_session_history(sender_id)
            messages.extend(history)

        # 添加当前消息
        messages.append({"role": "user", "content": message})

        # 添加上下文信息
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append({"role": "user", "content": f"[上下文信息]\n{context_str}"})

        # 调用API(带重试)
        max_retries = self.config.get('max_retries', 3)
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"调用AI API (尝试 {attempt + 1}/{max_retries})")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

                # 保存到历史
                if use_history and sender_id:
                    self.update_session_history(sender_id, message, content)

                # 缓存响应
                if cache_key:
                    self._cache_response(cache_key, content)

                logger.info(f"AI回复生成成功, tokens: {tokens_used}")

                return AIResponse(
                    content=content,
                    model=self.model,
                    tokens_used=tokens_used,
                    cached=False
                )

            except Exception as e:
                last_error = e
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    # 指数退避
                    wait_time = (2 ** attempt) * 1
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        # 所有重试都失败
        logger.error(f"AI生成失败: {last_error}")
        return AIResponse(
            content=self._get_fallback_response(message),
            model=self.model,
            error=str(last_error)
        )

    def _get_fallback_response(self, message: str) -> str:
        """获取失败时的备用回复"""
        fallback_responses = {
            "在吗": "在的,有什么可以帮您?",
            "你好": "您好! 很高兴为您服务",
            "在不在": "在的,请问有什么需要?",
            "hello": "Hello! How can I help you?",
        }

        for keyword, response in fallback_responses.items():
            if keyword.lower() in message.lower():
                return response

        return "抱歉,我现在暂时无法回复,请稍后再试。"

    def batch_generate(
        self,
        messages: List[str],
        sender_id: str = "batch",
        context: Optional[Dict] = None
    ) -> List[AIResponse]:
        """
        批量生成回复

        Args:
            messages: 消息列表
            sender_id: 发送者ID
            context: 上下文信息

        Returns:
            AIResponse列表
        """
        responses = []
        for msg in messages:
            response = self.generate_response(msg, sender_id, context, use_history=False)
            responses.append(response)

        return responses

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "model": self.model,
            "sessions": len(self.session_history),
            "total_messages": sum(len(h) for h in self.session_history.values()),
            "cache_enabled": self.enable_cache,
            "rate_limit_enabled": self.enable_rate_limit
        }


def create_responder(config_path: str = "config.json") -> SmartResponder:
    """
    工厂函数:创建AI回复器

    Args:
        config_path: 配置文件路径

    Returns:
        SmartResponder实例
    """
    import json

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.warning(f"配置文件 {config_path} 不存在,使用默认配置")
        config = {}

    return SmartResponder(config)


# 测试代码
if __name__ == "__main__":
    # 测试AI回复器
    test_config = {
        "ai_model": "deepseek-chat",
        "ai_api_key": "test-key",
        "ai_base_url": "https://api.deepseek.com/v1",
        "enable_cache": True,
        "enable_rate_limit": False
    }

    responder = SmartResponder(test_config)
    print(f"Responder stats: {responder.get_stats()}")

    # 测试回复
    response = responder.generate_response("你好")
    print(f"Response: {response.content}")
