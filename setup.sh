#!/bin/bash
# 微信RPA机器人安装脚本

echo "========================================="
echo "微信RPA机器人 - 环境配置"
echo "========================================="
echo ""

# 检查Python版本
echo "检查Python版本..."
python3 --version

# 升级pip
echo ""
echo "升级pip..."
python3 -m pip install --upgrade pip

# 安装依赖
echo ""
echo "安装Python依赖包..."
pip3 install -r requirements.txt

# 检查Tesseract OCR
echo ""
echo "检查Tesseract OCR..."
if ! command -v tesseract &> /dev/null; then
    echo "⚠️  警告: 未安装Tesseract OCR"
    echo ""
    echo "请安装Tesseract OCR:"
    echo "  macOS:   brew install tesseract tesseract-lang"
    echo "  Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-chi-sim"
    echo "  Windows: 下载安装包 https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
else
    echo "✓ Tesseract OCR已安装"
    tesseract --version
fi

# 创建配置文件
echo ""
echo "创建配置文件..."

# 创建 .env 文件
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ 已创建.env环境变量文件"
    echo "⚠️  请编辑.env填写AI API密钥 (推荐方式)"
else
    echo "✓ .env已存在"
fi

# 创建 config.json
if [ ! -f "config.json" ]; then
    cp config.json.example config.json
    echo "✓ 已创建config.json"
    echo "⚠️  也可以编辑config.json填写配置"
else
    echo "✓ config.json已存在"
fi

# 创建数据目录
mkdir -p logs
mkdir -p screenshots
mkdir -p data

echo ""
echo "========================================="
echo "安装完成!"
echo "========================================="
echo ""
echo "下一步:"
echo ""
echo "1. 配置AI API密钥 (二选一):"
echo "   方式一 (推荐): 编辑 .env 文件"
echo "   vim .env"
echo "   修改: AI_API_KEY=sk-your-api-key-here"
echo ""
echo "   方式二: 编辑 config.json 文件"
echo "   vim config.json"
echo "   修改: ai_api_key 字段"
echo ""
echo "2. 启动微信PC客户端并登录"
echo ""
echo "3. 运行机器人 (推荐新版本):"
echo "   python3 core/bot.py"
echo ""
echo "   或使用原版本 (兼容保留):"
echo "   python3 wechat_rpa_bot.py"
echo ""
echo "测试模式:"
echo "   python3 core/bot.py test"
echo ""
echo "Web管理界面:"
echo "   python3 web_manager.py"
echo "   访问: http://localhost:5000/dashboard"
echo ""
