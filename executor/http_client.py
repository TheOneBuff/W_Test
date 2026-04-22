import json
import threading
import time
import requests

class HttpClient:
    def __init__(self, server_url: str, executor_uuid: str, on_task_received=None, on_disconnect=None):
        self.server_url = server_url.rstrip('/')
        self.executor_uuid = executor_uuid
        self.on_task_received = on_task_received
        self.on_disconnect = on_disconnect

        self.connected = False
        self._running = False
        self._thread = None
        self._poll_interval = 30
        self._registered = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _run_loop(self):
        print("[HTTP] _run_loop 线程启动")
        self._start_heartbeat()
        self._start_poll()

    def _get_url(self, path: str) -> str:
        return f"{self.server_url}{path}"

    def _start_heartbeat(self):
        print("[HTTP] 启动心跳线程，间隔 20 秒")

        def heartbeat_loop():
            hb_count = 0
            while self._running:
                hb_count += 1
                try:
                    url = self._get_url("/api/pc/executors/heartbeat")
                    resp = requests.post(url, params={'uuid': self.executor_uuid}, timeout=5)
                    print(f"[HTTP] 心跳#{hb_count}: {resp.status_code}")
                except Exception as e:
                    print(f"[HTTP] 心跳#{hb_count} 失败: {e}")
                time.sleep(20)
            print("[HTTP] 心跳线程结束")

        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()

    def _start_poll(self):
        print(f"[HTTP] 开始轮询任务，间隔 {self._poll_interval} 秒")

        def poll_loop():
            while self._running:
                try:
                    url = self._get_url(f"/api/pc/executors/{self.executor_uuid}/tasks/pending")
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        tasks = resp.json()
                        if tasks:
                            for task in tasks:
                                print(f"[HTTP] 收到任务: {task.get('id')}")
                                if self.on_task_received:
                                    self.on_task_received(task)
                except Exception as e:
                    print(f"[HTTP] 轮询失败: {e}")
                time.sleep(self._poll_interval)
            print("[HTTP] 轮询线程结束")

        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()

    def send_report(self, report_id: int, status: str, logs: str = '', report_html: str = '', error_info: str = '', prereq_check: dict = None):
        try:
            url = self._get_url("/api/pc/executors/report")
            data = {
                'report_id': report_id,
                'status': status,
                'logs': logs,
                'report_html': report_html,
                'error_info': error_info,
                'prereq_check': prereq_check
            }
            resp = requests.post(url, json=data, timeout=30)
            print(f"[HTTP] 报告发送: report_id={report_id}, status={resp.status_code}")
        except Exception as e:
            print(f"[HTTP] 报告发送失败: {e}")

    def send_status(self, report_id: int, status: str, logs: str = ''):
        try:
            url = self._get_url("/api/pc/executors/status")
            data = {
                'report_id': report_id,
                'status': status,
                'logs': logs
            }
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            print(f"[HTTP] 状态发送失败: {e}")

    def send_log(self, report_id: int, content: str):
        try:
            url = self._get_url("/api/pc/executors/log")
            data = {
                'report_id': report_id,
                'content': content
            }
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            print(f"[HTTP] 日志发送失败: {e}")
