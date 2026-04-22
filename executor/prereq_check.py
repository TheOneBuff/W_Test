import subprocess
import os
import sys
import shutil
import shutil as _shutil


def _run_cmd(cmd, timeout=10):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except FileNotFoundError:
        return "NOT_FOUND", -2
    except Exception as e:
        return f"ERROR: {e}", -3


def check_python():
    stdout, code = _run_cmd('python --version')
    if code == 0 and 'Python 3.' in stdout:
        version_num = stdout.replace('Python ', '')
        try:
            major, minor, _ = version_num.split('.')
            if int(minor) >= 10:
                return {'passed': True, 'version': stdout}
        except:
            pass
    return {'passed': False, 'message': f'Python 版本需要 >= 3.10，当前为 {stdout}'}


def check_nodejs():
    stdout, code = _run_cmd('node --version')
    if code == 0 and stdout.startswith('v'):
        version_num = stdout.replace('v', '')
        try:
            major = int(version_num.split('.')[0])
            if major >= 24:
                return {'passed': True, 'version': stdout}
            return {'passed': False, 'message': f'Node.js 版本需要 >= 24.0，当前为 {stdout}'}
        except:
            return {'passed': False, 'message': f'Node.js 版本需要 >= 24.0，当前为 {stdout}'}
    return {'passed': False, 'message': f'Node.js 未找到: {stdout}'}


def check_npm():
    stdout, code = _run_cmd('npx --version')
    if code == 0:
        return {'passed': True, 'version': stdout}
    return {'passed': False, 'message': f'npx 未找到: {stdout}'}


def check_playwright():
    return {'passed': True, 'version': '跳过检查'}


def check_midscene():
    stdout, code = _run_cmd('npx @midscene/computer --version', timeout=30)
    if code == 0 and stdout and 'not found' not in stdout.lower():
        return {'passed': True, 'version': stdout}
    return {'passed': False, 'message': 'Midscene 未安装'}


def check_midscene_in_node_modules():
    node_modules_path = get_node_modules_path()
    if node_modules_path and os.path.exists(node_modules_path):
        midscene_path = os.path.join(node_modules_path, '@midscene', 'computer')
        if os.path.exists(midscene_path):
            return {'passed': True, 'path': midscene_path}
    return {'passed': False, 'message': 'Midscene 不在全局 node_modules 中'}


def get_node_modules_path():
    try:
        result = subprocess.run(
            ['npm', 'root', '-g'],
            capture_output=True, text=True, shell=True
        )
        return result.stdout.strip()
    except:
        return None


def check_adb():
    try:
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, shell=True)
        version_str = result.stdout.strip()
        if version_str:
            return {'passed': True, 'version': version_str}
        return {'passed': False, 'message': 'ADB 未安装'}
    except Exception as e:
        return {'passed': False, 'message': 'ADB 未安装，请安装 Android SDK 并配置 PATH'}


def check_android_sdk():
    try:
        result = subprocess.run(['echo', '%ANDROID_HOME%'], capture_output=True, text=True, shell=True)
        android_home = result.stdout.strip()
        if android_home and os.path.exists(android_home):
            return {'passed': True, 'path': android_home}
        return {'passed': False, 'message': 'ANDROID_HOME 环境变量未设置'}
    except Exception as e:
        return {'passed': False, 'message': 'ANDROID_HOME 环境变量未设置'}


def check_prerequisites_for_pc():
    checks = {
        'python': check_python(),
        'nodejs': check_nodejs(),
        'npx': check_npm(),
        'playwright': check_playwright(),
        'midscene': check_midscene()
    }
    
    all_passed = all(checks[key]['passed'] for key in checks)
    
    return {
        'all_passed': all_passed,
        'checks': checks,
        'summary': f"{sum(1 for k in checks if checks[k]['passed'])}/{len(checks)} 检查通过"
    }


def check_prerequisites_for_android():
    checks = {
        'python': check_python(),
        'nodejs': check_nodejs(),
        'npx': check_npm(),
        'adb': check_adb(),
        'android_sdk': check_android_sdk(),
        'midscene_android': check_midscene()
    }
    
    all_passed = all(checks[key]['passed'] for key in checks)
    
    return {
        'all_passed': all_passed,
        'checks': checks,
        'summary': f"{sum(1 for k in checks if checks[k]['passed'])}/{len(checks)} 检查通过"
    }


def run_all_checks():
    return check_prerequisites_for_pc()


def auto_install(checks):
    install_commands = []
    
    if not checks['playwright']['passed']:
        install_commands.append('pip install playwright && playwright install')
    
    if not checks['midscene']['passed']:
        install_commands.append('npm install -g @midscene/web')
    
    return install_commands


if __name__ == '__main__':
    print("请选择执行模式:")
    print("1. PC 桌面自动化")
    print("2. Android 自动化")
    
    choice = input("请输入 (1/2): ").strip()
    
    if choice == '2':
        result = check_prerequisites_for_android()
    else:
        result = check_prerequisites_for_pc()
    
    print(f"\n前置条件检查结果: {result['summary']}")
    for name, check in result['checks'].items():
        status = '✅' if check['passed'] else '❌'
        msg = check.get('message', f"版本: {check.get('version', 'N/A')}")
        print(f"  {status} {name}: {msg}")
