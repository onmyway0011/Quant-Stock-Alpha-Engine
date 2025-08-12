#!/bin/bash

# 量化股票交易系统停止脚本
# Quant Stock Alpha Engine Stop Script

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

# 查找运行中的进程
find_processes() {
    print_info "查找运行中的交易系统进程..."
    
    # 查找主进程
    main_pids=$(pgrep -f "python.*main.py" 2>/dev/null || true)
    
    # 查找测试进程
    test_pids=$(pgrep -f "python.*test_system.py" 2>/dev/null || true)
    
    if [ -z "$main_pids" ] && [ -z "$test_pids" ]; then
        print_warning "未找到运行中的交易系统进程"
        return 1
    fi
    
    if [ -n "$main_pids" ]; then
        print_info "找到主系统进程: $main_pids"
        echo "进程详情:"
        ps -p $main_pids -o pid,ppid,cmd 2>/dev/null || true
    fi
    
    if [ -n "$test_pids" ]; then
        print_info "找到测试进程: $test_pids"
    fi
    
    return 0
}

# 优雅停止进程
graceful_stop() {
    local pids="$1"
    local process_name="$2"
    
    if [ -z "$pids" ]; then
        return 0
    fi
    
    print_info "正在优雅停止${process_name}进程..."
    
    # 发送SIGTERM信号
    for pid in $pids; do
        if kill -TERM "$pid" 2>/dev/null; then
            print_info "已向进程 $pid 发送停止信号"
        fi
    done
    
    # 等待进程停止
    local wait_time=0
    local max_wait=30
    
    while [ $wait_time -lt $max_wait ]; do
        local running_pids=""
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                running_pids="$running_pids $pid"
            fi
        done
        
        if [ -z "$running_pids" ]; then
            print_success "${process_name}进程已优雅停止"
            return 0
        fi
        
        sleep 1
        wait_time=$((wait_time + 1))
        
        if [ $((wait_time % 5)) -eq 0 ]; then
            print_info "等待${process_name}进程停止... (${wait_time}/${max_wait}秒)"
        fi
    done
    
    # 如果优雅停止失败，强制停止
    print_warning "${process_name}进程未在规定时间内停止，将强制终止"
    for pid in $running_pids; do
        if kill -KILL "$pid" 2>/dev/null; then
            print_warning "强制终止进程 $pid"
        fi
    done
    
    sleep 2
    
    # 再次检查
    local still_running=""
    for pid in $running_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            still_running="$still_running $pid"
        fi
    done
    
    if [ -z "$still_running" ]; then
        print_success "${process_name}进程已强制停止"
    else
        print_error "无法停止${process_name}进程: $still_running"
        return 1
    fi
}

# 清理资源
cleanup_resources() {
    print_info "清理系统资源..."
    
    # 清理临时文件
    if [ -d "/tmp" ]; then
        find /tmp -name "*quant*" -type f -mtime +1 -delete 2>/dev/null || true
        find /tmp -name "*trading*" -type f -mtime +1 -delete 2>/dev/null || true
    fi
    
    # 清理日志文件（保留最近7天）
    if [ -d "logs" ]; then
        find logs -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
    fi
    
    print_success "资源清理完成"
}

# 显示系统状态
show_status() {
    print_info "系统状态检查..."
    
    # 检查进程
    local main_pids=$(pgrep -f "python.*main.py" 2>/dev/null || true)
    local test_pids=$(pgrep -f "python.*test_system.py" 2>/dev/null || true)
    
    if [ -z "$main_pids" ] && [ -z "$test_pids" ]; then
        print_success "✅ 系统已完全停止"
    else
        print_warning "⚠️  仍有进程在运行:"
        if [ -n "$main_pids" ]; then
            echo "   主系统进程: $main_pids"
        fi
        if [ -n "$test_pids" ]; then
            echo "   测试进程: $test_pids"
        fi
    fi
    
    # 检查端口占用（如果有Web界面）
    local port_usage=$(netstat -tlnp 2>/dev/null | grep ":8000\|:5000\|:3000" || true)
    if [ -n "$port_usage" ]; then
        print_info "端口占用情况:"
        echo "$port_usage"
    fi
    
    # 检查日志文件大小
    if [ -f "logs/trading.log" ]; then
        local log_size=$(du -h "logs/trading.log" | cut -f1)
        print_info "主日志文件大小: $log_size"
    fi
}

# 显示帮助信息
show_help() {
    echo "量化股票交易系统停止脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示帮助信息"
    echo "  -f, --force     强制停止所有相关进程"
    echo "  -s, --status    只显示系统状态"
    echo "  -c, --cleanup   停止系统并清理资源"
    echo ""
    echo "示例:"
    echo "  $0              # 优雅停止系统"
    echo "  $0 --force      # 强制停止所有进程"
    echo "  $0 --status     # 查看系统状态"
    echo "  $0 --cleanup    # 停止并清理"
}

# 强制停止所有相关进程
force_stop() {
    print_warning "强制停止所有相关进程..."
    
    # 停止所有Python相关进程
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "python.*test_system.py" 2>/dev/null || true
    
    sleep 2
    
    # 检查是否还有进程
    local remaining=$(pgrep -f "python.*(main|test_system).py" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        print_warning "仍有进程运行，使用SIGKILL强制终止..."
        pkill -9 -f "python.*(main|test_system).py" 2>/dev/null || true
        sleep 1
    fi
    
    print_success "强制停止完成"
}

# 主函数
main() {
    echo "🛑 量化股票交易系统停止脚本"
    echo "======================================"
    
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            force_stop
            show_status
            ;;
        -s|--status)
            show_status
            ;;
        -c|--cleanup)
            if find_processes; then
                main_pids=$(pgrep -f "python.*main.py" 2>/dev/null || true)
                test_pids=$(pgrep -f "python.*test_system.py" 2>/dev/null || true)
                
                graceful_stop "$main_pids" "主系统"
                graceful_stop "$test_pids" "测试"
            fi
            cleanup_resources
            show_status
            ;;
        "")
            # 默认优雅停止
            if find_processes; then
                main_pids=$(pgrep -f "python.*main.py" 2>/dev/null || true)
                test_pids=$(pgrep -f "python.*test_system.py" 2>/dev/null || true)
                
                graceful_stop "$main_pids" "主系统"
                graceful_stop "$test_pids" "测试"
                
                show_status
            else
                print_success "系统未在运行"
            fi
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
    
    echo "======================================"
    print_success "停止脚本执行完成"
}

# 错误处理
trap 'print_error "脚本执行被中断"; exit 1' INT TERM

# 运行主函数
main "$@"