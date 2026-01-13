#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web管理界面 - Flask应用
用于监控和管理微信机器人
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入管理器模块
from managers import get_database, SmartResponder
from config.config_manager import get_config

app = Flask(__name__)
DB_PATH = 'wechat_bot.db'
CONFIG_PATH = 'config.json'


def get_db():
    """获取数据库实例"""
    return get_database(DB_PATH)


def load_config():
    """加载配置"""
    config_mgr = get_config(CONFIG_PATH)
    config_mgr.load_env_file()
    return config_mgr.config.to_dict()


@app.route('/')
def index():
    """首页 - 重定向到dashboard"""
    return dashboard_page()


@app.route('/dashboard')
def dashboard_page():
    """仪表盘页面"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信机器人管理面板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 20px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }
        .messages-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .message-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .message-item:last-child { border-bottom: none; }
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .sender { font-weight: bold; color: #333; }
        .timestamp { color: #999; font-size: 12px; }
        .message-content { color: #666; margin: 5px 0; }
        .response-content {
            background: #f0f7ff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 8px;
        }
        .auto-badge {
            display: inline-block;
            padding: 2px 8px;
            background: #4caf50;
            color: white;
            border-radius: 12px;
            font-size: 11px;
            margin-left: 8px;
        }
        .test-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .test-input {
            width: 70%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .test-btn {
            padding: 10px 20px;
            background: #2196f3;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .test-btn:hover { background: #1976d2; }
        .test-response {
            margin-top: 15px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 微信机器人管理面板</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>今日消息总数</h3>
                <div class="value" id="todayTotal">0</div>
            </div>
            <div class="stat-card">
                <h3>自动回复数</h3>
                <div class="value" id="todayReplies">0</div>
            </div>
            <div class="stat-card">
                <h3>活跃用户</h3>
                <div class="value" id="todaySenders">0</div>
            </div>
            <div class="stat-card">
                <h3>自动回复率</h3>
                <div class="value" id="replyRate">0%</div>
            </div>
        </div>

        <div class="test-section">
            <h2>测试AI回复</h2>
            <input type="text" id="testMessage" class="test-input"
                   placeholder="输入测试消息...">
            <button class="test-btn" onclick="testAI()">测试</button>
            <div id="testResponse" class="test-response"></div>
        </div>

        <div class="messages-section">
            <h2>最近消息</h2>
            <div id="messagesList"></div>
        </div>
    </div>

    <script>
        // 加载统计数据
        async function loadStats() {
            const response = await fetch('/api/stats');
            const data = await response.json();

            document.getElementById('todayTotal').textContent =
                data.today.total_messages || 0;
            document.getElementById('todayReplies').textContent =
                data.today.auto_replies || 0;
            document.getElementById('todaySenders').textContent =
                data.today.unique_senders || 0;

            const rate = data.today.total_messages > 0
                ? ((data.today.auto_replies /
                    data.today.total_messages) * 100).toFixed(1)
                : 0;
            document.getElementById('replyRate').textContent = rate + '%';
        }

        // 加载消息列表
        async function loadMessages() {
            const response = await fetch('/api/messages?per_page=10');
            const data = await response.json();

            const list = document.getElementById('messagesList');
            list.innerHTML = data.messages.map(msg => `
                <div class="message-item">
                    <div class="message-header">
                        <span class="sender">${msg.sender}</span>
                        <span class="timestamp">${msg.timestamp}</span>
                    </div>
                    <div class="message-content">
                        <strong>消息:</strong> ${msg.message}
                    </div>
                    ${msg.response ? `
                        <div class="response-content">
                            <strong>回复:</strong> ${msg.response}
                            ${msg.auto_replied ?
                                '<span class="auto-badge">自动</span>' : ''}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }

        // 测试AI
        async function testAI() {
            const message = document.getElementById('testMessage').value;
            if (!message) return;

            const response = await fetch('/api/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            const responseDiv = document.getElementById('testResponse');
            responseDiv.style.display = 'block';
            responseDiv.innerHTML =
                `<strong>AI回复:</strong> ${data.response || data.error}`;
        }

        // 初始加载
        loadStats();
        loadMessages();

        // 定时刷新
        setInterval(() => {
            loadStats();
            loadMessages();
        }, 5000);
    </script>
</body>
</html>
    """
    return html


@app.route('/api/stats')
def api_stats():
    """API: 获取统计数据"""
    db = get_db()

    # 今日统计
    today = datetime.now().strftime('%Y-%m-%d')
    today_stats = db.get_daily_stats(today)

    # 总计统计
    total_stats = db.get_total_stats()

    # 最近7天趋势
    weekly = db.get_weekly_stats(7)
    trend = [stat.to_dict() for stat in weekly]

    return jsonify({
        'today': today_stats.to_dict() if today_stats else {},
        'total': total_stats,
        'trend': list(reversed(trend))
    })


@app.route('/api/messages')
def api_messages():
    """API: 获取消息列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    db = get_db()

    # 分页查询
    offset = (page - 1) * per_page
    messages = db.get_messages(limit=per_page, offset=offset)

    # 获取总数(需要直接查询)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM messages")
        total = cursor.fetchone()['total']

    return jsonify({
        'messages': [msg.to_dict() for msg in messages],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API: 获取/更新配置"""
    if request.method == 'GET':
        config = load_config()
        return jsonify(config)

    elif request.method == 'POST':
        data = request.json

        # 保存配置
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True})


@app.route('/api/test', methods=['POST'])
def api_test():
    """API: 测试AI回复"""
    data = request.json
    message = data.get('message', '')

    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    try:
        config = load_config()
        responder = SmartResponder(config)

        response = responder.generate_response(
            message,
            sender_id='web_test_user',
            use_history=False
        )

        return jsonify({
            'success': True,
            'response': response.content
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Web管理界面启动")
    print("=" * 50)
    print("访问地址: http://localhost:5000/dashboard")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
