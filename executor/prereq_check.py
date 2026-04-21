import subprocess
import os
import sys
import shutil


def check_python():
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True, shell=True)
        version_str = result.stdout.strip()
        if 'Python 3.' in version_str:
            version_num = version_str.replace('Python ', '')
            major, minor, _ = version_num.split('.')
            if int(minor) >= 10:
                return {'passed': True, 'version': version_str}
        return {'passed': False, 'message': f'Python 版本需要 >= 3.10，当前为 {version_str}'}
    except Exception as e:
        return {'passed': False, 'message': '未找到 Python，请先安装 Python 3.10+'}


def check_nodejs():
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, shell=True)
        version_str = result.stdout.strip()
        if version_str.startswith('v'):
            version_num = version_str.replace('v', '')
            major, minor = version_num.split('.')
            if int(major) >= 18:
                return {'passed': True, 'version': version_str}
        return {'passed': False, 'message': f'Node.js 版本需要 >= 18.0，当前为 {version_str}'}
    except Exception as e:
        return {'passed': False, 'message': '未找到 Node.js，请先安装 Node.js 18+'}


def check_npm():
    try:
        result = subprocess.run(['npx', '--version'], capture_output=True, text=True, shell=True)
        version_str = result.stdout.strip()
        return {'passed': True, 'version': version_str}
    except Exception as e:
        return {'passed': False, 'message': '未找到 npx，请检查 Node.js 安装'}


def check_playwright():
    try:
        result = subprocess.run(
            ['python', '-m', 'playwright', '--version'],
            capture_output=True, text=True, shell=True
        )
        version_str = result.stdout.strip()
        if version_str:
            return {'passed': True, 'version': version_str}
        return {'passed': False, 'message': 'Playwright 未安装'}
    except Exception as e:
        return {'passed': False, 'message': 'Playwright 未安装，请运行: pip install playwright && playwright install'}


def check_midscene():
    try:
        result = subprocess.run(
            ['npx', '@midscene/web', '--version'],
            capture_output=True, text=True, shell=True,
            timeout=30
        )
        version_str = result.stdout.strip()
        if version_str:
            return {'passed': True, 'version': version_str}
        return {'passed': False, 'message': 'Midscene 未安装'}
    except subprocess.TimeoutExpired:
        return {'passed': False, 'message': 'Midscene 检查超时'}
    except Exception as e:
        return {'passed': False, 'message': 'Midscene 未安装，请运行: npx @midscene/web install'}


def check_midscene_in_node_modules():
    node_modules_path = get_node_modules_path()
    if node_modules_path and os.path.exists(node_modules_path):
        midscene_path = os.path.join(node_modules_path, '@midscene', 'web')
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
