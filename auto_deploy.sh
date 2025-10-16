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

# 统一错误处理函数
handle_error() {
    local error_msg="$1"
    log "错误：$error_msg"
    send_notification "⚠️ **部署失败**: ${error_msg}\n**项目名称**: ${PROJECT_NAME}\n**代码分支**: ${DEPLOY_BRANCH}\n**部署节点**: ${SERVER_HOST}"
    exit 1
}

# 检查端口是否被占用
check_port_used() {
    local port=$1
    if command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":$port "
    else
        handle_error "需要安装 ss 或 netstat 来检查端口占用"
    fi
}

# 处理强制部署参数
FORCE_DEPLOY=0
if [ "$1" == "-f" ] || [ "$1" == "--force" ]; then
    FORCE_DEPLOY=1
    log "检测到强制部署参数"
fi

# 远程仓库地址
ORIGINAL_REPO_URL="http://192.168.30.28/framework/fastapi-base.git"
GIT_USER="cqvipcq%40outlook.com"
GIT_PASSWD="Cqvip.com"
# 用于部署的分支名
DEPLOY_BRANCH="master"
# 服务名
PROJECT_NAME="fastapi-base"
# 部署和映射端口
SERVER_PORT="8001"
# 部署环境 test/prod
APP_ENV="prod"
# 企微群机器人通知webhook地址
QY_NOTIFY_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a98cc573-9d3b-454b-84a5-9c281beffe24"

# 如果不是生产环境，则添加环境后缀
if [ "$APP_ENV" != "prod" ]; then
  PROJECT_NAME="${PROJECT_NAME}-${APP_ENV}"
fi
# 脚本的工作目录
WORK_DIR="/data/projects/$PROJECT_NAME"
SERVER_HOST=$(get_local_ip "192.168")
CONFIG_FILE="config-${APP_ENV}.yaml"
# 接口文档地址
OPENAPI_URL="http://${SERVER_HOST}:${SERVER_PORT}/docs"
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
    handle_error "无法获取本地IP"
fi

# 切换到工作目录
cd "$WORK_DIR" || handle_error "无法进入目录 $WORK_DIR"

# 设置远程 URL
git remote set-url origin "$REPO_URL"
# 捕获退出信号，在脚本结束时重置远程 URL
trap 'git remote set-url origin "$ORIGINAL_REPO_URL"' EXIT

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$DEPLOY_BRANCH" ]; then
    log "当前分支是 $CURRENT_BRANCH, 正在切换到 $DEPLOY_BRANCH"
    git checkout "$DEPLOY_BRANCH" || handle_error "切换分支失败"
fi

# 更新远程仓库信息
git fetch origin || handle_error "fetch 失败"

LOCAL_COMMIT=$(git rev-parse "$DEPLOY_BRANCH")
REMOTE_COMMIT=$(git rev-parse "origin/$DEPLOY_BRANCH")

# 添加强制部署逻辑
if [ "$FORCE_DEPLOY" -eq 1 ] || [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    if [ "$FORCE_DEPLOY" -eq 1 ]; then
        log "执行强制部署"
        # 强制更新代码
        git reset --hard "origin/$DEPLOY_BRANCH" || handle_error "强制重置分支失败"
        log "当前代码版本：$(git rev-parse --short HEAD)"
    else
        log "检测到代码更新，开始持续部署流程..."
        # 拉取最新更新
        git pull origin "$DEPLOY_BRANCH" || handle_error "pull 失败"
        log "此次更新的 commit 列表:"
        git log --oneline "$LOCAL_COMMIT..$REMOTE_COMMIT"
    fi

    # 验证配置文件存在
    [[ ! -f "$CONFIG_FILE" ]] && {
        log "创建默认配置文件..."
        touch "$CONFIG_FILE"
    }

    DEPLOY_COMMIT_SHORT=$(git rev-parse --short HEAD)
    DOCKER_IMAGE="${PROJECT_NAME}:${DEPLOY_COMMIT_SHORT}-$(date +%Y%m%d%H%M)"

    # 构建Docker镜像
    log "开始构建容器镜像..."
    DOCKER_BUILDKIT=1 docker build -t "$DOCKER_IMAGE" . || {
        log "镜像构建失败"
        send_notification "容器镜像构建失败！\n请检查构建日志"
        exit 1
    }

    # 清理旧容器
    docker rm -f "$PROJECT_NAME" 2>/dev/null && log "旧容器已移除"

    # 启动容器前检查端口占用
    if check_port_used "${SERVER_PORT}"; then
        handle_error "宿主机端口 ${SERVER_PORT} 已被占用"
    fi

    # 启动新容器
    log "启动新版本容器..."
    docker run -d \
        --name "$PROJECT_NAME" \
        --restart unless-stopped \
        -p "${SERVER_PORT}:${SERVER_PORT}" \
        -e APP_ENV="$APP_ENV" \
        -e SERVER_HOST="${SERVER_HOST:-0.0.0.0}" \
        -e SERVER_PORT="${SERVER_PORT}" \
        -v "$(pwd)/$CONFIG_FILE:/app/$CONFIG_FILE" \
        -v "$(pwd)/log:/app/log" \
        "$DOCKER_IMAGE" || {
            log "容器启动失败"
            send_notification "容器启动失败！\n请检查运行时配置"
            exit 1
        }

    # 等待应用启动
    log "等待应用启动"
    MAX_RETRIES=15
    SLEEP_INTERVAL=3
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s "http://${SERVER_HOST}:${SERVER_PORT}/health" >/dev/null 2>&1; then
            HEALTH_CHECK="✅ 通过"
            break
        else
            echo "第 $i 次检查失败，等待 $SLEEP_INTERVAL 秒..."
        fi
        sleep $SLEEP_INTERVAL
    done
    [[ -z "$HEALTH_CHECK" ]] && HEALTH_CHECK="⚠️ 失败(接口可能尚未就绪)"

    # 生成变更报告
    DEPLOY_MODE="自动触发"
    CHANGELOG_CONTENT=""
    if [ "$FORCE_DEPLOY" -eq 1 ]; then
        DEPLOY_MODE="手动强制部署"
        CHANGELOG_CONTENT="📝 **最新版本信息**:\n"
        LATEST_COMMIT=$(git log -3 --pretty=format:"%h %an - %s")
        CHANGELOG_CONTENT+="> ${LATEST_COMMIT}\n\n"
    else
        CHANGELOG_CONTENT="📝 **变更内容**:\n"
        COMMIT_LIST=$(git log --pretty=format:"%h %an - %s" --no-merges "${LOCAL_COMMIT}..${REMOTE_COMMIT}")
        while IFS= read -r commit; do
            CHANGELOG_CONTENT+="> ${commit}\n"
        done <<< "$COMMIT_LIST"
        CHANGELOG_CONTENT+="\n"
    fi
    NOTIFICATION_CONTENT=""
    COMMIT_LIST=$(git log --pretty=format:"%h %an - %s" --no-merges "${LOCAL_COMMIT}..${REMOTE_COMMIT}")
    NOTIFICATION_CONTENT+="✅ **自动化部署成功**\n"
    NOTIFICATION_CONTENT+="**项目名称**: ${PROJECT_NAME}\n"
    NOTIFICATION_CONTENT+="**代码分支**: ${DEPLOY_BRANCH}\n"
    NOTIFICATION_CONTENT+="**部署环境**: ${APP_ENV}\n"
    NOTIFICATION_CONTENT+="**部署方式**: ${DEPLOY_MODE}\n"
    NOTIFICATION_CONTENT+="**容器镜像**: ${DOCKER_IMAGE}\n"
    NOTIFICATION_CONTENT+="**部署节点**: ${SERVER_HOST}\n"
    NOTIFICATION_CONTENT+="**部署端口**: ${SERVER_PORT}\n"
    NOTIFICATION_CONTENT+="**健康检查**: ${HEALTH_CHECK}\n"
    NOTIFICATION_CONTENT+="**部署时间**: $(date +'%Y-%m-%d %H:%M:%S')\n\n"
    
    NOTIFICATION_CONTENT+="${CHANGELOG_CONTENT}"

    NOTIFICATION_CONTENT+="🔗 **相关链接**:\n"
    NOTIFICATION_CONTENT+="- [接口文档](${OPENAPI_URL})\n"
    NOTIFICATION_CONTENT+="\n"

    # 发送企业微信通知
    send_notification "$NOTIFICATION_CONTENT"
    log "部署流程完成"
else
    log "当前已是最新版本，无需部署"
fi