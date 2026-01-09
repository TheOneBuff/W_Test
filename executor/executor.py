import requests
import time
import subprocess
import os
import json

PLATFORM_URL = "http://your-platform-ip:8000"


def run_midscene(task):
    """
    1. 设置环境变量 (API Key)
    2. 将脚本内容传递给 TS (通过环境变量或临时文件)
    3. 执行 npx tsx runner.ts
    """

    # 1. 准备环境
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = task["llm_config"]["api_key"]

    # 注入环境参数 (如果有的话)
    for k, v in task.get("env_vars", {}).items():
        env[k] = str(v)

    # 2. 将脚本写入临时文件 (供 runner.ts 读取)
    # 假设 script 是一个 JSON 数组字符串: '["点击设置", "点击显示"]'
    with open("temp_script.json", "w", encoding="utf-8") as f:
        f.write(task["script"])

    print(f"[*] Starting Midscene execution for Task #{task['id']}...")

    # 3. 执行 TS
    try:
        # 确保安装了依赖: npm install @midscene/android tsx
        process = subprocess.Popen(
            ["npx", "tsx", "runner.ts"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        return process.returncode, stdout, stderr
    except Exception as e:
        return 1, "", str(e)


def main():
    print(f"🚀 Android Executor started. Connecting to {PLATFORM_URL}...")

    while True:
        try:
            # 1. 轮询
            resp = requests.get(f"{PLATFORM_URL}/api/android/tasks/pop")
            if resp.status_code == 200 and resp.json():
                task = resp.json()
                print(f"\n[+] Received Task #{task['id']}")

                # 2. 执行
                code, out, err = run_midscene(task)

                # 3. 读取报告文件 (Midscene 生成的)
                html_content = ""
                # 假设 runner.ts 配置生成在 ./midscene_run/report/report.html
                report_path = "./midscene_run/report/report.html"
                if os.path.exists(report_path):
                    with open(report_path, "r", encoding="utf-8") as f:
                        html_content = f.read()

                # 4. 上报
                requests.post(f"{PLATFORM_URL}/api/android/tasks/{task['id']}/report", json={
                    "status": "success" if code == 0 else "failed",
                    "logs": f"STDOUT:\n{out}\n\nSTDERR:\n{err}",
                    "html_report": html_content
                })
                print(f"[*] Task #{task['id']} reported.")

            else:
                time.sleep(3)  # 空闲等待

        except Exception as e:
            print(f"[!] Connection Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
