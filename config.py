"""
项目配置文件
"""
import os

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 目录配置
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static')
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')

# Flask配置
FLASK_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'debug': False
}

# 图像处理配置
IMAGE_PROCESSING = {
    'default_padding': 10,
    'min_area_ratio': 0.03,  # 最小面积占比
    'max_area_ratio': 0.9,   # 最大面积占比
    'gaussian_blur_kernel': (3, 3),
    'morph_close_kernel': (11, 11),
    'morph_open_kernel': (3, 3),
}

# SVG生成配置
SVG_CONFIG = {
    'max_corner_radius_x': 30,
    'max_corner_radius_y': 30,
}

# 确保必要的目录存在
for directory in [STATIC_DIR, IMAGES_DIR, UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True)
