#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 支持环境变量和配置文件
优先级: 环境变量 > 配置文件 > 默认值
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """机器人配置数据类"""

    # 微信窗口配置
    wechat_window_name: str = "微信"

    # 回复延迟配置
    reply_delay_min: float = 2.0
    reply_delay_max: float = 5.0

    # 每日限额
    max_daily_replies: int = 100

    # 关键词和过滤
    auto_reply_keywords: list = field(default_factory=lambda: ["在吗", "你好", "在不在", "hello"])
    blacklist: list = field(default_factory=list)
    whitelist: list = field(default_factory=list)

    # AI配置
    ai_enabled: bool = True
    ai_model: str = "deepseek-chat"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.deepseek.com/v1"
    max_tokens: int = 200
    temperature: float = 0.7
    max_history_turns: int = 10

    # 系统提示词
    system_prompt: str = ""

    # 缓存和性能
    enable_cache: bool = True
    enable_rate_limit: bool = True
    rate_limit_max_requests: int = 60
    rate_limit_time_window: int = 60

    # 重试配置
    max_retries: int = 3

    # 数据库配置
    db_path: str = "wechat_bot.db"

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "wechat_bot.log"

    # 备用回复
    fallback_responses: dict = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理 - 从环境变量读取敏感配置"""
        # API密钥优先从环境变量读取
        env_api_key = os.getenv('WECHAT_BOT_API_KEY') or os.getenv('AI_API_KEY')
        if env_api_key:
            self.ai_api_key = env_api_key
            logger.info("从环境变量读取API密钥")

        # 其他可选的环境变量覆盖
        if os.getenv('AI_MODEL'):
            self.ai_model = os.getenv('AI_MODEL')
        if os.getenv('AI_BASE_URL'):
            self.ai_base_url = os.getenv('AI_BASE_URL')
        if os.getenv('MAX_DAILY_REPLIES'):
            self.max_daily_replies = int(os.getenv('MAX_DAILY_REPLIES'))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典(隐藏敏感信息)"""
        data = {
            "wechat_window_name": self.wechat_window_name,
            "reply_delay_min": self.reply_delay_min,
            "reply_delay_max": self.reply_delay_max,
            "max_daily_replies": self.max_daily_replies,
            "auto_reply_keywords": self.auto_reply_keywords,
            "blacklist": self.blacklist,
            "whitelist": self.whitelist,
            "ai_enabled": self.ai_enabled,
            "ai_model": self.ai_model,
            "ai_api_key": "***hidden***" if self.ai_api_key else "",
            "ai_base_url": self.ai_base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_cache": self.enable_cache,
            "enable_rate_limit": self.enable_rate_limit,
            "db_path": self.db_path,
            "log_level": self.log_level
        }
        return data

    def validate(self) -> bool:
        """验证配置"""
        if self.ai_enabled and not self.ai_api_key:
            logger.warning("AI已启用但未配置API密钥")
            return False

        if self.reply_delay_min < 0 or self.reply_delay_max < self.reply_delay_min:
            logger.error("回复延迟配置无效")
            return False

        if self.max_daily_replies < 0:
            logger.error("每日回复限额无效")
            return False

        return True


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG_PATH = "config.json"
    DEFAULT_ENV_PATH = ".env"

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        logger.info(f"配置管理器初始化完成: {self.config_path}")

    def _load_config(self) -> BotConfig:
        """加载配置"""
        # 1. 从文件加载
        file_config = self._load_from_file()

        # 2. 从环境变量加载(会覆盖文件配置)
        env_config = self._load_from_env()

        # 3. 合并配置
        merged = {**file_config, **env_config}

        # 4. 创建配置对象
        config = BotConfig(**merged)

        # 5. 验证配置
        if not config.validate():
            logger.warning("配置验证失败,使用默认值")

        return config

    def _load_from_file(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件 {self.config_path} 不存在,使用默认配置")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"从 {self.config_path} 加载配置")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}

        # AI配置
        if os.getenv('AI_API_KEY') or os.getenv('WECHAT_BOT_API_KEY'):
            env_config['ai_api_key'] = os.getenv('AI_API_KEY') or os.getenv('WECHAT_BOT_API_KEY')

        if os.getenv('AI_MODEL'):
            env_config['ai_model'] = os.getenv('AI_MODEL')

        if os.getenv('AI_BASE_URL'):
            env_config['ai_base_url'] = os.getenv('AI_BASE_URL')

        # 限额配置
        if os.getenv('MAX_DAILY_REPLIES'):
            env_config['max_daily_replies'] = int(os.getenv('MAX_DAILY_REPLIES'))

        # 延迟配置
        if os.getenv('REPLY_DELAY_MIN'):
            env_config['reply_delay_min'] = float(os.getenv('REPLY_DELAY_MIN'))

        if os.getenv('REPLY_DELAY_MAX'):
            env_config['reply_delay_max'] = float(os.getenv('REPLY_DELAY_MAX'))

        # 数据库配置
        if os.getenv('DB_PATH'):
            env_config['db_path'] = os.getenv('DB_PATH')

        # 日志配置
        if os.getenv('LOG_LEVEL'):
            env_config['log_level'] = os.getenv('LOG_LEVEL')

        if env_config:
            logger.info(f"从环境变量加载配置: {list(env_config.keys())}")

        return env_config

    def load_env_file(self, env_path: Optional[str] = None):
        """
        加载.env文件

        Args:
            env_path: .env文件路径
        """
        env_path = env_path or self.DEFAULT_ENV_PATH

        if not os.path.exists(env_path):
            logger.info(f".env文件 {env_path} 不存在,跳过")
            return

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

            logger.info(f"已加载 .env 文件: {env_path}")

        except Exception as e:
            logger.error(f"加载 .env 文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self.config, key, default)

    def reload(self):
        """重新加载配置"""
        logger.info("重新加载配置...")
        self.config = self._load_config()

    def save_example(self, output_path: str = "config.json.example"):
        """保存配置示例"""
        example = BotConfig().to_dict()

        # 添加注释
        example_with_comments = {
            "_comment": "微信机器人配置文件 - 复制此文件为 config.json 并修改",
            **example
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(example_with_comments, f, ensure_ascii=False, indent=2)

        logger.info(f"配置示例已保存到 {output_path}")


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


# 测试代码
if __name__ == "__main__":
    # 测试配置管理器
    config_mgr = ConfigManager()
    config = config_mgr.config

    print(f"AI模型: {config.ai_model}")
    print(f"API密钥: {'已配置' if config.ai_api_key else '未配置'}")
    print(f"每日限额: {config.max_daily_replies}")
    print(f"配置验证: {'通过' if config.validate() else '失败'}")
