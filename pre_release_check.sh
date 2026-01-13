#!/bin/bash
# 预发布安全检查脚本

echo "========================================="
echo "生产环境部署前安全检查"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查计数
PASS=0
FAIL=0
WARN=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

echo "1. 检查敏感文件..."
echo "-------------------"

# 检查是否存在真实配置文件
if [ -f ".env" ]; then
    check_warn ".env 文件存在（确保不被提交）"

    # 检查是否包含示例密钥
    if grep -q "sk-your-api-key-here\|sk-xxx\|your-api-key-here" .env 2>/dev/null; then
        check_fail ".env 包含示例密钥，请配置真实密钥"
    else
        check_pass ".env 已配置（请确保密钥安全）"
    fi

    # 检查文件权限
    PERMS=$(stat -c "%a" .env 2>/dev/null || stat -f "%Lp" .env 2>/dev/null)
    if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
        check_warn ".env 权限不安全: $PERMS（建议 600）"
    else
        check_pass ".env 文件权限安全: $PERMS"
    fi
else
    check_warn ".env 文件不存在（部署时需要创建）"
fi

if [ -f "config.json" ]; then
    check_warn "config.json 存在（检查是否包含真实密钥）"

    if grep -q '"sk-[^"]*"' config.json 2>/dev/null; then
        check_fail "config.json 可能包含真实API密钥！"
    fi
else
    check_pass "config.json 不存在（使用 .env 更安全）"
fi

echo ""
echo "2. 检查 .gitignore..."
echo "-------------------"

if [ -f ".gitignore" ]; then
    check_pass ".gitignore 存在"

    # 检查关键条目
    for item in ".env" "config.json" "*.db" "*.log" "__pycache__" ".mypy_cache"; do
        if grep -q "^$item" .gitignore; then
            check_pass ".gitignore 包含 $item"
        else
            check_warn ".gitignore 缺少 $item"
        fi
    done
else
    check_fail ".gitignore 不存在！"
fi

echo ""
echo "3. 检查临时文件和缓存..."
echo "-------------------"

# 检查 Python 缓存
if [ -d "__pycache__" ]; then
    check_warn "__pycache__ 目录存在"
else
    check_pass "无 Python 缓存目录"
fi

if [ -d ".mypy_cache" ]; then
    check_warn ".mypy_cache 目录存在"
else
    check_pass "无 mypy 缓存目录"
fi

# 检查数据库文件
DB_COUNT=$(find . -maxdepth 1 -name "*.db" -o -name "*.sqlite" 2>/dev/null | wc -l)
if [ $DB_COUNT -gt 0 ]; then
    check_warn "发现 $DB_COUNT 个数据库文件（应在 .gitignore 中）"
else
    check_pass "无数据库文件"
fi

# 检查日志文件
LOG_COUNT=$(find . -maxdepth 1 -name "*.log" 2>/dev/null | wc -l)
if [ $LOG_COUNT -gt 0 ]; then
    check_warn "发现 $LOG_COUNT 个日志文件"
else
    check_pass "无日志文件"
fi

echo ""
echo "4. 检查代码安全性..."
echo "-------------------"

# 检查硬编码密钥
if grep -r "sk-[a-zA-Z0-9]\{20,\}" --include="*.py" . 2>/dev/null | grep -v "example\|your\|xxx" > /dev/null; then
    check_fail "发现可能的硬编码API密钥！"
else
    check_pass "无硬编码API密钥"
fi

# 检查敏感词
if grep -r "TODO\|FIXME\|XXX\|HACK" --include="*.py" . 2>/dev/null > /dev/null; then
    check_warn "代码中存在开发标记"
else
    check_pass "无开发标记"
fi

echo ""
echo "5. 检查必需文件..."
echo "-------------------"

REQUIRED_FILES=(
    "README.md"
    "requirements.txt"
    ".env.example"
    "config.json.example"
    "core/bot.py"
    "managers/__init__.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "必需文件存在: $file"
    else
        check_fail "缺少必需文件: $file"
    fi
done

echo ""
echo "6. 检查文档..."
echo "-------------------"

if [ -f "README.md" ]; then
    check_pass "README.md 存在"

    # 检查关键章节
    for keyword in "快速开始" "配置" "运行" "安全"; do
        if grep -q "$keyword" README.md 2>/dev/null; then
            check_pass "README.md 包含: $keyword"
        fi
    done
fi

if [ -f "CHECKLIST.md" ]; then
    check_pass "CHECKLIST.md 存在"
else
    check_warn "建议添加 CHECKLIST.md"
fi

echo ""
echo "========================================="
echo "检查结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASS${NC}"
echo -e "${YELLOW}警告: $WARN${NC}"
echo -e "${RED}失败: $FAIL${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ 发现严重问题，请修复后再部署！${NC}"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}⚠️  存在警告项，建议检查后再部署${NC}"
    exit 0
else
    echo -e "${GREEN}✅ 所有检查通过，可以部署！${NC}"
    exit 0
fi
