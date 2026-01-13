#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信自动回复机器人 - 优化版本
使用模块化架构,提升可维护性和性能
"""

import sys
import os
import time
import logging
import numpy as np
import pyautogui  # pyright: ignore[reportMissingModuleSource]
import pywinauto  # pyright: ignore[reportMissingImports]
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入管理器模块
from managers import (
    SmartResponder,
    DatabaseManager,
    MessageDetector,
    MessageRecord,
    get_database
)
from config.config_manager import ConfigManager, get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wechat_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WeChatBot:
    """
    微信自动回复机器人 - 优化版本

    主要改进:
    1. 使用模块化架构,职责分离
    2. 使用连接池管理数据库连接
    3. 集成AI回复管理器(带重试和速率限制)
    4. 支持环境变量配置
    5. 会话持久化
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化机器人

        Args:
            config_path: 配置文件路径(可选)
        """
        # 加载配置
        self.config_mgr = get_config(config_path)
        self.config_mgr.load_env_file()  # 加载.env文件
        self.config = self.config_mgr.config

        # 初始化组件
        self.db = get_database(self.config.db_path)
        self.ai_responder: Optional[SmartResponder] = None
        self.message_detector: Optional[MessageDetector] = None

        # 微信窗口
        self.wechat_window = None

        # 安全设置
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True

        logger.info("=" * 50)
        logger.info("微信机器人初始化完成")
        logger.info(f"AI模型: {self.config.ai_model}")
        logger.info(f"每日限额: {self.config.max_daily_replies}")
        logger.info("=" * 50)

    def connect_wechat(self) -> bool:
        """
        连接微信客户端

        Returns:
            是否连接成功
        """
        try:
            app = pywinauto.Application().connect(
                title=self.config.wechat_window_name,
                timeout=10
            )
            self.wechat_window = app.window(
                title=self.config.wechat_window_name
            )
            self.wechat_window.set_focus()

            # 初始化消息检测器
            self.message_detector = MessageDetector(self.wechat_window)

            logger.info("成功连接微信客户端")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"连接微信失败: {e}")
            logger.info("请确保:")
            logger.info("1. 微信PC客户端已启动")
            logger.info("2. 微信已登录")
            logger.info("3. 微信窗口可见")
            return False

    def init_ai_responder(self):
        """初始化AI回复器"""
        if self.config.ai_enabled and self.ai_responder is None:
            self.ai_responder = SmartResponder(self.config.to_dict())
            logger.info("AI回复器初始化完成")

    def should_reply(self, sender: str, message: str) -> bool:
        """
        判断是否应该自动回复

        Args:
            sender: 发送者
            message: 消息内容

        Returns:
            是否回复
        """
        # 检查黑名单
        if sender in self.config.blacklist:
            logger.info(f"用户 {sender} 在黑名单中,跳过")
            return False

        # 检查白名单
        if self.config.whitelist and sender not in self.config.whitelist:
            logger.info(f"用户 {sender} 不在白名单中,跳过")
            return False

        # 检查关键词
        if self.config.auto_reply_keywords:
            if not any(kw in message for kw in self.config.auto_reply_keywords):
                logger.debug("消息不匹配关键词,跳过")
                return False

        # 检查每日限额
        stats = self.db.get_daily_stats()
        if stats and stats.auto_replies >= self.config.max_daily_replies:
            logger.warning("今日回复已达上限")
            return False

        return True

    def get_sender_name(self) -> str:
        """
        获取发送者名称

        Returns:
            发送者名称(如果无法识别则返回"unknown")
        """
        if self.message_detector:
            sender = self.message_detector.get_active_chat_name()
            return sender if sender else "unknown"
        return "unknown"

    def generate_response(self, message: str, sender: str) -> str:
        """
        生成回复

        Args:
            message: 消息内容
            sender: 发送者ID

        Returns:
            回复内容
        """
        if not self.config.ai_enabled:
            return self._get_fallback_response(message)

        if self.ai_responder is None:
            self.init_ai_responder()

        try:
            # 使用AI生成回复(带重试和速率限制)
            ai_response = self.ai_responder.generate_response(
                message,
                sender_id=sender,
                use_history=True
            )

            if ai_response.error:
                logger.warning(f"AI生成失败: {ai_response.error}")
                return self._get_fallback_response(message)

            return ai_response.content

        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return self._get_fallback_response(message)

    def _get_fallback_response(self, message: str) -> str:
        """获取备用回复"""
        fallback_responses = {
            "在吗": "在的,有什么可以帮您?",
            "你好": "您好! 很高兴为您服务",
            "在不在": "在的,请问有什么需要?",
            "hello": "Hello! How can I help you?",
            "价格": "关于价格问题,建议查看官网或咨询人工客服",
            "price": "关于价格问题,请查看官网或咨询人工客服"
        }

        for keyword, response in fallback_responses.items():
            if keyword.lower() in message.lower():
                return response

        return "收到您的消息,我会尽快回复"

    def send_message(self, message: str) -> bool:
        """
        发送消息

        Args:
            message: 消息内容

        Returns:
            是否发送成功
        """
        try:
            # 跳转到输入框
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.3)
            pyautogui.press('escape')
            time.sleep(0.3)

            # 输入消息
            pyautogui.write(message, interval=0.05)
            time.sleep(0.5)

            # 发送
            pyautogui.press('enter')
            logger.info(f"发送消息: {message}")

            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def run_once(self) -> bool:
        """
        执行一次监控-回复循环

        Returns:
            是否成功处理
        """
        try:
            # 检测新消息
            if not self.message_detector:
                return False

            if not self.message_detector.detect_new_message():
                return False

            logger.info("检测到新消息")

            # 读取消息
            message = self.message_detector.read_last_message()
            if not message:
                logger.warning("无法读取消息内容")
                return False

            logger.info(f"消息内容: {message}")

            # 获取发送者
            sender = self.get_sender_name()

            # 判断是否回复
            if not self.should_reply(sender, message):
                return False

            # 生成回复
            response = self.generate_response(message, sender)
            logger.info(f"生成回复: {response}")

            # 延迟(模拟人类)
            delay = np.random.uniform(
                self.config.reply_delay_min,
                self.config.reply_delay_max
            )
            logger.info(f"等待 {delay:.1f} 秒后回复...")
            time.sleep(delay)

            # 发送回复
            if self.send_message(response):
                # 保存记录
                record = MessageRecord(
                    sender=sender,
                    message=message,
                    response=response,
                    auto_replied=True
                )
                self.db.save_message(record)
                return True

            return False

        except Exception as e:
            logger.error(f"处理失败: {e}")
            return False

    def run(self):
        """主循环"""
        logger.info("=" * 50)
        logger.info("微信自动回复机器人启动")
        logger.info("=" * 50)

        # 连接微信
        if not self.connect_wechat():
            logger.error("无法连接微信,程序退出")
            return

        # 初始化AI
        if self.config.ai_enabled:
            self.init_ai_responder()

        logger.info("开始监控消息...")
        logger.info("按 Ctrl+C 停止程序")
        logger.info("或将鼠标移到屏幕左上角紧急停止")

        try:
            while True:
                self.run_once()
                time.sleep(2)  # 每2秒检查一次

        except KeyboardInterrupt:
            logger.info("\n收到停止信号,正在退出...")

        finally:
            self.cleanup()

    def test_mode(self):
        """测试模式"""
        logger.info("测试模式")

        if not self.connect_wechat():
            return

        # 初始化AI
        if self.config.ai_enabled:
            self.init_ai_responder()

        test_message = "你好,在吗?"
        logger.info(f"测试消息: {test_message}")

        # 生成回复
        response = self.generate_response(test_message, "test_user")
        logger.info(f"AI回复: {response}")

        # 发送
        self.send_message(response)

    def cleanup(self):
        """清理资源"""
        if self.db:
            self.db.close()
        logger.info("程序已停止")


def main():
    """主函数"""
    import json

    # 创建配置文件示例(如果不存在)
    if not os.path.exists('config.json'):
        example_config = {
            "_comment": "微信机器人配置文件",
            "wechat_window_name": "微信",
            "reply_delay_min": 2,
            "reply_delay_max": 5,
            "max_daily_replies": 100,
            "auto_reply_keywords": ["在吗", "你好", "在不在"],
            "blacklist": [],
            "whitelist": [],
            "ai_enabled": True,
            "ai_model": "deepseek-chat",
            "ai_api_key": "your-api-key-here",
            "ai_base_url": "https://api.deepseek.com/v1"
        }

        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(example_config, f, indent=2, ensure_ascii=False)

        logger.info("已创建配置文件 config.json,请填写API密钥")
        logger.info("或使用 .env 文件配置API密钥")
        return

    # 运行机器人
    bot = WeChatBot()

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        bot.test_mode()
    else:
        bot.run()


if __name__ == "__main__":
    main()
