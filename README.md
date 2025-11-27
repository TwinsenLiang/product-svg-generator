# Auto SVG Generator

智能图像分析与SVG矢量图生成工具

## 功能特点

- **智能主体检测**：自动识别图像中的主要对象
- **轮廓提取**：精确提取物体轮廓
- **SVG生成**：基于检测结果生成矢量图
- **产品图片上传**：支持点击上传和拖拽上传产品图片
- **标记校验功能**：精确对比原图与SVG的坐标偏移
  - 在原图和SVG上点击对应位置添加数字标记
  - 自动计算X轴和Y轴的偏移量
  - 表格化显示配对状态和偏移数据
  - 偏移超过5像素会红色高亮提示
- **Web界面**：直观的可视化操作界面
- **实时预览**：即时查看处理结果

## 项目结构

```
auto_svg_generator/
├── config.py              # 项目配置
├── run.py                 # 启动脚本
├── requirements.txt       # 依赖列表
├── src/                   # 源代码目录
│   ├── app.py            # Flask应用
│   ├── image_processor.py # 图像处理模块
│   ├── svg_generator.py  # SVG生成模块
│   └── svg_templates.py  # SVG模板定义
├── static/               # 静态资源
│   ├── css/
│   ├── js/
│   ├── images/          # 测试图像
│   └── uploads/         # 上传图像
└── templates/           # HTML模板
    └── index.html
```

## 安装

1. 创建虚拟环境：
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用

启动服务：
```bash
python run.py
```

访问 http://localhost:8000 使用Web界面

## 配置

在 `config.py` 中可以调整：
- 图像处理参数（边距、面积阈值等）
- SVG生成参数（圆角半径等）
- 服务器配置（端口、主机等）

## 技术栈

- **后端**: Flask, OpenCV, NumPy
- **前端**: HTML, CSS, JavaScript
- **图像处理**: OpenCV轮廓检测、形态学操作
- **矢量图生成**: SVG标准

## 许可

Copyright © 2025
