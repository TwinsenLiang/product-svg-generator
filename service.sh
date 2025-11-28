#!/bin/bash

# ============================================================
# 服务管理脚本通用范本
# ============================================================
#
# 用法: ./service.sh [start|stop|restart|status|logs|help]
#
# 命令说明:
#   start   - 后台启动服务
#   stop    - 停止服务
#   restart - 重启服务
#   status  - 查看服务状态
#   logs    - 查看实时日志
#   help    - 显示帮助信息

# ============================================================
# 配置变量 - 根据实际项目修改这些变量
# ============================================================

# 服务显示名称
SERVICE_NAME="产品SVG生成器"

# 应用名称（用于标识）
APP_NAME="auto_svg_generator"

# PID 文件路径
PID_FILE="app.pid"

# 日志文件路径
LOG_FILE="logs/app.log"

# 启动命令（根据项目类型修改）
# 示例:
#   Python: START_CMD="python app.py"
#   Node.js: START_CMD="node app.js"
#   Go: START_CMD="./app"
#   Java: START_CMD="java -jar app.jar"
START_CMD="python run.py"

# 服务端口（用于状态检查，可选）
SERVICE_PORT="8000"

# 是否启用 Python 虚拟环境 (true/false)
USE_VENV="true"

# 是否需要检查依赖 (true/false)
CHECK_DEPS="true"

# 依赖文件路径（如果 CHECK_DEPS=true）
DEPS_FILE="requirements.txt"

# ============================================================
# 以下为通用功能代码，一般不需要修改
# ============================================================

# 显示帮助信息
show_help() {
    echo "$SERVICE_NAME - 服务管理脚本"
    echo ""
    echo "用法: $0 [start|stop|restart|status|logs|help]"
    echo ""
    echo "命令说明:"
    echo "  start   - 后台启动服务"
    echo "  stop    - 停止服务"
    echo "  restart - 重启服务"
    echo "  status  - 查看服务状态"
    echo "  logs    - 查看实时日志"
    echo "  help    - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动服务"
    echo "  $0 status   # 查看状态"
    echo "  $0 logs     # 查看日志"
    echo "  $0 stop     # 停止服务"
}

# 检查 Python 环境（仅在 USE_VENV=true 时使用）
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "错误: 未找到 Python3，请先安装 Python3"
        exit 1
    fi
}

# 检查虚拟环境（仅在 USE_VENV=true 时使用）
check_venv() {
    if [ ! -d "venv" ]; then
        echo "正在创建虚拟环境..."
        python3 -m venv venv

        if [ $? -ne 0 ]; then
            echo "错误: 虚拟环境创建失败"
            exit 1
        fi
    fi
}

# 安装依赖（仅在 CHECK_DEPS=true 时使用）
install_deps() {
    if [ ! -f "$DEPS_FILE" ]; then
        echo "警告: 依赖文件 $DEPS_FILE 不存在，跳过依赖安装"
        return
    fi

    echo "检查并安装依赖包..."

    if [ "$USE_VENV" = "true" ]; then
        source venv/bin/activate
    fi

    pip install -r "$DEPS_FILE" > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        echo "错误: 依赖包安装失败"
        exit 1
    fi

    echo "依赖包检查完成"
}

# 启动服务
start_service() {
    echo "=========================================="
    echo "$SERVICE_NAME - 启动服务"
    echo "=========================================="

    # 检查服务是否已经运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "服务已经在运行中 (PID: $PID)"
            echo "如需重启，请使用: $0 restart"
            exit 1
        else
            echo "PID 文件存在但进程不存在，清理旧的 PID 文件"
            rm -f $PID_FILE
        fi
    fi

    # 检查环境和依赖（如果启用）
    if [ "$USE_VENV" = "true" ]; then
        check_python
        check_venv
    fi

    if [ "$CHECK_DEPS" = "true" ]; then
        install_deps
    fi

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    echo "正在启动服务..."

    # 准备启动命令
    if [ "$USE_VENV" = "true" ]; then
        EXEC_CMD="source venv/bin/activate && $START_CMD"
    else
        EXEC_CMD="$START_CMD"
    fi

    # 启动服务
    nohup bash -c "$EXEC_CMD" > "$LOG_FILE" 2>&1 &
    PID=$!

    # 保存 PID
    echo $PID > $PID_FILE

    # 等待启动
    sleep 2

    # 检查进程是否真的在运行
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ 服务启动成功!"
        echo "  PID: $PID"
        if [ -n "$SERVICE_PORT" ]; then
            echo "  访问地址: http://localhost:$SERVICE_PORT"
        fi
        echo "  日志文件: $LOG_FILE"
        echo ""
        echo "管理命令:"
        echo "  $0 status - 查看状态"
        echo "  $0 logs   - 查看日志"
        echo "  $0 stop   - 停止服务"
    else
        echo "✗ 服务启动失败，请检查日志: $LOG_FILE"
        rm -f $PID_FILE
        exit 1
    fi
}

# 停止服务
stop_service() {
    echo "=========================================="
    echo "$SERVICE_NAME - 停止服务"
    echo "=========================================="

    # 检查 PID 文件是否存在
    if [ ! -f "$PID_FILE" ]; then
        echo "服务未运行（PID 文件不存在）"
        exit 0
    fi

    # 读取 PID
    PID=$(cat $PID_FILE)

    # 检查进程是否存在
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "进程不存在 (PID: $PID)，清理 PID 文件"
        rm -f $PID_FILE
        exit 0
    fi

    echo "正在停止服务 (PID: $PID)..."

    # 尝试优雅停止
    kill $PID

    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "✓ 服务已优雅停止"
            rm -f $PID_FILE
            exit 0
        fi
        echo "等待进程结束... ($i/10)"
        sleep 1
    done

    # 如果优雅停止失败，强制停止
    echo "优雅停止失败，强制停止服务..."
    kill -9 $PID

    # 再次检查
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✓ 服务已强制停止"
        rm -f $PID_FILE
        exit 0
    else
        echo "✗ 无法停止服务，请手动检查"
        exit 1
    fi
}

# 重启服务
restart_service() {
    echo "=========================================="
    echo "$SERVICE_NAME - 重启服务"
    echo "=========================================="

    echo "正在停止服务..."
    stop_service

    echo ""
    echo "正在启动服务..."
    start_service
}

# 查看服务状态
show_status() {
    echo "=========================================="
    echo "$SERVICE_NAME - 服务状态"
    echo "=========================================="

    # 检查 PID 文件是否存在
    if [ ! -f "$PID_FILE" ]; then
        echo "服务状态: 未运行"
        echo "PID 文件不存在"
        echo ""
        echo "启动服务: $0 start"
        exit 0
    fi

    # 读取 PID
    PID=$(cat $PID_FILE)

    # 检查进程是否存在
    if ps -p $PID > /dev/null 2>&1; then
        # 获取进程信息
        CMDLINE=$(ps -p $PID -o cmd --no-headers)
        START_TIME=$(ps -p $PID -o lstart --no-headers)
        CPU_USAGE=$(ps -p $PID -o %cpu --no-headers)
        MEM_USAGE=$(ps -p $PID -o %mem --no-headers)

        echo "服务状态: ✓ 正在运行"
        echo "进程ID: $PID"
        echo "启动时间: $START_TIME"
        echo "CPU使用: ${CPU_USAGE}%"
        echo "内存使用: ${MEM_USAGE}%"
        echo "命令行: $CMDLINE"
        echo ""
        if [ -n "$SERVICE_PORT" ]; then
            echo "访问地址: http://localhost:$SERVICE_PORT"
        fi
        echo "日志文件: $LOG_FILE"
        echo ""
        echo "管理命令:"
        echo "  $0 logs     - 查看日志"
        echo "  $0 restart  - 重启服务"
        echo "  $0 stop     - 停止服务"

        # 检查端口是否在监听（如果配置了端口）
        if [ -n "$SERVICE_PORT" ]; then
            echo ""
            echo "端口监听状态:"
            if command -v netstat &> /dev/null; then
                if netstat -tlnp 2>/dev/null | grep ":$SERVICE_PORT " > /dev/null; then
                    echo "  端口 $SERVICE_PORT: ✓ 正在监听"
                else
                    echo "  端口 $SERVICE_PORT: ✗ 未监听"
                fi
            elif command -v ss &> /dev/null; then
                if ss -tlnp 2>/dev/null | grep ":$SERVICE_PORT " > /dev/null; then
                    echo "  端口 $SERVICE_PORT: ✓ 正在监听"
                else
                    echo "  端口 $SERVICE_PORT: ✗ 未监听"
                fi
            else
                echo "  (无法检查端口状态，缺少 netstat 或 ss 命令)"
            fi
        fi

    else
        echo "服务状态: ✗ 进程不存在"
        echo "PID 文件存在但进程不在运行"
        echo "清理 PID 文件..."
        rm -f $PID_FILE
        echo ""
        echo "启动服务: $0 start"
    fi
}

# 查看日志
show_logs() {
    echo "=========================================="
    echo "$SERVICE_NAME - 实时日志"
    echo "=========================================="
    echo "按 Ctrl+C 退出日志查看"
    echo ""

    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "日志文件不存在: $LOG_FILE"
        echo "请先启动服务: $0 start"
    fi
}

# 主程序
main() {
    case "$1" in
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            echo "错误: 未知命令 '$1'"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主程序
main "$@"
