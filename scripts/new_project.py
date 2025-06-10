import os.path
from pathlib import Path
import shutil
import subprocess

BASE_PROJECT_NAME = "fastapi-base"


def copy_git_files(src_dir, dest_dir):
    """复制已添加到 Git 的文件到新目录"""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # 获取 Git 已跟踪的文件列表
    result = subprocess.run(["git", "-C", src_dir, "ls-files"], capture_output=True, text=True)
    git_files = result.stdout.splitlines()

    for file in git_files:
        src_file = os.path.join(src_dir, file)
        dest_file = os.path.join(dest_dir, file)
        dest_file_dir = os.path.dirname(dest_file)
        if not os.path.exists(dest_file_dir):
            os.makedirs(dest_file_dir)
        shutil.copy2(src_file, dest_file)
        print(f"复制文件: {file}")


def replace_project_name(dest_dir, old_name, new_name):
    """全局替换项目名"""
    for root, _, files in os.walk(dest_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file: str
            if file.endswith((".py", ".md", ".yaml", ".yml", ".sh", ".conf", ".json", ".txt")):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = content.replace(old_name, new_name)
                if new_content != content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"替换项目名: {file_path}")


def init_git_repo(dest_dir, remote_url=None):
    """初始化新的 Git 仓库并提交"""
    subprocess.run(["git", "-C", dest_dir, "init"])
    subprocess.run(["git", "-C", dest_dir, "add", "."])
    subprocess.run(["git", "-C", dest_dir, "commit", "-m", "Initial commit"])

    if remote_url:
        # 关联远程仓库
        subprocess.run(["git", "-C", dest_dir, "remote", "add", "origin", remote_url])
        # 推送到远程仓库
        subprocess.run(["git", "-C", dest_dir, "push", "-u", "origin", "master"])


def main():
    new_project_name = "foreign-fulltext"  # 新项目名
    src_dir = Path(__file__).parent.parent  # 当前项目路径
    dest_dir = src_dir.parent / new_project_name  # 新项目路径
    src_dir = str(src_dir)
    dest_dir = str(dest_dir)

    print("开始复制项目文件...")
    copy_git_files(src_dir, dest_dir)

    print("开始全局替换项目名...")
    replace_project_name(dest_dir, BASE_PROJECT_NAME, new_project_name)

    print("初始化新的 Git 仓库...")
    init_git_repo(dest_dir, remote_url="http://192.168.30.28/datacenter-datawarehouse/foreign-fulltext.git")

    print("新项目创建完成！")


if __name__ == "__main__":
    main()
