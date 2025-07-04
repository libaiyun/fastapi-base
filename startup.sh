#!/bin/bash

set -e

cd /app

echo "启动异步任务调度进程..."
python scheduler_async.py 2>&1 &

echo "启动 Web 服务..."
# exec 替换脚本成为前台进程，作为容器的主服务进程
exec python run.py 2>&1



# #!/bin/bash
# set -e
# echo "启动所有进程到后台..."
# /path/to/process1 &
# /path/to/process2 &
# /path/to/process3 &
# echo "所有进程启动完毕，等待第一个退出的子进程..."
# wait -n  # 等待任何一个直接子进程退出
# echo "有子进程退出！正在终止其他进程并退出容器..."
# kill $(jobs -p) # 尝试杀死其他后台进程（直接子进程）
# wait # 等待它们真正退出 (避免成为僵尸进程，也让kill生效)
# exit 0 # 或根据退出的子进程状态码设置
