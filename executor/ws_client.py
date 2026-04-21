import json
import threading
import time
import uuid
import websocket

class WSClient:
    def __init__(self, server_url: str, executor_uuid: str, on_task_received=None, on_disconnect=None):
        self.server_url = server_url
        self.executor_uuid = executor_uuid
        self.on_task_received = on_task_received
        self.on_disconnect = on_disconnect
        
        self.ws = None
        self.connected = False
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 0
        self._running = False
        self._thread = None
        
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self.ws:
            self.ws.close()
        if self._thread:
            self._thread.join(timeout=3)
            
    def _run_loop(self):
        while self._running:
            try:
                self._connect()
            except Exception as e:
                print(f"[WS] 连接错误: {e}")
                time.sleep(self.reconnect_interval)
                
    def _connect(self):
        print(f"[WS] 正在连接服务器: {self.server_url}")
        
        self.ws = websocket.WebSocketApp(
            self.server_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.ws.run_forever(ping_interval=20, ping_timeout=10)
        
    def _on_open(self, ws):
        print("[WS] 连接已建立")
        self.connected = True
        self._send_register()
        self._send_heartbeat()
        
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'heartbeat_ack':
                print("[WS] 心跳响应收到")
                
            elif msg_type == 'task':
                task = data.get('task')
                if task and self.on_task_received:
                    self.on_task_received(task)
                    
            elif msg_type == 'cancel':
                task_id = data.get('task_id')
                print(f"[WS] 收到取消任务指令: {task_id}")
                
            elif msg_type == 'ping':
                self.ws.send(json.dumps({'type': 'pong'}))
                
        except json.JSONDecodeError:
            print(f"[WS] 收到无效 JSON: {message}")
            
    def _on_error(self, ws, error):
        print(f"[WS] 错误: {error}")
        self.connected = False
        
    def _on_close(self, ws, close_status_code, close_msg):
        print(f"[WS] 连接关闭: {close_status_code} - {close_msg}")
        self.connected = False
        if self._running and self.on_disconnect:
            self.on_disconnect()
            
    def _send_register(self):
        if self.ws and self.connected:
            msg = {
                'type': 'register',
                'uuid': self.executor_uuid
            }
            self.ws.send(json.dumps(msg))
            print("[WS] 已发送注册消息")
            
    def _send_heartbeat(self):
        if self.ws and self.connected:
            msg = {
                'type': 'heartbeat',
                'uuid': self.executor_uuid
            }
            self.ws.send(json.dumps(msg))
            
    def send_status(self, report_id: int, status: str, logs: str = ''):
        if self.ws and self.connected:
            msg = {
                'type': 'status',
                'report_id': report_id,
                'status': status,
                'logs': logs
            }
            self.ws.send(json.dumps(msg))
            
    def send_log(self, report_id: int, content: str):
        if self.ws and self.connected:
            msg = {
                'type': 'log',
                'report_id': report_id,
                'content': content
            }
            self.ws.send(json.dumps(msg))
            
    def send_report(self, report_id: int, status: str, logs: str = '', report_html: str = '', error_info: str = '', prereq_check: dict = None):
        if self.ws and self.connected:
            msg = {
                'type': 'report',
                'report_id': report_id,
                'status': status,
                'logs': logs,
                'report_html': report_html,
                'error_info': error_info,
                'prereq_check': prereq_check
            }
            self.ws.send(json.dumps(msg))


def heartbeat_thread(ws_client: WSClient, interval: int = 30):
    while ws_client._running:
        if ws_client.connected:
            ws_client._send_heartbeat()
        time.sleep(interval)


def start_heartbeat(ws_client: WSClient, interval: int = 30):
    t = threading.Thread(target=heartbeat_thread, args=(ws_client, interval), daemon=True)
    t.start()
    return t
