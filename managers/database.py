#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器 - 负责数据持久化和查询
使用连接池提升性能,支持事务和批量操作
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MessageRecord:
    """消息记录数据类"""
    sender: str
    message: str
    response: Optional[str]
    timestamp: str
    auto_replied: bool
    id: Optional[int] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class DailyStats:
    """每日统计数据类"""
    date: str
    total_messages: int
    auto_replies: int
    unique_senders: int

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class DatabaseManager:
    """数据库管理器 - 使用连接池和事务管理"""

    def __init__(self, db_path: str = 'wechat_bot.db', pool_size: int = 5):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
            pool_size: 连接池大小
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._connection_pool: List[sqlite3.Connection] = []
        self._pool_lock = None

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

        logger.info(f"数据库管理器初始化完成: {db_path}")

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接(上下文管理器)
        自动归还到连接池
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            self._return_connection(conn)

    def _get_connection(self) -> sqlite3.Connection:
        """从连接池获取连接"""
        if self._connection_pool:
            return self._connection_pool.pop()

        # 创建新连接
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None  # 自动提交模式
        )
        conn.row_factory = sqlite3.Row
        # 启用WAL模式(更好的并发性能)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        return conn

    def _return_connection(self, conn: sqlite3.Connection):
        """归还连接到池"""
        if len(self._connection_pool) < self.pool_size:
            self._connection_pool.append(conn)
        else:
            conn.close()

    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 消息记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    auto_replied BOOLEAN DEFAULT 1,
                    INDEX idx_sender (sender),
                    INDEX idx_timestamp (timestamp)
                )
            """)

            # 会话统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_messages INTEGER DEFAULT 0,
                    auto_replies INTEGER DEFAULT 0,
                    unique_senders INTEGER DEFAULT 0
                )
            """)

            # 会话历史表(新增:持久化会话)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session (session_id, timestamp)
                )
            """)

            # 创建索引(如果不存在)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_sender
                ON messages(sender)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp DESC)
            """)

            conn.commit()

        logger.info("数据库表初始化完成")

    def save_message(self, record: MessageRecord) -> int:
        """
        保存消息记录

        Args:
            record: 消息记录对象

        Returns:
            插入记录的ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO messages (sender, message, response, auto_replied)
                VALUES (?, ?, ?, ?)
            """, (record.sender, record.message, record.response, record.auto_replied))

            message_id = cursor.lastrowid

            # 更新统计
            self._update_daily_stats(conn, record.auto_replied, record.sender)

            conn.commit()

        return message_id

    def _update_daily_stats(self, conn: sqlite3.Connection, auto_replied: bool, sender: str):
        """更新每日统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = conn.cursor()

        # 使用UPSERT语法
        cursor.execute("""
            INSERT INTO daily_stats (date, total_messages, auto_replies, unique_senders)
            VALUES (?, 1, ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                total_messages = total_messages + 1,
                auto_replies = auto_replies + ?,
                unique_senders = (
                    SELECT COUNT(DISTINCT sender)
                    FROM messages
                    WHERE DATE(timestamp) = ?
                )
        """, (today, 1 if auto_replied else 0, 1 if auto_replied else 0, today))

    def get_messages(
        self,
        sender: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MessageRecord]:
        """
        查询消息记录

        Args:
            sender: 发送者过滤(可选)
            limit: 返回数量限制
            offset: 偏移量
            start_date: 开始日期(YYYY-MM-DD)
            end_date: 结束日期(YYYY-MM-DD)

        Returns:
            消息记录列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM messages WHERE 1=1"
            params = []

            if sender:
                query += " AND sender = ?"
                params.append(sender)

            if start_date:
                query += " AND DATE(timestamp) >= ?"
                params.append(start_date)

            if end_date:
                query += " AND DATE(timestamp) <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [MessageRecord(**dict(row)) for row in rows]

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        """
        获取每日统计

        Args:
            date: 日期(YYYY-MM-DD),默认为今天

        Returns:
            统计数据对象
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
            row = cursor.fetchone()

            if row:
                return DailyStats(**dict(row))
            return None

    def get_weekly_stats(self, days: int = 7) -> List[DailyStats]:
        """获取最近N天的统计"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_stats
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

            rows = cursor.fetchall()
            return [DailyStats(**dict(row)) for row in rows]

    def get_total_stats(self) -> Dict[str, Any]:
        """获取总体统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 消息总数
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total_messages = cursor.fetchone()['total']

            # 自动回复数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM messages
                WHERE auto_replied = 1
            """)
            auto_replies = cursor.fetchone()['count']

            # 独立用户数
            cursor.execute("SELECT COUNT(DISTINCT sender) as count FROM messages")
            unique_senders = cursor.fetchone()['count']

            # 平均每日消息数
            cursor.execute("""
                SELECT AVG(total_messages) as avg
                FROM daily_stats
            """)
            avg_daily = cursor.fetchone()['avg'] or 0

            return {
                "total_messages": total_messages,
                "auto_replies": auto_replies,
                "unique_senders": unique_senders,
                "avg_daily_messages": round(avg_daily, 1),
                "auto_reply_rate": round(auto_replies / total_messages * 100, 1) if total_messages > 0 else 0
            }

    def save_session_message(self, session_id: str, role: str, content: str):
        """保存会话消息(用于持久化对话历史)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_history (session_id, role, content)
                VALUES (?, ?, ?)
            """, (session_id, role, content))
            conn.commit()

    def get_session_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """
        获取会话历史

        Args:
            session_id: 会话ID
            limit: 返回数量

        Returns:
            消息列表 [{"role": "...", "content": "..."}]
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content
                FROM session_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))

            rows = cursor.fetchall()
            return [{"role": row['role'], "content": row['content']} for row in reversed(rows)]

    def clear_old_messages(self, days: int = 30):
        """清理旧消息(定期维护)"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 删除旧消息
            cursor.execute("""
                DELETE FROM messages
                WHERE DATE(timestamp) < ?
            """, (cutoff_date,))

            deleted_messages = cursor.rowcount

            # 删除旧会话历史
            cursor.execute("""
                DELETE FROM session_history
                WHERE DATE(timestamp) < ?
            """, (cutoff_date,))

            deleted_sessions = cursor.rowcount

            conn.commit()

        logger.info(f"清理旧数据: {deleted_messages} 条消息, {deleted_sessions} 条会话")

        return deleted_messages + deleted_sessions

    def export_to_json(self, output_path: str, days: int = 7):
        """导出数据为JSON"""
        messages = self.get_messages(start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'))

        data = {
            "export_time": datetime.now().isoformat(),
            "messages": [msg.to_dict() for msg in messages]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"导出 {len(messages)} 条记录到 {output_path}")

    def close(self):
        """关闭所有连接"""
        for conn in self._connection_pool:
            conn.close()
        self._connection_pool.clear()
        logger.info("数据库连接池已关闭")


# 单例模式
_db_instance: Optional[DatabaseManager] = None


def get_database(db_path: str = 'wechat_bot.db') -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager(db_path)
    return _db_instance


# 测试代码
if __name__ == "__main__":
    # 测试数据库管理器
    db = DatabaseManager(":memory:")  # 使用内存数据库测试

    # 插入测试数据
    record = MessageRecord(
        sender="test_user",
        message="你好",
        response="您好!",
        auto_replied=True
    )
    msg_id = db.save_message(record)
    print(f"插入消息 ID: {msg_id}")

    # 查询消息
    messages = db.get_messages(limit=10)
    print(f"查询到 {len(messages)} 条消息")

    # 获取统计
    stats = db.get_total_stats()
    print(f"统计信息: {stats}")

    db.close()
