#!/bin/bash
# * * * * * /bin/bash /data/projects/fastapi-base/auto_deploy.sh >> /data/projects/fastapi-base/deploy.log 2>&1

# 远程仓库地址
ORIGINAL_REPO_URL="http://192.168.30.28/framework/fastapi-base.git"
GIT_USER="cqvipcq%40outlook.com"
GIT_PASSWD="Cqvip.com"
# 用于部署的分支名
RELEASE_BRANCH="release/1.0.0"
# 服务名
SERVICE_NAME="fastapi-base"
# 脚本的工作目录
WORK_DIR="/data/projects/$SERVICE_NAME"
# 企微群机器人通知webhook地址
QY_NOTIFY_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=013547da-3d78-4a7f-b4a7-e668b192c293"
PIP_PATH="/opt/anaconda3/envs/${SERVICE_NAME}/bin/pip"
SUPERVISORCTL_PATH="/opt/anaconda3/envs/${SERVICE_NAME}/bin/supervisorctl"
OPENAPI_URL="http://192.168.98.79:8150/docs"

# 远程仓库地址（带用户名和密码）
REPO_URL="http://${GIT_USER}:${GIT_PASSWD}@${ORIGINAL_REPO_URL#http://}"

set -e  # 一旦发生错误，脚本将退出

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
                "content": "'"${content}"'"
            }
        }' || log "发送通知失败"
}

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
    log "检测到更新，正在拉取..."

    # 拉取最新更新
    git pull origin "$RELEASE_BRANCH" || { log "pull 失败"; exit 1; }

    log "此次更新的 commit 列表:"
    git log --oneline "$LOCAL_COMMIT..$REMOTE_COMMIT"

    # 安装依赖包
    log "正在安装依赖包..."
    $PIP_PATH install -r requirements.txt || { log "依赖包安装失败"; exit 1; }
    log "依赖包安装完成"

    # 重新加载supervisor配置文件，并根据新的配置启动、停止或重启进程
    $SUPERVISORCTL_PATH reread
    $SUPERVISORCTL_PATH update

    # 重启所有进程
    $SUPERVISORCTL_PATH restart all || { log "进程重启失败"; exit 1; }
    log "进程已重启"
    $SUPERVISORCTL_PATH status all

    # 构建通知内容
    COMMIT_LIST=$(git log --oneline --no-merges "$LOCAL_COMMIT..$REMOTE_COMMIT")
    NOTIFICATION_CONTENT="应用部署更新成功，以下是最近的 commit 列表：\n"

    # 添加 commit 列表到通知内容
    while read -r commit; do
        NOTIFICATION_CONTENT+="> $commit\n"
    done <<< "$COMMIT_LIST"

    # 添加接口文档链接
    NOTIFICATION_CONTENT+="\n接口文档地址：[服务接口文档](${OPENAPI_URL})"

    # 发送企业微信通知
    send_notification "$NOTIFICATION_CONTENT"
else
    log "没有检测到更新"
fi
