#!/usr/bin/env python3
"""
Auto SVG Generator 启动脚本
"""
import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from src.app import app
from config import FLASK_CONFIG

if __name__ == '__main__':
    print("🎨 启动 Auto SVG Generator...")
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    print(f"🌐 访问地址: http://{FLASK_CONFIG['host']}:{FLASK_CONFIG['port']}")

    app.run(**FLASK_CONFIG)
