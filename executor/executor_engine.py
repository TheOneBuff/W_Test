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
        
    def write_script_file(self, script_content: str, script_type: str, task_id: int) -> str:
        ext = 'ts' if script_type == 'typescript' else 'yaml'
        self.script_file = os.path.join(self.working_dir, f"task_{task_id}_script.{ext}")
        
        with open(self.script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        return self.script_file
        
    def write_html_report(self, html_content: str, task_id: int) -> str:
        self.report_file = os.path.join(self.working_dir, f"task_{task_id}_report.html")
        
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
        
    def execute_typescript(self, script_file: str, task_id: int, env_vars: dict = None) -> tuple:
        report_file = os.path.join(self.working_dir, f"task_{task_id}_report.html")
        
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            
        cmd = ['npx', 'tsx', 'runner.ts', script_file, report_file]
        
        print(f"[Executor] 执行命令: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_dir,
                env=env
            )
            
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
            
            return return_code, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            return -1, '', 'Execution Timeout (10 minutes)'
        except Exception as e:
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
        
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            
        report_file = os.path.join(self.working_dir, f"task_{task_id}_report.html")
        cmd = ['npx', 'tsx', 'runner.ts', script_file, report_file]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_dir,
                env=env
            )
            
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
            
            return return_code, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            return -1, '', 'Execution Timeout (10 minutes)'
        except Exception as e:
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
        report_file = os.path.join(self.working_dir, f"task_{task_id}_report.html")
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                return f.read()
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
