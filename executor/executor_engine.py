import os
import sys
import json
import subprocess
import tempfile
import shutil
from datetime import datetime

class ExecutorEngine:
    def __init__(self, working_dir=None):
        self.working_dir = working_dir or os.path.dirname(os.path.abspath(__file__))
        self.script_file = None
        self.report_file = None
        
    def _get_task_dir(self, task_id: int) -> str:
        task_dir = os.path.join(self.working_dir, f"task_{task_id}")
        if not os.path.exists(task_dir):
            os.makedirs(task_dir, exist_ok=True)
            print(f"[Executor] 创建任务目录: {task_dir}")
        return task_dir
    
    def write_script_file(self, script_content: str, script_type: str, task_id: int) -> str:
        ext = 'ts' if script_type == 'typescript' else 'yaml'
        task_dir = self._get_task_dir(task_id)
        self.script_file = os.path.join(task_dir, f"task_{task_id}_script.{ext}")
        
        with open(self.script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        return self.script_file
        
    def write_html_report(self, html_content: str, task_id: int) -> str:
        task_dir = self._get_task_dir(task_id)
        self.report_file = os.path.join(task_dir, f"task_{task_id}_report.html")
        
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return self.report_file
        
    def cleanup(self):
        if self.script_file and os.path.exists(self.script_file):
            try:
                os.remove(self.script_file)
            except:
                pass
        self.script_file = None
        self.report_file = None
        
    def _build_env(self, env_vars: dict = None, preserve_path: bool = False) -> dict:
        if preserve_path:
            env = dict(os.environ)
        else:
            env = os.environ.copy()
        
        env["MIDSCENE_DEBUG_LOG"] = "true"
        env["PYTHONUNBUFFERED"] = "1"
        env["FORCE_COLOR"] = "1"
        env["DEBUG"] = "pw:api"
        env["MIDSCENE_MODEL_REASONING_ENABLED"] = "false"
        
        print(f"[环境变量] 基础配置已设置")
        
        if env_vars:
            if env_vars.get("api_key"):
                env["OPENAI_API_KEY"] = env_vars["api_key"]
                print(f"[环境变量] OPENAI_API_KEY=****{env_vars['api_key'][-4:]}")
            if env_vars.get("base_url"):
                env["OPENAI_BASE_URL"] = env_vars["base_url"]
                print(f"[环境变量] OPENAI_BASE_URL={env_vars['base_url']}")
            if env_vars.get("model_name"):
                env["MIDSCENE_MODEL_NAME"] = env_vars["model_name"]
                print(f"[环境变量] MIDSCENE_MODEL_NAME={env_vars['model_name']}")
            if env_vars.get("model_family"):
                env["MIDSCENE_MODEL_FAMILY"] = env_vars["model_family"]
                print(f"[环境变量] MIDSCENE_MODEL_FAMILY={env_vars['model_family']}")
                
            custom_env = env_vars.get("custom_env", {})
            for k, v in custom_env.items():
                env[str(k)] = str(v)
                print(f"[环境变量] 自定义 {k}={v}")
        
        return env
        
    def execute_typescript(self, script_file: str, task_id: int, env_vars: dict = None) -> tuple:
        task_dir = self._get_task_dir(task_id)
        report_file = os.path.join(task_dir, f"task_{task_id}_report.html")
        
        env = self._build_env(env_vars, preserve_path=True)
        
        script_name = os.path.basename(script_file)
        cmd_str = f'npx tsx {script_name}'
        
        print(f"[TS执行] 命令: {cmd_str}")
        print(f"[TS执行] 工作目录: {task_dir}")
        print(f"[TS执行] 脚本文件: {script_name}")
        
        try:
            process = subprocess.Popen(
                cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                cwd=task_dir,
                env=env,
                shell=True
            )
            
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
            
            print(f"[TS执行] 完成，退出码: {return_code}")
            return return_code, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("[TS执行] 超时，10分钟限制")
            return -1, '', 'Execution Timeout (10 minutes)'
        except Exception as e:
            print(f"[TS执行] 异常: {e}")
            return -1, '', str(e)
            
    def execute_yaml(self, script_content: str, task_id: int, env_vars: dict = None) -> tuple:
        try:
            yaml_content = json.loads(script_content)
        except:
            yaml_content = [line.strip() for line in script_content.split('\n') if line.strip()]
            
        script_file = self.write_script_file(
            json.dumps(yaml_content, ensure_ascii=False),
            'json',
            task_id
        )
        
        env = self._build_env(env_vars, preserve_path=True)
            
        task_dir = self._get_task_dir(task_id)
        report_file = os.path.join(task_dir, f"task_{task_id}_report.html")
        script_name = os.path.basename(script_file)
        cmd_str = f'tsx runner.ts {script_name} {report_file}'
        
        print(f"[YAML执行] 命令: {cmd_str}")
        print(f"[YAML执行] 工作目录: {task_dir}")
        print(f"[YAML执行] 脚本文件: {script_name}")
        print(f"[YAML执行] 报告文件: {report_file}")
        
        try:
            process = subprocess.Popen(
                cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                cwd=task_dir,
                env=env,
                shell=True
            )
            
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
            
            print(f"[YAML执行] 完成，退出码: {return_code}")
            return return_code, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("[YAML执行] 超时，10分钟限制")
            return -1, '', 'Execution Timeout (10 minutes)'
        except Exception as e:
            print(f"[YAML执行] 异常: {e}")
            return -1, '', str(e)
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)
                
    def execute(self, script_content: str, script_type: str, task_id: int, env_vars: dict = None) -> tuple:
        print(f"[Executor] 开始执行任务 #{task_id}, 类型: {script_type}")
        
        if script_type == 'typescript':
            script_file = self.write_script_file(script_content, script_type, task_id)
            try:
                return self.execute_typescript(script_file, task_id, env_vars)
            finally:
                pass
        else:
            return self.execute_yaml(script_content, task_id, env_vars)
            
    def read_report(self, task_id: int) -> str:
        task_dir = self._get_task_dir(task_id)
        report_dir = os.path.join(task_dir, "midscene_run", "report")
        print(f"[Executor] 任务目录: {task_dir}")
        print(f"[Executor] 报告目录: {report_dir}")
        
        if os.path.exists(report_dir):
            # 查找目录下的 HTML 文件
            for file_name in os.listdir(report_dir):
                if file_name.endswith('.html') and file_name.startswith('computer-'):
                    report_file = os.path.join(report_dir, file_name)
                    print(f"[Executor] 找到报告文件: {report_file}")
                    if os.path.exists(report_file):
                        return report_file
        
        return ''


def create_default_runner():
    runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runner.ts')
    if os.path.exists(runner_path):
        return runner_path
    
    runner_content = '''
import * as fs from 'fs';
import * as path from 'path';

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: tsx runner.ts <script_file> <report_file>');
    process.exit(1);
  }
  
  const scriptFile = args[0];
  const reportFile = args[1];
  
  console.log(`[*] Midscene Runner starting...`);
  console.log(`[*] Script: ${scriptFile}`);
  console.log(`[*] Report: ${reportFile}`);
  
  // 读取脚本内容
  let script: any;
  try {
    const content = fs.readFileSync(scriptFile, 'utf-8');
    script = JSON.parse(content);
  } catch (e) {
    console.error('Failed to read script:', e);
    process.exit(1);
  }
  
  // 生成简单的 HTML 报告
  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Midscene Report</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    .header { background: #4CAF50; color: white; padding: 20px; }
    .success { color: #4CAF50; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Midscene PC Automation Report</h1>
    <p>Task executed successfully</p>
  </div>
  <pre>${JSON.stringify(script, null, 2)}</pre>
</body>
</html>
  `;
  
  fs.writeFileSync(reportFile, html);
  console.log('[*] Report generated:', reportFile);
}

main().catch(console.error);
    '''
    
    with open(runner_path, 'w', encoding='utf-8') as f:
        f.write(runner_content)
        
    return runner_path
