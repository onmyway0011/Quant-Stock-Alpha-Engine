#!/bin/bash

# 量化股票交易系统部署脚本
# 支持本地开发、Docker和生产环境部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
🚀 量化股票交易系统部署脚本

用法: $0 [选项] <部署模式>

部署模式:
  dev         开发环境部署
  docker      Docker容器部署
  prod        生产环境部署
  stop        停止所有服务
  clean       清理部署环境

选项:
  -h, --help     显示帮助信息
  -v, --verbose  详细输出
  --no-deps      跳过依赖检查
  --force        强制重新部署

示例:
  $0 dev                    # 开发环境部署
  $0 docker                 # Docker部署
  $0 prod --force           # 强制生产环境部署
  $0 stop                   # 停止所有服务

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi
    
    # 检查Docker (如果需要)
    if [[ "$DEPLOY_MODE" == "docker" || "$DEPLOY_MODE" == "prod" ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker 未安装"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            log_error "Docker Compose 未安装"
            exit 1
        fi
    fi
    
    log_success "依赖检查完成"
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."
    
    # 创建.env文件（如果不存在）
    if [[ ! -f ../.env ]]; then
        if [[ -f ../.env.example ]]; then
            cp ../.env.example ../.env
            log_warning "已创建.env文件，请配置相关API密钥"
        else
            log_error ".env.example文件不存在"
            exit 1
        fi
    fi
    
    # 根据部署模式设置环境
    case $DEPLOY_MODE in
        "dev")
            export ENVIRONMENT=development
            export DEBUG=true
            ;;
        "docker")
            export ENVIRONMENT=docker
            export DEBUG=false
            ;;
        "prod")
            export ENVIRONMENT=production
            export DEBUG=false
            ;;
    esac
    
    log_success "环境变量设置完成"
}

# 开发环境部署
deploy_dev() {
    log_info "开始开发环境部署..."
    
    # 创建虚拟环境
    if [[ ! -d "../venv" ]]; then
        log_info "创建Python虚拟环境..."
        python3 -m venv ../venv
    fi
    
    # 激活虚拟环境
    source ../venv/bin/activate
    
    # 安装依赖
    log_info "安装Python依赖..."
    pip install -r ../requirements.txt
    
    # 创建必要目录
    mkdir -p ../logs ../data ../config
    
    # 初始化数据库
    log_info "初始化数据库..."
    python3 -c "from src.models.models import Base; from sqlalchemy import create_engine; engine = create_engine('sqlite:///trading.db'); Base.metadata.create_all(engine)" 2>/dev/null || true
    
    # 运行测试
    if [[ "$SKIP_TESTS" != "true" ]]; then
        log_info "运行系统测试..."
        cd ..
        python3 scripts/run_tests.py --quick
        cd deployment
    fi
    
    log_success "开发环境部署完成"
    log_info "启动命令:"
    echo "  cd .. && python3 main.py"
    echo "  cd .. && python3 scripts/start_web_config.py"
}

# Docker部署
deploy_docker() {
    log_info "开始Docker部署..."
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    log_info "启动Docker服务..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose ps
    
    log_success "Docker部署完成"
    log_info "访问地址:"
    echo "  Web配置界面: http://localhost:8080"
    echo "  n8n工作流: http://localhost:5678"
    echo "  Grafana监控: http://localhost:3000"
}

# 生产环境部署
deploy_prod() {
    log_info "开始生产环境部署..."
    
    # 安全检查
    log_warning "生产环境部署需要额外的安全配置"
    read -p "确认继续生产环境部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    # 创建生产环境配置
    if [[ ! -f "docker-compose.prod.yml" ]]; then
        log_info "创建生产环境配置..."
        cp docker-compose.yml docker-compose.prod.yml
        # 这里可以添加生产环境特定的配置修改
    fi
    
    # 部署
    log_info "部署生产环境..."
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "生产环境部署完成"
    log_warning "请确保:"
    echo "  1. 配置了正确的SSL证书"
    echo "  2. 设置了防火墙规则"
    echo "  3. 配置了监控和日志收集"
    echo "  4. 定期备份数据"
}

# 停止服务
stop_services() {
    log_info "停止所有服务..."
    
    # 停止Docker服务
    if [[ -f "docker-compose.yml" ]]; then
        docker-compose down
    fi
    
    # 停止开发环境服务
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "python.*start_web_config.py" 2>/dev/null || true
    
    log_success "所有服务已停止"
}

# 清理环境
clean_environment() {
    log_info "清理部署环境..."
    
    # 停止服务
    stop_services
    
    # 清理Docker资源
    if command -v docker &> /dev/null; then
        log_info "清理Docker资源..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
        docker system prune -f
    fi
    
    # 清理临时文件
    log_info "清理临时文件..."
    rm -rf ../logs/* ../data/cache/* ../data/temp/*
    
    log_success "环境清理完成"
}

# 主函数
main() {
    # 解析参数
    DEPLOY_MODE=""
    VERBOSE=false
    SKIP_DEPS=false
    FORCE=false
    SKIP_TESTS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --no-deps)
                SKIP_DEPS=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            dev|docker|prod|stop|clean)
                DEPLOY_MODE=$1
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查部署模式
    if [[ -z "$DEPLOY_MODE" ]]; then
        log_error "请指定部署模式"
        show_help
        exit 1
    fi
    
    # 显示部署信息
    log_info "量化股票交易系统部署"
    log_info "部署模式: $DEPLOY_MODE"
    log_info "详细输出: $VERBOSE"
    log_info "跳过依赖: $SKIP_DEPS"
    log_info "强制部署: $FORCE"
    echo
    
    # 切换到项目根目录
    cd "$(dirname "$0")"
    
    # 执行部署
    case $DEPLOY_MODE in
        "dev")
            [[ "$SKIP_DEPS" != "true" ]] && check_dependencies
            setup_environment
            deploy_dev
            ;;
        "docker")
            [[ "$SKIP_DEPS" != "true" ]] && check_dependencies
            setup_environment
            deploy_docker
            ;;
        "prod")
            [[ "$SKIP_DEPS" != "true" ]] && check_dependencies
            setup_environment
            deploy_prod
            ;;
        "stop")
            stop_services
            ;;
        "clean")
            clean_environment
            ;;
        *)
            log_error "不支持的部署模式: $DEPLOY_MODE"
            exit 1
            ;;
    esac
    
    log_success "部署脚本执行完成"
}

# 执行主函数
main "$@"