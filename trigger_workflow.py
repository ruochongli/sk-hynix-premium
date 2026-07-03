"""
本地定时触发 GitHub Actions workflow。
因为 GitHub Actions 的 schedule 在该仓库始终不触发，
所以用这个脚本每隔 5 分钟调用一次 workflow_dispatch。

用法：
    set GITHUB_TOKEN=ghp_xxx
    python trigger_workflow.py

或者把 GITHUB_TOKEN 写进同目录 .env 文件：
    GITHUB_TOKEN=ghp_xxx
"""
import os
import time
import requests
from pathlib import Path

REPO = "ruochongli/sk-hynix-premium"
WORKFLOW_ID = "update-data.yml"
INTERVAL = 300  # 5 分钟


def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        env_file = Path(__file__).with_suffix(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    if not token:
        raise RuntimeError("请设置 GITHUB_TOKEN 环境变量或写入 trigger_workflow.env")
    return token


def trigger(token):
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.post(url, json={"ref": "main"}, headers=headers, timeout=30)
    if r.status_code == 204:
        print(f"[{time.strftime('%H:%M:%S')}] 已触发 workflow_dispatch")
        return True
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 触发失败: {r.status_code} {r.text[:200]}")
        return False


def main():
    token = get_token()
    print("启动本地触发器，每 5 分钟触发一次 GitHub Actions...")
    # 启动时立即触发一次
    trigger(token)
    while True:
        time.sleep(INTERVAL)
        trigger(token)


if __name__ == "__main__":
    main()
