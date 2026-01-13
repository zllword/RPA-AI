#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息检测器 - 负责检测新消息和读取内容
使用图像识别和OCR技术
"""

import cv2
import numpy as np
import pyautogui # pyright: ignore[reportMissingModuleSource]
import logging
from typing import Optional, Tuple, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class MessageDetector:
    """消息检测器 - 检测新消息并读取内容"""

    # 红点检测的HSV范围
    RED_LOWER = np.array([0, 0, 150])
    RED_UPPER = np.array([100, 100, 255])

    # 红点面积范围(用于过滤)
    MIN_RED_DOT_AREA = 50
    MAX_RED_DOT_AREA = 500

    def __init__(self, wechat_window=None):
        """
        初始化消息检测器

        Args:
            wechat_window: pywinauto窗口对象(可选)
        """
        self.wechat_window = wechat_window
        self.last_screenshot: Optional[np.ndarray] = None
        self.last_detection_time: Optional[float] = None
        self.detected_red_dots: List[Tuple[int, int]] = []

        logger.info("消息检测器初始化完成")

    def take_screenshot(self) -> Optional[np.ndarray]:
        """
        截取微信窗口截图

        Returns:
            OpenCV格式的图像数组
        """
        try:
            if self.wechat_window:
                # 获取窗口位置
                rect = self.wechat_window.rectangle()
                screenshot = pyautogui.screenshot(
                    region=(rect.left, rect.top, rect.width(), rect.height())
                )
            else:
                # 截取整个屏幕
                screenshot = pyautogui.screenshot()

            # 转换为OpenCV格式(BGR)
            self.last_screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            return self.last_screenshot

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None

    def detect_new_message(self, screenshot: Optional[np.ndarray] = None) -> bool:
        """
        检测是否有新消息(通过识别未读红点)

        Args:
            screenshot: 截图图像(可选,如果不提供则自动截图)

        Returns:
            是否检测到新消息
        """
        if screenshot is None:
            screenshot = self.take_screenshot()

        if screenshot is None:
            return False

        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        # 创建红色掩码
        red_mask = cv2.inRange(hsv, self.RED_LOWER, self.RED_UPPER)

        # 查找轮廓
        contours, _ = cv2.findContours(
            red_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # 检查红点
        self.detected_red_dots = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # 过滤合适大小的红点
            if self.MIN_RED_DOT_AREA < area < self.MAX_RED_DOT_AREA:
                # 获取红点中心
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    self.detected_red_dots.append((cx, cy))

        if self.detected_red_dots:
            logger.debug(f"检测到 {len(self.detected_red_dots)} 个未读红点")
            return True

        return False

    def get_red_dot_positions(self) -> List[Tuple[int, int]]:
        """获取检测到的红点位置"""
        return self.detected_red_dots

    def read_last_message(self, screenshot: Optional[np.ndarray] = None) -> Optional[str]:
        """
        读取最后一条消息(通过OCR)

        Args:
            screenshot: 截图图像(可选)

        Returns:
            消息内容文本
        """
        try:
            import pytesseract

            if screenshot is None:
                screenshot = self.take_screenshot()

            if screenshot is None:
                return None

            # 裁剪消息区域(需要根据实际微信界面调整坐标)
            height, width = screenshot.shape[:2]

            # 示例: 裁剪右下角消息区域
            message_area = screenshot[
                int(height * 0.6):int(height * 0.9),
                int(width * 0.3):int(width * 0.95)
            ]

            # 预处理图像(提升OCR准确率)
            gray = cv2.cvtColor(message_area, cv2.COLOR_BGR2GRAY)

            # 二值化
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 去噪
            denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

            # OCR识别
            text = pytesseract.image_to_string(
                denoised,
                lang='chi_sim+eng',
                config='--psm 6'
            )

            # 提取最后一条消息
            messages = [line.strip() for line in text.split('\n') if line.strip()]

            if messages:
                last_message = messages[-1]
                logger.debug(f"OCR识别结果: {last_message}")
                return last_message

            return None

        except ImportError:
            logger.error("pytesseract未安装,请运行: pip install pytesseract")
            return None
        except Exception as e:
            logger.error(f"OCR读取失败: {e}")
            return None

    def get_active_chat_name(self, screenshot: Optional[np.ndarray] = None) -> Optional[str]:
        """
        获取当前聊天窗口的用户名(通过OCR)

        Args:
            screenshot: 截图图像(可选)

        Returns:
            聊天对象名称
        """
        try:
            import pytesseract

            if screenshot is None:
                screenshot = self.take_screenshot()

            if screenshot is None:
                return None

            # 裁剪标题区域(左上角)
            height, width = screenshot.shape[:2]
            title_area = screenshot[0:int(height * 0.1), int(width * 0.1):int(width * 0.5)]

            # OCR识别
            text = pytesseract.image_to_string(
                title_area,
                lang='chi_sim+eng',
                config='--psm 7'
            )

            # 清理结果
            chat_name = text.strip().split('\n')[0] if text else None

            if chat_name:
                logger.debug(f"识别到聊天窗口: {chat_name}")

            return chat_name

        except Exception as e:
            logger.error(f"获取聊天窗口失败: {e}")
            return None

    def save_screenshot(self, output_dir: str = "screenshots"):
        """
        保存截图(用于调试)

        Args:
            output_dir: 输出目录
        """
        import os
        from pathlib import Path

        if self.last_screenshot is None:
            logger.warning("没有可保存的截图")
            return

        # 创建目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)

        # 保存
        cv2.imwrite(filepath, self.last_screenshot)
        logger.info(f"截图已保存: {filepath}")

        return filepath

    def analyze_message_area(self, screenshot: Optional[np.ndarray] = None) -> dict:
        """
        分析消息区域(返回统计信息)

        Args:
            screenshot: 截图图像(可选)

        Returns:
            分析结果字典
        """
        if screenshot is None:
            screenshot = self.take_screenshot()

        if screenshot is None:
            return {}

        height, width = screenshot.shape[:2]

        return {
            "size": (width, height),
            "channels": screenshot.shape[2] if len(screenshot.shape) > 2 else 1,
            "red_dots": len(self.detected_red_dots),
            "red_dot_positions": self.detected_red_dots
        }


# 测试代码
if __name__ == "__main__":
    # 测试消息检测器
    detector = MessageDetector()

    # 截图
    screenshot = detector.take_screenshot()
    print(f"截图大小: {screenshot.shape if screenshot is not None else 'None'}")

    # 检测新消息
    has_new = detector.detect_new_message(screenshot)
    print(f"检测到新消息: {has_new}")

    # 保存截图
    if screenshot is not None:
        detector.save_screenshot()
