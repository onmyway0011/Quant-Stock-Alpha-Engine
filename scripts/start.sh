#!/bin/bash

# 量化股票交易系统启动脚本
# Quant Stock Alpha Engine Startup Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    print_info "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3未安装，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
        print_success "Python版本检查通过: $python_version"
    else
        print_error "Python版本过低: $python_version，需要3.8+"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    print_info "检查项目依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt文件不存在"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "虚拟环境不存在，正在创建..."
        python3 -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    print_info "安装/更新依赖包..."
    pip install -r requirements.txt
    print_success "依赖安装完成"
}

# 检查配置文件
check_config() {
    print_info "检查配置文件..."
    
    if [ ! -f "config.yaml" ]; then
        print_error "config.yaml配置文件不存在"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        print_warning ".env文件不存在，请复制.env.example并配置"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_info "已复制.env.example到.env，请编辑配置"
        else
            print_error ".env.example文件也不存在"
            exit 1
        fi
    fi
    
    print_success "配置文件检查完成"
}

# 创建必要目录
setup_directories() {
    print_info "创建必要目录..."
    
    mkdir -p logs
    mkdir -p data
    
    print_success "目录创建完成"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    python3 -c "
from src.models.models import Base
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL', 'sqlite:///stock_trading.db')
engine = create_engine(db_url)
Base.metadata.create_all(engine)
print('数据库表创建完成')
" 2>/dev/null || print_warning "数据库初始化可能失败，请检查配置"
    
    print_success "数据库初始化完成"
}

# 运行系统测试
run_test() {
    print_info "运行系统测试..."
    
    if python3 test_system.py; then
        print_success "系统测试通过"
        return 0
    else
        print_warning "系统测试未完全通过，但可以尝试启动"
        return 1
    fi
}

# 启动系统
start_system() {
    print_info "启动量化股票交易系统..."
    
    # 检查是否已有进程在运行
    if pgrep -f "python.*main.py" > /dev/null; then
        print_warning "系统可能已在运行，正在检查..."
        ps aux | grep "python.*main.py" | grep -v grep
        read -p "是否要强制重启？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "正在停止现有进程..."
            pkill -f "python.*main.py" || true
            sleep 2
        else
            print_info "取消启动"
            exit 0
        fi
    fi
    
    # 启动系统
    print_success "🚀 正在启动量化股票交易系统..."
    echo "======================================"
    echo "按 Ctrl+C 停止系统"
    echo "日志文件: logs/trading.log"
    echo "======================================"
    
    python3 main.py
}

# 显示帮助信息
show_help() {
    echo "量化股票交易系统启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -t, --test     只运行测试，不启动系统"
    echo "  -s, --setup    只进行环境设置，不启动系统"
    echo "  --no-test      跳过测试直接启动"
    echo ""
    echo "示例:"
    echo "  $0              # 完整启动流程"
    echo "  $0 --test       # 只运行测试"
    echo "  $0 --setup      # 只进行环境设置"
    echo "  $0 --no-test    # 跳过测试直接启动"
}

# 主函数
main() {
    echo "🎯 量化股票交易系统启动脚本"
    echo "======================================"
    
    # 解析命令行参数
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--test)
            check_python
            check_dependencies
            check_config
            setup_directories
            init_database
            run_test
            exit 0
            ;;
        -s|--setup)
            check_python
            check_dependencies
            check_config
            setup_directories
            init_database
            print_success "环境设置完成"
            exit 0
            ;;
        --no-test)
            check_python
            check_dependencies
            check_config
            setup_directories
            init_database
            start_system
            ;;
        "")
            # 默认完整流程
            check_python
            check_dependencies
            check_config
            setup_directories
            init_database
            
            # 运行测试（可选）
            if run_test; then
                print_success "所有检查通过，准备启动系统"
            else
                read -p "测试未完全通过，是否继续启动？(y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_info "启动已取消"
                    exit 0
                fi
            fi
            
            start_system
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 错误处理
trap 'print_error "脚本执行被中断"; exit 1' INT TERM

# 检查是否在项目根目录
if [ ! -f "main.py" ]; then
    print_error "请在项目根目录运行此脚本"
    exit 1
fi

# 运行主函数
main "$@"