#!/bin/bash

# 设置变量
LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/streamlit_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="./streamlit.pid"

# 创建日志目录（如果不存在）
mkdir -p $LOG_DIR

# 检查是否已有实例在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo "已有一个实例正在运行，PID: $PID"
        echo "如需重启，请先运行 ./stop_background.sh"
        exit 1
    else
        echo "发现过期的PID文件，将被覆盖"
    fi
fi

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
fi

# 在后台启动Streamlit应用，监听所有网络接口
echo "在后台启动Streamlit应用，监听所有网络接口..."
nohup streamlit run streamlit_agent_chat.py --server.headless=true --server.address=0.0.0.0 > $LOG_FILE 2>&1 &

# 保存PID
echo $! > $PID_FILE
echo "应用已在后台启动，PID: $(cat $PID_FILE)"
echo "日志文件: $LOG_FILE"
echo "使用 ./stop_background.sh 停止应用"
