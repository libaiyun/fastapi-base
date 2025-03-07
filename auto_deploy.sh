#!/bin/bash
# * * * * * /bin/bash /data/projects/fastapi-base/auto_deploy.sh >> /data/projects/fastapi-base/deploy.log 2>&1

# 函数：获取本机IP
get_local_ip() {
    prefix=$1
    hostname -I | tr ' ' '\n' | grep "^${prefix//./\\.}" | head -n 1
}

# 函数：打印日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 函数：发送企业微信通知
send_notification() {
    local content="$1"
    curl -s "$QY_NOTIFY_URL" \
        -H 'Content-Type: application/json' \
        -d '{
            "msgtype": "markdown",
            "markdown": {
                "content": "'"${content//\"/\\\"}"'"
            }
        }' || log "发送通知失败"
}

# 检查端口是否被占用
check_port_used() {
    local port=$1
    if command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":$port "
    else
        log "错误：需要安装 ss 或 netstat 来检查端口占用"
        exit 1
    fi
}

# 远程仓库地址
ORIGINAL_REPO_URL="http://192.168.30.28/framework/fastapi-base.git"
GIT_USER="cqvipcq%40outlook.com"
GIT_PASSWD="Cqvip.com"
# 用于部署的分支名
RELEASE_BRANCH="release/1.0.0"
# 服务名
PROJECT_NAME="fastapi-base"
# 脚本的工作目录
WORK_DIR="/data/projects/$PROJECT_NAME"
SERVER_HOST=$(get_local_ip "192.168")
SERVER_PORT="8150"
DOCKER_IMAGE="${PROJECT_NAME}:1.0.0"
CONFIG_FILE="config-prod.yaml"
# 企微群机器人通知webhook地址
QY_NOTIFY_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=013547da-3d78-4a7f-b4a7-e668b192c293"
OPENAPI_URL="http://192.168.98.79:8150/docs"

# 远程仓库地址（带用户名和密码）
REPO_URL="http://${GIT_USER}:${GIT_PASSWD}@${ORIGINAL_REPO_URL#http://}"

# 脚本开头添加锁机制
LOCK_FILE="/tmp/${PROJECT_NAME}.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "已有其他部署进程运行，退出"
    exit 0
fi

set -e  # 一旦发生错误，脚本将退出

if [ -z "$SERVER_HOST" ]; then
    log "错误：无法获取本地IP"
    send_notification "⚠️ 部署失败：无法获取服务IP"
    exit 1
fi
# 启动容器前检查端口占用
if check_port_used "${SERVER_PORT}"; then
    log "错误：宿主机端口 ${SERVER_PORT} 已被占用"
    send_notification "⚠️ 部署失败：端口 ${SERVER_PORT} 冲突"
    exit 1
fi

# 切换到工作目录
cd "$WORK_DIR" || { log "无法进入目录 $WORK_DIR"; exit 1; }

# 设置远程 URL
git remote set-url origin "$REPO_URL"
# 捕获退出信号，在脚本结束时重置远程 URL
trap 'git remote set-url origin "$ORIGINAL_REPO_URL"' EXIT

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]; then
    log "当前分支是 $CURRENT_BRANCH, 正在切换到 $RELEASE_BRANCH"
    git checkout "$RELEASE_BRANCH" || { log "切换分支失败"; exit 1; }
fi

# 更新远程仓库信息
git fetch origin || { log "fetch 失败"; exit 1; }

LOCAL_COMMIT=$(git rev-parse "$RELEASE_BRANCH")
REMOTE_COMMIT=$(git rev-parse "origin/$RELEASE_BRANCH")

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    log "检测到代码更新，开始持续部署流程..."

    # 拉取最新更新
    git pull origin "$RELEASE_BRANCH" || { log "pull 失败"; exit 1; }

    log "此次更新的 commit 列表:"
    git log --oneline "$LOCAL_COMMIT..$REMOTE_COMMIT"

    # 验证配置文件存在
    [[ ! -f "$CONFIG_FILE" ]] && {
        log "创建默认配置文件..."
        touch "$CONFIG_FILE"
    }

    # 构建Docker镜像
    log "开始构建容器镜像..."
    docker build -t "$DOCKER_IMAGE" . --no-cache || {
        log "镜像构建失败";
        send_notification "容器镜像构建失败！\n请检查构建日志"
        exit 1
    }

    # 清理旧容器
    docker rm -f "$PROJECT_NAME" 2>/dev/null && log "旧容器已移除"

    # 启动新容器
    log "启动新版本容器..."
    docker run -d \
        --name "$PROJECT_NAME" \
        --restart unless-stopped \
        -p "${SERVER_PORT}:${SERVER_PORT}" \
        -e APP_ENV=prod \
        -e SERVER_HOST="${SERVER_HOST:-0.0.0.0}" \
        -e SERVER_PORT="${SERVER_PORT}" \
        -v "$(pwd)/$CONFIG_FILE:/app/config-prod.yaml" \
        -v "$(pwd)/log:/app/log" \
        "$DOCKER_IMAGE" || {
            log "容器启动失败";
            send_notification "容器启动失败！\n请检查运行时配置"
            exit 1
        }

    # 生成变更报告
    COMMIT_LIST=$(git log --oneline --no-merges "${LOCAL_COMMIT}..${REMOTE_COMMIT}")
    NOTIFICATION_CONTENT="✅ 容器化部署成功\n\n**版本信息**\n> 镜像版本：${DOCKER_IMAGE}\n> 部署时间：$(date +'%Y-%m-%d %H:%M:%S')\n\n**更新内容**\n"

    while IFS= read -r commit; do
        NOTIFICATION_CONTENT+="> ${commit}\n"
    done <<< "$COMMIT_LIST"

    NOTIFICATION_CONTENT+="\n**访问地址**\n[接口文档](${OPENAPI_URL})"

    # 发送企业微信通知
    send_notification "$NOTIFICATION_CONTENT"
    log "部署流程完成"
else
    log "当前已是最新版本，无需部署"
fi
