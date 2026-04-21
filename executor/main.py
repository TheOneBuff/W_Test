import os
import sys
import json
import uuid
import platform
import socket
import time
import threading
import requests
from datetime import datetime

from prereq_check import check_prerequisites_for_pc, check_prerequisites_for_android
from ws_client import WSClient, start_heartbeat
from executor_engine import ExecutorEngine

VERSION = "1.0.0"


class PCExecutor:
    def __init__(self, server_url=None, script_dir=None):
        self.platform_url = server_url or "http://localhost:8000"
        self.ws_url = server_url.replace('http://', 'ws://').replace('https://', 'wss://') + "/api/pc/ws/executor"
        self.script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))
        self.executor_name = socket.gethostname()
        self.executor_type = "pc"
        self.running = False
        self.connected = False
        
        self.uuid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.executor_uuid')
        self.uuid = self._load_or_create_uuid()
        self.ws_client = None
        self.engine = ExecutorEngine(self.script_dir)
        self.current_task = None
        self._heartbeat_thread = None
        self._log_callback = None
        
    def _load_or_create_uuid(self) -> str:
        uuid_file = self.uuid_file
        if os.path.exists(uuid_file):
            with open(uuid_file, 'r') as f:
                return f.read().strip()
        
        new_uuid = str(uuid.uuid4())
        with open(uuid_file, 'w') as f:
            f.write(new_uuid)
        return new_uuid
        
    def _get_system_info(self) -> dict:
        return {
            'os_version': f"{platform.system()} {platform.release()}",
            'hostname': platform.node(),
            'ip_address': self._get_local_ip(),
            'executor_version': VERSION,
            'executor_type': self.executor_type,
            'script_types': ['typescript', 'yaml']
        }
        
    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'
            
    def set_log_callback(self, callback):
        self._log_callback = callback
        
    def log(self, message, level="info"):
        print(message)
        if self._log_callback:
            self._log_callback(message, level)
            
    def run_prereq_checks(self) -> dict:
        return check_prerequisites_for_pc()
        
    def register_to_server(self) -> bool:
        system_info = self._get_system_info()
        data = {
            'name': self.executor_name,
            'uuid': self.uuid,
            'capabilities': {'script_types': system_info['script_types']},
            'os_version': system_info['os_version'],
            'hostname': system_info['hostname'],
            'ip_address': system_info['ip_address'],
            'executor_version': system_info['executor_version']
        }
        
        try:
            resp = requests.post(f"{self.platform_url}/api/pc/executors/register", json=data, timeout=10)
            if resp.status_code == 200:
                return True
            return False
        except Exception as e:
            self.log(f"连接服务器失败: {e}", "error")
            return False
            
    def on_task_received(self, task: dict):
        self.log(f"[收到任务] Task #{task.get('id')}", "task")
        self.current_task = task
        self._execute_task(task)
        
    def on_disconnect(self):
        self.connected = False
        self.log("[连接断开] 正在尝试重连...", "warning")
        
    def on_connect(self):
        self.connected = True
        self.log("[已连接] WebSocket 连接成功", "success")
        
    def _execute_task(self, task: dict):
        report_id = task.get('id')
        script_content = task.get('script', '')
        script_type = task.get('script_type', 'typescript')
        llm_config = task.get('llm_config', {})
        
        self.log(f"[执行中] 开始执行任务 #{report_id}", "info")
        
        env_vars = {}
        if llm_config.get('api_key'):
            env_vars['OPENAI_API_KEY'] = llm_config['api_key']
        if llm_config.get('base_url'):
            env_vars['OPENAI_BASE_URL'] = llm_config['base_url']
            
        return_code, stdout, stderr = self.engine.execute(
            script_content,
            script_type,
            report_id,
            env_vars
        )
        
        logs = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        
        report_html = self.engine.read_report(report_id)
        status = 'success' if return_code == 0 else 'failed'
        
        if self.ws_client and self.connected:
            self.ws_client.send_report(
                report_id=report_id,
                status=status,
                logs=logs,
                report_html=report_html
            )
            
        self._upload_report(report_id, status, logs, report_html)
        
        self.log(f"[任务完成] Task #{report_id} - 状态: {status}", "success" if status == "success" else "error")
        self.current_task = None
        
    def _upload_report(self, report_id: int, status: str, logs: str, report_html: str):
        try:
            data = {
                'report_id': report_id,
                'status': status,
                'logs': logs,
                'report_path': report_html
            }
            resp = requests.post(f"{self.platform_url}/api/pc/reports/upload", json=data, timeout=30)
            if resp.status_code == 200:
                self.log(f"[上报成功] 报告 #{report_id} 已上传", "success")
        except Exception as e:
            self.log(f"[上报异常] {e}", "error")
            
    def start(self):
        self.running = True
        
        prereq_result = self.run_prereq_checks()
        self.log("=" * 50, "info")
        self.log("PC 桌面自动化执行器 v" + VERSION, "info")
        self.log("=" * 50, "info")
        
        for name, check in prereq_result['checks'].items():
            status = '✅' if check['passed'] else '❌'
            self.log(f"  {status} {name}: {check.get('version', check.get('message', ''))}", "info")
            
        if not self.register_to_server():
            self.log("[错误] 无法连接到服务器", "error")
            return False
            
        self.log("✅ 注册成功! UUID: " + self.uuid, "success")
        
        self.ws_client = WSClient(
            server_url=self.ws_url,
            executor_uuid=self.uuid,
            on_task_received=self.on_task_received,
            on_disconnect=self.on_disconnect
        )
        
        self.ws_client.start()
        self._heartbeat_thread = start_heartbeat(self.ws_client, 30)
        self.connected = True
        self.on_connect()
        
        self.log("=" * 50, "info")
        return True
        
    def stop(self):
        self.running = False
        if self.ws_client:
            self.ws_client.stop()
        self.connected = False
        self.log("[已停止] 执行器已停止", "info")
        
    def update_config(self, server_url=None, script_dir=None):
        if server_url:
            self.platform_url = server_url
            self.ws_url = server_url.replace('http://', 'ws://').replace('https://', 'wss://') + "/api/pc/ws/executor"
        if script_dir:
            self.script_dir = script_dir
            self.engine = ExecutorEngine(self.script_dir)


class AndroidExecutor:
    def __init__(self, server_url=None):
        self.platform_url = server_url or "http://localhost:8000"
        self.api_base = f"{self.platform_url}/api/android"
        self.executor_name = socket.gethostname()
        self.executor_type = "android"
        self.running = False
        self._log_callback = None
        
    def set_log_callback(self, callback):
        self._log_callback = callback
        
    def log(self, message, level="info"):
        print(message)
        if self._log_callback:
            self._log_callback(message, level)
            
    def run_prereq_checks(self) -> dict:
        return check_prerequisites_for_android()
        
    def start(self):
        import subprocess
        self.running = True
        
        prereq_result = self.run_prereq_checks()
        self.log("=" * 50, "info")
        self.log("Android 自动化执行器 v" + VERSION, "info")
        self.log("=" * 50, "info")
        
        for name, check in prereq_result['checks'].items():
            status = '✅' if check['passed'] else '❌'
            self.log(f"  {status} {name}: {check.get('version', check.get('message', ''))}", "info")
            
        self.log(f"🚀 Android Executor started. Target: {self.platform_url}", "info")
        self.log("=" * 50, "info")
        
    def stop(self):
        self.running = False
        
    def update_config(self, server_url=None):
        if server_url:
            self.platform_url = server_url
            self.api_base = f"{self.platform_url}/api/android"


def show_config_dialog():
    """显示初始配置对话框"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.title("自动化执行器配置")
        root.geometry("500x380")
        root.resizable(False, False)
        
        executor_type_var = tk.StringVar(value="pc")
        server_url_var = tk.StringVar(value="http://localhost:8000")
        script_dir_var = tk.StringVar(value=os.path.dirname(os.path.abspath(__file__)))
        
        def browse_script_dir():
            folder = filedialog.askdirectory(title="选择脚本存放目录", initialdir=script_dir_var.get())
            if folder:
                script_dir_var.set(folder)
        
        def on_type_change(*args):
            if executor_type_var.get() == "android":
                script_dir_label.config(state=tk.DISABLED)
                script_dir_entry.config(state=tk.DISABLED)
                browse_btn.config(state=tk.DISABLED)
            else:
                script_dir_label.config(state=tk.NORMAL)
                script_dir_entry.config(state=tk.NORMAL)
                browse_btn.config(state=tk.NORMAL)
        
        executor_type_var.trace('w', on_type_change)
        
        tk.Label(root, text="执行模式:", font=('Arial', 11)).place(x=30, y=30)
        tk.Radiobutton(root, text="PC 桌面自动化", variable=executor_type_var, value="pc", 
                      font=('Arial', 10)).place(x=130, y=30)
        tk.Radiobutton(root, text="Android 自动化", variable=executor_type_var, value="android",
                      font=('Arial', 10)).place(x=280, y=30)
        
        tk.Label(root, text="服务器地址:", font=('Arial', 11)).place(x=30, y=80)
        tk.Entry(root, textvariable=server_url_var, width=50).place(x=130, y=80, height=28)
        tk.Label(root, text="(不填则使用默认地址)", font=('Arial', 9), fg='gray').place(x=130, y=110)
        
        script_dir_label = tk.Label(root, text="脚本存放目录:", font=('Arial', 11))
        script_dir_label.place(x=30, y=145)
        script_dir_entry = tk.Entry(root, textvariable=script_dir_var, width=40)
        script_dir_entry.place(x=130, y=145, height=28)
        browse_btn = tk.Button(root, text="浏览...", command=browse_script_dir)
        browse_btn.place(x=420, y=145, height=28)
        tk.Label(root, text="(脚本文件将保存在此目录)", font=('Arial', 9), fg='gray').place(x=130, y=175)
        
        info_frame = tk.Frame(root, bd=1, relief=tk.SOLID, bg='#f0f0f0')
        info_frame.place(x=30, y=205, width=440, height=100)
        
        tk.Label(info_frame, text="PC 桌面自动化:", font=('Arial', 9, 'bold'), bg='#f0f0f0').place(x=10, y=8)
        tk.Label(info_frame, text="• 支持 TypeScript/YAML 脚本", font=('Arial', 9), bg='#f0f0f0').place(x=10, y=30)
        tk.Label(info_frame, text="• 需要 Playwright + Midscene 环境", font=('Arial', 9), bg='#f0f0f0').place(x=10, y=48)
        
        tk.Label(info_frame, text="Android 自动化:", font=('Arial', 9, 'bold'), bg='#f0f0f0').place(x=230, y=8)
        tk.Label(info_frame, text="• 支持 Midscene Android", font=('Arial', 9), bg='#f0f0f0').place(x=230, y=30)
        tk.Label(info_frame, text="• 需要 ADB 连接手机", font=('Arial', 9), bg='#f0f0f0').place(x=230, y=48)
        
        def on_confirm():
            url = server_url_var.get().strip()
            if url:
                if not url.startswith('http'):
                    url = 'http://' + url
                if ':' not in url.split('//')[1] if '//' in url else ':' not in url:
                    url = url.rstrip('/') + ':8000'
            else:
                url = "http://localhost:8000"
            root.executor_type = executor_type_var.get()
            root.server_url = url
            root.script_dir = script_dir_var.get().strip() or os.path.dirname(os.path.abspath(__file__))
            root.destroy()
            
        def on_cancel():
            root.executor_type = None
            root.server_url = None
            root.script_dir = None
            root.destroy()
            sys.exit(0)
            
        frame = tk.Frame(root)
        frame.place(x=130, y=320)
        tk.Button(frame, text="确定", command=on_confirm, width=12, bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="取消", command=on_cancel, width=12, font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        root.protocol("WM_DELETE_WINDOW", on_cancel)
        root.center_x = (root.winfo_screenwidth() - 500) // 2
        root.center_y = (root.winfo_screenheight() - 380) // 2
        root.geometry(f"+{root.center_x}+{root.center_y}")
        
        root.mainloop()
        
        return getattr(root, 'executor_type', None), getattr(root, 'server_url', None), getattr(root, 'script_dir', None)
        
    except ImportError:
        return "pc", "http://localhost:8000", os.path.dirname(os.path.abspath(__file__))


def show_gui_manager(executor):
    """显示 GUI 管理界面"""
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        import threading
        
        root = tk.Tk()
        root.title(f"自动化执行器 - {executor.executor_type.upper()}")
        root.geometry("700x550")
        root.minsize(600, 450)
        
        executor._log_callback = None
        logs = []
        log_lock = threading.Lock()
        
        def add_log(message, level="info"):
            nonlocal logs
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {message}"
            with log_lock:
                logs.append((log_line, level))
                if len(logs) > 500:
                    logs = logs[-500:]
                text_area.insert(tk.END, log_line + "\n", level)
                text_area.see(tk.END)
                
        executor._log_callback = add_log
        
        status_bar = tk.Frame(root, bg='#2c3e50', height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = tk.Label(status_bar, text="状态: 未连接", bg='#2c3e50', fg='white', anchor=tk.W)
        status_label.pack(side=tk.LEFT, padx=10)
        
        uuid_label = tk.Label(status_bar, text=f"UUID: {executor.uuid[:8]}...", bg='#2c3e50', fg='#95a5a6', anchor=tk.W)
        uuid_label.pack(side=tk.LEFT, padx=20)
        
        server_label = tk.Label(status_bar, text=f"服务器: {executor.platform_url}", bg='#2c3e50', fg='#95a5a6', anchor=tk.W)
        server_label.pack(side=tk.RIGHT, padx=10)
        
        top_frame = tk.Frame(root, bg='#34495e', padx=10, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(top_frame, text="服务器地址:", bg='#34495e', fg='white', font=('Arial', 10)).pack(side=tk.LEFT)
        server_entry = tk.Entry(top_frame, width=35, font=('Arial', 10))
        server_entry.insert(0, executor.platform_url)
        server_entry.pack(side=tk.LEFT, padx=5)
        
        if executor.executor_type == "pc":
            tk.Label(top_frame, text="脚本目录:", bg='#34495e', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=(20, 0))
            script_entry = tk.Entry(top_frame, width=25, font=('Arial', 10))
            script_entry.insert(0, executor.script_dir)
            script_entry.pack(side=tk.LEFT, padx=5)
        
        btn_frame = tk.Frame(top_frame, bg='#34495e')
        btn_frame.pack(side=tk.RIGHT)
        
        running = False
        
        def update_status():
            nonlocal running
            if running:
                status_label.config(text="状态: 运行中", bg='#27ae60')
            else:
                status_label.config(text="状态: 已停止", bg='#e74c3c')
                
        def on_start():
            nonlocal running
            if running:
                return
            executor.platform_url = server_entry.get().strip()
            if not executor.platform_url.startswith('http'):
                executor.platform_url = 'http://' + executor.platform_url
            if executor.executor_type == "pc":
                executor.script_dir = script_entry.get().strip()
                executor.update_config(executor.platform_url, executor.script_dir)
            else:
                executor.update_config(executor.platform_url)
                
            server_label.config(text=f"服务器: {executor.platform_url}")
            
            def run():
                nonlocal running
                running = True
                update_status()
                executor.start()
                running = False
                update_status()
                
            threading.Thread(target=run, daemon=True).start()
            
        def on_stop():
            nonlocal running
            if not running:
                return
            executor.stop()
            running = False
            update_status()
            
        start_btn = tk.Button(btn_frame, text="启动", command=on_start, bg='#27ae60', fg='white', 
                            font=('Arial', 10, 'bold'), width=8)
        start_btn.pack(side=tk.LEFT, padx=2)
        
        stop_btn = tk.Button(btn_frame, text="停止", command=on_stop, bg='#e74c3c', fg='white',
                          font=('Arial', 10, 'bold'), width=8, state=tk.DISABLED)
        stop_btn.pack(side=tk.LEFT, padx=2)
        
        def on_config_change(*args):
            if running:
                return
            new_url = server_entry.get().strip()
            if new_url != executor.platform_url:
                server_label.config(text=f"服务器: {new_url}")
                
        server_entry.bind('<KeyRelease>', on_config_change)
        
        task_frame = tk.LabelFrame(root, text="当前任务", padx=10, pady=5, font=('Arial', 10, 'bold'))
        task_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))
        
        task_label = tk.Label(task_frame, text="无执行中的任务", font=('Arial', 10), anchor=tk.W)
        task_label.pack(side=tk.LEFT)
        
        log_frame = tk.LabelFrame(root, text="执行日志", padx=5, pady=5, font=('Arial', 10, 'bold'))
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_area = tk.Text(log_frame, wrap=tk.WORD, font=('Consolas', 10), bg='#1e1e1e', fg='#d4d4d4')
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_frame, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.config(yscrollcommand=scrollbar.set)
        
        text_area.tag_config('info', foreground='#d4d4d4')
        text_area.tag_config('success', foreground='#4ec9b0')
        text_area.tag_config('error', foreground='#f48771')
        text_area.tag_config('warning', foreground='#ce9178')
        text_area.tag_config('task', foreground='#569cd6')
        
        def clear_logs():
            nonlocal logs
            logs = []
            text_area.delete('1.0', tk.END)
            
        def save_logs():
            filename = f"executor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for log, _ in logs:
                    f.write(log + '\n')
            messagebox.showinfo("保存成功", f"日志已保存到: {filename}")
            
        log_btn_frame = tk.Frame(log_frame)
        log_btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(log_btn_frame, text="清空日志", command=clear_logs, font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(log_btn_frame, text="保存日志", command=save_logs, font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        add_log("=" * 50, "info")
        add_log(f"自动化执行器 v{VERSION} (GUI 模式)", "info")
        add_log(f"执行模式: {executor.executor_type.upper()}", "info")
        add_log("=" * 50, "info")
        add_log("请点击「启动」按钮开始执行", "info")
        
        def on_closing():
            if running:
                if messagebox.askokcancel("退出", "执行器正在运行，确定要退出吗？"):
                    executor.stop()
                    root.destroy()
            else:
                root.destroy()
                
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except ImportError:
        print("[错误] tkinter 未安装，无法显示 GUI")
        print("请运行: pip install tkinter 或使用 Python 自带 tkinter")
        sys.exit(1)


def parse_arguments():
    """解析命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动化执行器')
    parser.add_argument('--type', '-t', type=str, choices=['pc', 'android'], default=None,
                        help='执行模式: pc (桌面自动化) 或 android (移动端自动化)')
    parser.add_argument('--server', '-s', type=str, default=None,
                        help='服务器地址 (如: http://192.168.1.100:8000)')
    parser.add_argument('--script-dir', '-d', type=str, default=None,
                        help='脚本存放目录 (仅 PC 模式)')
    parser.add_argument('--no-gui', action='store_true',
                        help='使用命令行模式，不显示配置窗口和 GUI')
    parser.add_argument('--help-config', action='store_true',
                        help='显示配置帮助信息')
    
    args = parser.parse_args()
    
    if args.help_config:
        print("\n=== 自动化执行器配置帮助 ===")
        print("\n使用方式:")
        print("  1. 双击运行: 自动弹出配置窗口")
        print("  2. GUI 模式运行:")
        print("     python main.py --type pc")
        print("     python main.py -t android")
        print("\n执行模式:")
        print("  pc       - PC 桌面自动化 (需要 Playwright + Midscene)")
        print("  android  - Android 自动化 (需要 ADB + Midscene Android)")
        print("")
        sys.exit(0)
    
    return args


def main():
    args = parse_arguments()
    
    executor_type = args.type
    server_url = args.server
    script_dir = args.script_dir
    
    if not args.no_gui and executor_type is None:
        try:
            executor_type, server_url, script_dir = show_config_dialog()
        except Exception as e:
            print(f"[提示] 无法显示配置窗口: {e}")
            executor_type = "pc"
    
    executor_type = executor_type or "pc"
    
    if executor_type == "android":
        executor = AndroidExecutor(server_url=server_url)
    else:
        executor = PCExecutor(server_url=server_url, script_dir=script_dir)
    
    if args.no_gui:
        executor.start()
    else:
        show_gui_manager(executor)


if __name__ == "__main__":
    main()
