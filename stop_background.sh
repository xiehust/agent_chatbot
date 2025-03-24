#!/bin/bash

PID_FILE="./streamlit.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "未找到PID文件，应用可能未在运行"
    exit 1
fi

# 读取PID
PID=$(cat $PID_FILE)

# 检查进程是否存在
if ps -p $PID > /dev/null; then
    echo "停止Streamlit应用 (PID: $PID)..."
    kill $PID
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null; then
            break
        fi
        echo "等待进程结束..."
        sleep 1
    done
    
    # 如果进程仍在运行，强制终止
    if ps -p $PID > /dev/null; then
        echo "进程未响应，强制终止..."
        kill -9 $PID
    fi
    
    echo "应用已停止"
else
    echo "进程 $PID 不存在，可能已经停止"
fi

# 删除PID文件
rm -f $PID_FILE
