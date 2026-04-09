#!/usr/bin/env python
"""
运行数据库迁移脚本

在容器启动时执行，应用所有未应用的迁移
"""
import subprocess
import sys
import os

def run_migrations():
    print("开始运行数据库迁移...")
    try:
        # 获取脚本所在目录的父目录（即 backend 目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 运行 alembic upgrade 命令
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=script_dir
        )
        
        if result.returncode == 0:
            print("数据库迁移成功完成！")
            print("输出:", result.stdout)
        else:
            print("数据库迁移失败！")
            print("错误:", result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"运行迁移时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
