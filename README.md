# 微信RPA自动回复机器人

> 基于RPA+AI技术的微信自动回复机器人,支持智能回复、消息监控、数据分析

## 🌟 版本说明

### ⭐ 新版本 (推荐)
- **位置**: [core/bot.py](core/bot.py)
- **架构**: 模块化设计,职责分离
- **特性**:
  - ✅ 环境变量配置 (安全性更高)
  - ✅ 数据库连接池 (性能更好)
  - ✅ 重试机制 & 速率限制
  - ✅ 会话持久化
  - ✅ 完整的类型提示


## 📋 功能特点

- ✅ 自动监控微信消息
- ✅ AI智能回复(支持多种LLM)
- ✅ 意图识别和上下文管理
- ✅ 消息记录和统计分析
- ✅ 黑名单/白名单过滤
- ✅ 回复延迟模拟(避免被检测)
- ✅ 每日回复限额
- ✅ 数据持久化存储
- ✅ Web管理界面

## 🏗️ 技术架构

```
微信PC客户端 ←→ RPA控制层 ←→ 消息处理层 ←→ AI分析层 ←→ 数据存储层
    ↓              ↓              ↓            ↓           ↓
  界面操作      图像识别        消息提取     LLM调用     SQLite
```

### 技术栈

- **RPA框架**: PyAutoGUI, Pywinauto
- **图像处理**: OpenCV, PIL
- **文字识别**: Tesseract OCR
- **AI模型**: OpenAI / DeepSeek / 通义千问 / 文心一言
- **数据存储**: SQLite (WAL模式)
- **Web框架**: Flask
- **语言**: Python 3.8+

---

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- macOS / Windows / Linux
- Python 3.8+
- 微信PC客户端(已登录)

#### 安装依赖

```bash
# 克隆项目
cd /path/to/project

# 运行安装脚本 (推荐)
chmod +x setup.sh
./setup.sh

# 或手动安装
pip install -r requirements.txt
```

#### 安装Tesseract OCR(必需)

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Ubuntu:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

**Windows:**
下载安装包: https://github.com/UB-Mannheim/tesseract/wiki

---

### 2. 配置

#### 方式一: 环境变量 (推荐) ⭐

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vim .env
```

```bash
# .env 文件内容
AI_API_KEY=sk-your-api-key-here
AI_MODEL=deepseek-chat
AI_BASE_URL=https://api.deepseek.com/v1
MAX_DAILY_REPLIES=100
REPLY_DELAY_MIN=2
REPLY_DELAY_MAX=5
```

#### 方式二: 配置文件

```bash
# 复制配置模板
cp config.json.example config.json

# 编辑 config.json
vim config.json
```

```json
{
  "wechat_window_name": "微信",
  "reply_delay_min": 2,
  "reply_delay_max": 5,
  "max_daily_replies": 100,
  "ai_enabled": true,
  "ai_model": "deepseek-chat",
  "ai_api_key": "sk-your-api-key-here",
  "ai_base_url": "https://api.deepseek.com/v1"
}
```

#### API密钥获取

**DeepSeek (推荐,国内):**
- 官网: https://platform.deepseek.com/
- 新用户赠送额度
- API便宜效果好

**OpenAI:**
- 官网: https://platform.openai.com/
- 需要国际支付

**通义千问:**
- 官网: https://dashscope.aliyun.com/
- 阿里云提供

---

### 3. 运行

#### 🌟 使用新版本 (推荐)

```bash
# 测试模式
python3 core/bot.py test

# 正常运行
python3 core/bot.py

# 或使用启动脚本
./start.sh

# 后台运行
nohup python3 core/bot.py > logs/bot.log 2>&1 &
```

#### 🔵 使用原版本 (兼容)

```bash
# 测试模式
python3 wechat_rpa_bot.py test

# 正常运行
python3 wechat_rpa_bot.py

# 或使用启动脚本
./start_legacy.sh
```

#### 🌐 Web管理界面

```bash
# 启动Web界面
python3 web_manager.py

# 或使用脚本
./start_web.sh

# 访问
http://localhost:5000/dashboard
```

---

## 🔧 工作原理

### 1. 消息监控

机器人通过以下方式检测新消息:

```python
# 方法1: 图像识别 - 检测未读红点
screenshot = take_screenshot()
red_dots = detect_red_dots(screenshot)

# 方法2: OCR识别 - 读取消息内容
messages = ocr_read_text(screenshot)
```

### 2. 消息处理流程

```
1. 定期截图 (每2秒)
   ↓
2. 检测新消息 (红点/OCR)
   ↓
3. 读取消息内容
   ↓
4. 判断是否回复 (白名单/关键词/限额)
   ↓
5. AI生成回复
   ↓
6. 延迟等待 (2-5秒,模拟人类)
   ↓
7. 发送回复
   ↓
8. 记录日志
```

### 3. AI回复生成

```python
# 意图识别
intent = detect_intent(message)  # greeting/inquiry/complaint/...

# 上下文管理
history = get_conversation_history(sender_id)

# LLM调用 (带重试)
response = openai.ChatCompletion.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
        # ... 历史对话
    ],
    max_retries=3  # 自动重试
)
```

---

## 📊 高级配置

### 1. 自定义回复规则

编辑 `config.json`:

```json
{
  "auto_reply_keywords": ["在吗", "你好", "咨询", "帮助"],
  "blacklist": ["广告号1", "推广号2"],
  "whitelist": ["重要客户A", "VIP客户B"],
  "fallback_responses": {
    "greeting": "您好! 有什么可以帮您?",
    "default": "收到,稍后回复"
  }
}
```

### 2. 切换AI模型

```json
{
  "ai_model": "deepseek-chat",  // 或 gpt-4, qwen-turbo 等
  "ai_base_url": "https://api.deepseek.com/v1"
}
```

### 3. 调整安全参数

```json
{
  "reply_delay_min": 2,    // 最小延迟(秒)
  "reply_delay_max": 5,    // 最大延迟(秒)
  "max_daily_replies": 100 // 每日最大回复数
}
```

### 4. 环境变量配置

支持的环境变量 (优先级高于配置文件):

```bash
# AI配置
AI_API_KEY=sk-xxx              # API密钥
AI_MODEL=deepseek-chat         # 模型名称
AI_BASE_URL=https://...        # API地址

# 运行参数
MAX_DAILY_REPLIES=100          # 每日限额
REPLY_DELAY_MIN=2              # 最小延迟
REPLY_DELAY_MAX=5              # 最大延迟

# 数据库
DB_PATH=wechat_bot.db          # 数据库路径

# 日志
LOG_LEVEL=INFO                 # 日志级别
```

---

## 📈 数据管理

### 查看消息记录

```bash
# 进入数据库
sqlite3 wechat_bot.db

# 查询最近消息
SELECT * FROM messages ORDER BY timestamp DESC LIMIT 10;

# 查看今日统计
SELECT * FROM daily_stats WHERE date = date('now');
```

### Web界面管理

访问 http://localhost:5000/dashboard 查看:
- 实时统计数据
- 消息记录列表
- AI回复测试
- 配置管理

### 导出数据

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('wechat_bot.db')
df = pd.read_sql_query("SELECT * FROM messages", conn)
df.to_excel('messages.xlsx', index=False)
```

---

## ❓ 常见问题

### Q1: 如何避免微信被封?

**最佳实践:**
1. ✅ 使用小号测试
2. ✅ 设置合理的回复延迟(2-5秒)
3. ✅ 限制每日回复数量(<100)
4. ✅ 避免频繁重复操作
5. ✅ 使用白名单模式
6. ❌ 不要群发广告
7. ❌ 不要添加陌生人为好友

### Q2: OCR识别不准确怎么办?

**优化方法:**
1. 升级Tesseract版本
2. 调整截图区域
3. 使用付费OCR API(百度/腾讯)
4. 使用微信hook(更稳定但有风险)

### Q3: AI回复质量如何提升?

**优化方向:**
1. 选择更好的模型(GPT-4 > DeepSeek > GPT-3.5)
2. 优化系统提示词(system prompt)
3. 增加上下文轮数
4. 添加知识库(RAG)
5. 使用Fine-tuning模型

### Q4: 能否用于企业微信?

可以,但建议使用官方API:

```python
# 企业微信官方API(推荐)
from work.weixin.qq.com import API

api = WeComAPI(corpid, corpsecret)
api.send_message(user_id, message)
```

### Q5: 如何部署到服务器?

**方案1: VPS + 远程桌面**
- 购买Windows VPS
- 远程桌面登录微信
- 运行机器人

**方案2: Docker**
```dockerfile
FROM python:3.9
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "core/bot.py"]
```

---

## 📚 项目结构

```
wechat-rpa-bot/
├── core/                      # 核心模块 (新版本)
│   ├── __init__.py
│   └── bot.py                 # 优化版主程序 ⭐
├── managers/                  # 管理器模块
│   ├── __init__.py
│   ├── ai_responder.py        # AI回复管理器
│   ├── database.py            # 数据库管理器
│   └── message_detector.py    # 消息检测器
├── config/                    # 配置模块
│   ├── __init__.py
│   └── config_manager.py      # 配置管理器
├── utils/                     # 工具模块
│   └── __init__.py
├── wechat_rpa_bot.py          # 原版主程序 (兼容)
├── web_manager.py             # Web管理界面
├── config.json.example        # 配置示例
├── .env.example               # 环境变量示例 ⭐
├── requirements.txt           # 依赖列表
├── setup.sh                   # 安装脚本
├── deploy.sh                  # 部署脚本
├── README.md                  # 本文档
├── OPTIMIZATION_REPORT.md     # 优化报告
├── wechat_bot.db              # 数据库(自动生成)
└── screenshots/               # 截图目录
```

---

## 🔐 安全建议

### ⚠️ 法律合规

1. 仅用于个人学习和合法用途
2. 不要用于骚扰、垃圾信息
3. 遵守微信用户协议
4. 保护用户隐私
5. 不要窃取他人数据

### 🔒 技术安全

1. **API密钥**: 使用环境变量,不要硬编码
2. **数据存储**: 数据库文件设置适当权限
3. **日志脱敏**: 避免记录敏感信息
4. **访问控制**: Web界面建议添加认证

```python
# 推荐配置方式
import os
api_key = os.getenv('AI_API_KEY')  # ✅ 安全

# 不推荐
api_key = "sk-xxx"  # ❌ 危险
```

---

## 🗺️ 开发路线图

### 已完成 ✅
- [x] 基础RPA框架
- [x] AI回复集成
- [x] 意图识别
- [x] 数据持久化
- [x] 安全防护
- [x] 模块化重构
- [x] 环境变量配置
- [x] Web管理界面

### 计划中 🚧
- [ ] Docker容器化
- [ ] 知识库集成(RAG)
- [ ] 多账号管理
- [ ] 性能监控
- [ ] 更多LLM支持
- [ ] 单元测试覆盖

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

### 开发流程

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

---

## 📄 许可证

MIT License - 仅供学习交流使用

---

## 📞 联系方式

- Issue: [GitHub Issues](https://github.com/yourusername/wechat-rpa-bot/issues)
- Email: your-email@example.com

---

## 🙏 致谢

感谢以下开源项目:
- PyAutoGUI
- Pywinauto
- OpenCV
- Tesseract OCR
- OpenAI Python SDK

---

## ⚠️ 免责声明

本项目仅供学习研究使用,使用者需自行承担风险。请遵守相关法律法规和平台协议。

---

**文档更新**: 2026-01-13
**版本**: v2.0 (优化版本)
