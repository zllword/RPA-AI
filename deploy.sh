#!/bin/bash
# 微信RPA机器人 - 部署脚本

set -e  # 遇到错误立即退出

echo "========================================="
echo "微信RPA机器人 - 部署向导"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 已安装"
        return 0
    else
        echo -e "${RED}✗${NC} $1 未安装"
        return 1
    fi
}

# 1. 环境检查
echo "步骤 1/7: 环境检查"
echo "-------------------"

check_command python3 || {
    echo -e "${RED}错误: 未找到Python3${NC}"
    echo "请先安装Python 3.8+"
    exit 1
}

check_command pip3 || {
    echo -e "${YELLOW}警告: pip3未找到,尝试安装...${NC}"
    python3 -m ensurepip --upgrade
}

echo ""

# 2. 安装依赖
echo "步骤 2/7: 安装Python依赖"
echo "-------------------"

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo -e "${GREEN}✓${NC} 依赖安装完成"
else
    echo -e "${YELLOW}⚠${NC} requirements.txt不存在,跳过"
fi

echo ""

# 3. 检查Tesseract
echo "步骤 3/7: 检查OCR引擎"
echo "-------------------"

if check_command tesseract; then
    tesseract --version
else
    echo -e "${YELLOW}⚠${NC} Tesseract OCR未安装"
    echo ""
    echo "请根据你的系统安装:"
    echo "  macOS:   brew install tesseract tesseract-lang"
    echo "  Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-chi-sim"
    echo "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# 4. 配置文件设置
echo "步骤 4/7: 配置文件设置"
echo "-------------------"

# 创建 .env 文件
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} 已创建 .env 环境变量文件"
        echo -e "${YELLOW}⚠${NC} 请编辑 .env 填写API密钥 (推荐方式)"
    else
        echo -e "${RED}✗${NC} .env.example 不存在"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} .env 已存在"
fi

# 创建 config.json
if [ ! -f "config.json" ]; then
    if [ -f "config.json.example" ]; then
        cp config.json.example config.json
        echo -e "${GREEN}✓${NC} 已创建 config.json"
        echo -e "${YELLOW}⚠${NC} 也可以编辑 config.json 配置"
    fi
else
    echo -e "${GREEN}✓${NC} config.json 已存在"
fi

echo ""

# 5. 创建必要目录
echo "步骤 5/7: 创建目录结构"
echo "-------------------"

mkdir -p logs
mkdir -p screenshots
mkdir -p data
mkdir -p backups

echo -e "${GREEN}✓${NC} 目录结构创建完成"

echo ""

# 6. 创建启动脚本
echo "步骤 6/7: 创建启动脚本"
echo "-------------------"

# 新版本启动脚本
cat > start.sh << 'EOF'
#!/bin/bash
# 启动微信RPA机器人 (新版本)

echo "启动机器人 (优化版本)..."

# 激活虚拟环境(如果使用)
# source venv/bin/activate

# 使用新版本 (推荐)
python3 core/bot.py

# 或者后台运行
# nohup python3 core/bot.py > logs/bot.log 2>&1 &
EOF

chmod +x start.sh

# 原版本启动脚本
cat > start_legacy.sh << 'EOF'
#!/bin/bash
# 启动微信RPA机器人 (原版本)

echo "启动机器人 (原版本)..."

# 激活虚拟环境(如果使用)
# source venv/bin/activate

# 使用原版本 (兼容保留)
python3 wechat_rpa_bot.py
EOF

chmod +x start_legacy.sh

# 停止脚本
cat > stop.sh << 'EOF'
#!/bin/bash
# 停止微信RPA机器人

echo "停止机器人..."
pkill -f "python3.*bot.py"
echo "机器人已停止"
EOF

chmod +x stop.sh

# Web管理界面启动脚本
cat > start_web.sh << 'EOF'
#!/bin/bash
# 启动Web管理界面

echo "启动Web管理界面..."
python3 web_manager.py
EOF

chmod +x start_web.sh

echo -e "${GREEN}✓${NC} 启动脚本创建完成"
echo "  - start.sh         启动新版本机器人"
echo "  - start_legacy.sh  启动原版本机器人"
echo "  - stop.sh          停止机器人"
echo "  - start_web.sh     启动Web管理界面"

echo ""

# 7. 显示使用说明
echo "步骤 7/7: 部署完成"
echo "-------------------"

echo ""
echo "========================================="
echo -e "${GREEN}部署完成!${NC}"
echo "========================================="
echo ""
echo -e "${BLUE}版本说明:${NC}"
echo "  新版本 (推荐): 优化的模块化架构"
echo "  原版本 (兼容): 单体架构,保留用于兼容"
echo ""
echo "下一步操作:"
echo ""
echo "1. 配置AI API密钥 (推荐):"
echo "   vim .env"
echo "   修改: AI_API_KEY=sk-your-api-key-here"
echo ""
echo "   或者编辑配置文件:"
echo "   vim config.json"
echo ""
echo "2. 启动微信PC客户端并登录"
echo ""
echo "3. 运行机器人:"
echo ""
echo -e "   ${GREEN}新版本 (推荐):${NC}"
echo "   ./start.sh"
echo "   或"
echo "   python3 core/bot.py"
echo ""
echo -e "   ${YELLOW}原版本 (兼容):${NC}"
echo "   ./start_legacy.sh"
echo "   或"
echo "   python3 wechat_rpa_bot.py"
echo ""
echo "4. 测试模式:"
echo "   python3 core/bot.py test"
echo ""
echo "5. Web管理界面:"
echo "   ./start_web.sh"
echo "   访问: http://localhost:5000/dashboard"
echo ""
echo "6. 查看日志:"
echo "   tail -f wechat_bot.log"
echo "   或"
echo "   tail -f logs/bot.log"
echo ""
echo "7. 停止机器人:"
echo "   ./stop.sh"
echo ""
echo -e "${YELLOW}⚠ 重要提示:${NC}"
echo "- 请使用小号测试"
echo "- 设置合理的回复延迟 (2-5秒)"
echo "- 限制每日回复数量 (<100)"
echo "- 遵守微信使用规范"
echo "- 建议使用白名单模式"
echo ""
echo -e "${BLUE}📖 详细文档:${NC}"
echo "   README.md              - 使用文档"
echo "   OPTIMIZATION_REPORT.md  - 优化说明"
echo ""
echo "祝使用愉快!"
echo ""
