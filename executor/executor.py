import requests
import time
import subprocess
import os
import sys
import json

# 配置平台地址 (根据实际情况修改)
PLATFORM_URL = os.getenv("PLATFORM_URL", "http://localhost:8000")
API_BASE = f"{PLATFORM_URL}/api/android"


def run_midscene_runner(task):
    """
    调用 Node.js 脚本执行 Midscene
    """
    task_id = task["id"]
    script_content = task["script"]
    api_key = task["llm_config"]["api_key"]

    print(f"[*] Task #{task_id}: Preparing environment...")

    # 1. 写入临时脚本文件
    script_file = f"task_{task_id}_script.json"
    # Midscene runner 需要知道要把报告生成在哪
    report_file = f"task_{task_id}_report.html"

    # 尝试解析 JSON，如果不是 JSON 则封装为列表
    try:
        json_content = json.loads(script_content)
    except:
        json_content = [line.strip() for line in script_content.split('\n') if line.strip()]

    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(json_content, f, ensure_ascii=False)

    # 2. 设置环境变量
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    # 如果 Midscene 支持自定义报告路径，可以通过 env 传进去，或者在 args 里传
    env["MIDSCENE_REPORT_FILE"] = report_file

    cmd = ["npx", "tsx", "runner.ts", script_file, report_file]

    print(f"[*] Task #{task_id}: Running Midscene...")
    try:
        # 执行命令
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))  # 确保在当前目录执行
        )

        # 实时等待结束
        stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
        return_code = process.returncode

    except subprocess.TimeoutExpired:
        process.kill()
        return -1, "", "Execution Timeout"
    except Exception as e:
        return -1, "", str(e)
    finally:
        # 清理临时脚本
        if os.path.exists(script_file):
            os.remove(script_file)

    return return_code, stdout, stderr, report_file


def main():
    print(f"🚀 Android Executor started. Target: {PLATFORM_URL}")
    print("Waiting for tasks...")

    while True:
        try:
            # 1. 轮询领取任务
            try:
                resp = requests.get(f"{API_BASE}/tasks/pop", timeout=10)
            except requests.exceptions.ConnectionError:
                print(f"[!] Cannot connect to platform. Retrying in 5s...")
                time.sleep(5)
                continue

            if resp.status_code != 200:
                print(f"[!] Server error: {resp.text}")
                time.sleep(5)
                continue

            task = resp.json()
            if not task:
                time.sleep(2)  # 无任务，休息一下
                continue

            print(f"\n[+] Received Task #{task['id']}")

            # 2. 执行任务
            code, out, err, report_path = run_midscene_runner(task)

            # 3. 读取 HTML 报告
            html_content = ""
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                os.remove(report_path)  # 读取后删除本地文件
            else:
                err += "\n[System] Report file not found."

            # 4. 上报结果
            status = "success" if code == 0 else "failed"
            payload = {
                "status": status,
                "logs": f"STDOUT:\n{out}\n\nSTDERR:\n{err}",
                "html_report": html_content
            }

            print(f"[*] Uploading report for Task #{task['id']} ({status})...")
            requests.post(f"{API_BASE}/tasks/{task['id']}/report", json=payload)
            print("[*] Done.")

        except Exception as e:
            print(f"[!] Unexpected Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()