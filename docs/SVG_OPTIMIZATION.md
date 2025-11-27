# SVG智能优化方案

## 概述

基于图像相似度的SVG自动迭代优化系统，通过对比原图和生成的SVG渲染图来不断调整参数，直到达到相似度阈值。

## 核心思路

```
1. 生成初始SVG
2. 将SVG渲染为图像
3. 计算渲染图与原图的相似度
4. 如果相似度 >= 阈值，停止优化
5. 否则，调整参数并重复步骤1-4
6. 最多迭代N次，防止死循环
```

## 相似度计算方法

使用OpenCV内置方法，无需额外依赖：

### 1. 均方误差 (MSE)
- 像素级差异计算
- 值越小越相似

### 2. 峰值信噪比 (PSNR)
- 图像质量指标
- 值越大越相似（通常>30dB为好）

### 3. 直方图相似度
- 颜色分布对比
- 值范围 0-1，越接近1越相似

### 4. 模板匹配
- 结构匹配度
- 值范围 -1到1，越接近1越相似

### 综合相似度
```python
overall = 0.4 * psnr_normalized + 0.3 * hist_similarity + 0.3 * template_match
```

## 参数优化策略

### 当前可优化的参数

1. **位置参数 (x, y)**
   - 根据偏移量自动调整
   - 从标记校验获取偏移数据

2. **尺寸参数 (w, h)**
   - 基于轮廓检测结果微调
   - 适应不同宽高比

3. **圆角半径 (rx, ry)**
   - 通过角点检测优化
   - 匹配实际产品圆角

4. **渐变色参数**
   - 从原图采样关键位置颜色
   - 自动生成渐变色

5. **光影效果**
   - 高光位置和强度
   - 阴影偏移和模糊度

## 性能优化

### 1. 防止死循环
```python
max_iterations = 10  # 最大迭代10次
```

### 2. 早停机制
```python
similarity_threshold = 0.95  # 达到95%相似度即停止
```

### 3. GPU加速
目前OpenCV的cv2.matchTemplate等函数在支持CUDA的系统上会自动使用GPU。

未来可以集成：
- `cv2.cuda` 模块（需要编译CUDA版OpenCV）
- PyTorch/TensorFlow进行深度学习优化

### 4. 内存管理
- 及时释放中间图像数组
- 使用numpy视图而非复制
- 限制图像尺寸（如最大1024px）

## 使用示例

```python
from src.svg_optimizer import SVGOptimizer
from src.svg_generator import SVGGenerator
import cv2

# 加载原图
original_image = cv2.imread('product.jpg')

# 创建优化器
optimizer = SVGOptimizer(
    similarity_threshold=0.95,
    max_iterations=10
)

# 初始参数
initial_params = {
    'width': 262,
    'height': 1000,
    'padded_rect': (0, 0, 262, 1000),
    'main_contour': None,
    'features': [],
    'crop_offset': (0, 0)
}

# 执行优化
svg_generator = SVGGenerator()
best_params, history = optimizer.optimize_svg_parameters(
    original_image,
    svg_generator,
    initial_params
)

# 查看优化历史
for record in history:
    print(f"迭代{record['iteration']}: 相似度={record['similarity']:.4f}")
```

## 未来改进方向

### 1. SVG渲染集成
当前SVG渲染功能待实现，可选方案：
- **cairosvg**: Python库，支持SVG转PNG（需要Cairo库）
- **svglib + reportlab**: 纯Python方案
- **Selenium + Chrome**: 通过浏览器渲染（重量级但准确）

### 2. 智能参数调整算法
- **梯度下降**: 根据相似度变化调整参数
- **遗传算法**: 多组参数并行优化
- **强化学习**: 学习最优参数调整策略

### 3. 多点采样优化
利用标记校验的多点数据：
```python
# 从3个标记点提取颜色
colors = [
    optimizer.extract_color_from_image(img, 208, 237),  # 位置1
    optimizer.extract_color_from_image(img, 159, 241),  # 位置2
    optimizer.extract_color_from_image(img, 261, 242),  # 位置3
]

# 生成自适应渐变
gradient = create_gradient_from_samples(colors)
```

### 4. GPU深度加速
```python
# 使用CUDA加速的OpenCV
import cv2.cuda as cuda

# 或使用PyTorch
import torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
```

## 当前限制

1. **SVG渲染**: 暂未集成渲染库，需要手动实现
2. **参数调整**: 目前只有框架，实际调整算法待完善
3. **GPU加速**: 依赖系统CUDA支持和cv2编译选项

## 贡献指南

欢迎贡献代码来完善以下部分：
- [ ] SVG渲染功能实现
- [ ] 参数优化算法
- [ ] GPU加速集成
- [ ] 更多相似度指标
- [ ] 可视化优化过程

---

*文档更新时间: 2025-11-27*
