"""
自动颜色提取模块
从产品图像自动提取渐变色
"""
import cv2
import numpy as np


class ColorExtractor:
    """自动颜色提取器"""

    def __init__(self):
        # 点阵采样配置(使用比例而不是像素)
        self.y_step_percent = 0.05  # Y轴步长比例(默认5% = 每5%采样一次 = 20行)
        self.x_samples = 5  # 水平方向采样点数(对应0%, 25%, 50%, 75%, 100%)

    def extract_gradient_colors(self, image, num_samples=5):
        """
        从图像自动提取渐变色

        Args:
            image: numpy数组格式的图像
            num_samples: 采样点数量

        Returns:
            颜色列表，按Y坐标排序
        """
        h, w = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1

        colors = []
        print(f"[颜色提取] 图像尺寸: {w}x{h}, 通道数: {channels}, 采样点数: {num_samples}", flush=True)
        print(f"[颜色提取] 图像类型: {image.dtype}, 形状: {image.shape}", flush=True)

        # 在图像宽度方向(X轴)均匀采样，获取左右渐变
        for i in range(num_samples):
            x = int(w * (i + 0.5) / num_samples)

            # 采样策略：在遥控器主体边缘采样，避开中间按钮区域
            # 分三段采样：顶部20%、底部20%区域
            sample_regions = []

            # 顶部区域(上方20%)
            y_top = int(h * 0.1)
            y_top_end = int(h * 0.3)

            # 底部区域(下方20%)
            y_bottom = int(h * 0.7)
            y_bottom_end = int(h * 0.9)

            sample_size = 15
            x1, x2 = max(0, x - sample_size//2), min(w, x + sample_size//2 + 1)

            # 从顶部和底部各采样
            region_top = image[y_top:y_top_end, x1:x2]
            region_bottom = image[y_bottom:y_bottom_end, x1:x2]

            # 合并区域取平均
            combined = np.concatenate([region_top.reshape(-1, 3), region_bottom.reshape(-1, 3)], axis=0)
            avg_color = np.mean(combined, axis=0).astype(int)

            if i == 0:  # 只在第一次打印调试信息
                print(f"[DEBUG] 采样位置: x={x}, 顶部y=[{y_top},{y_top_end}], 底部y=[{y_bottom},{y_bottom_end}]", flush=True)
                print(f"[DEBUG] 顶部区域shape: {region_top.shape}, 底部区域shape: {region_bottom.shape}", flush=True)

            # OpenCV使用BGR，转换为RGB
            if len(avg_color) >= 3:
                b, g, r = avg_color[:3]
            else:
                r = g = b = avg_color[0]

            hex_color = f"{r:02x}{g:02x}{b:02x}"

            colors.append({
                'x': x,
                'r': int(r),
                'g': int(g),
                'b': int(b),
                'hex': hex_color,
                'offset': int((i / (num_samples - 1)) * 100) if num_samples > 1 else 0
            })

            print(f"[颜色提取] 点{i+1}/{num_samples}: X={x}, RGB=({r},{g},{b}) #{hex_color}", flush=True)

        return colors

    def generate_svg_gradient(self, colors, gradient_id="remoteGradient"):
        """
        根据颜色列表生成SVG渐变定义

        Args:
            colors: 颜色列表
            gradient_id: 渐变ID

        Returns:
            SVG渐变定义字符串
        """
        # 水平渐变：从左(x1=0%)到右(x2=100%)
        gradient = f'<linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="0%">\n'

        for color in colors:
            gradient += f'  <stop offset="{color["offset"]}%" style="stop-color:#{color["hex"]};stop-opacity:1" />\n'

        gradient += '</linearGradient>'

        return gradient

    def apply_gradient_to_svg_content(self, svg_content, gradient_def):
        """
        替换SVG内容中的渐变定义

        Args:
            svg_content: 原始SVG字符串
            gradient_def: 新的渐变定义

        Returns:
            更新后的SVG字符串
        """
        import re

        # 查找并替换 <linearGradient id="remoteGradient" ...> ... </linearGradient>
        pattern = r'<linearGradient id="remoteGradient"[^>]*>.*?</linearGradient>'

        if re.search(pattern, svg_content, re.DOTALL):
            new_svg = re.sub(pattern, gradient_def, svg_content, flags=re.DOTALL)
            print("[颜色提取] ✓ 已替换SVG中的渐变色定义", flush=True)
            return new_svg
        else:
            print("[颜色提取] ⚠ 未找到渐变色定义，返回原SVG", flush=True)
            return svg_content

    def extract_color_grid(self, image, y_step_percent=None, x_samples=None):
        """
        点阵式颜色采样

        Args:
            image: numpy数组格式的图像
            y_step_percent: Y轴步长比例(0-1),默认使用self.y_step_percent
            x_samples: X轴采样点数,默认使用self.x_samples

        Returns:
            颜色网格列表: [{'x': x, 'y': y, 'r': r, 'g': g, 'b': b, 'hex': hex}, ...]
        """
        y_step_percent = y_step_percent or self.y_step_percent
        x_samples = x_samples or self.x_samples

        h, w = image.shape[:2]
        color_grid = []

        print(f"[点阵采样] 图像尺寸: {w}x{h}, Y步长: {y_step_percent*100:.1f}%, X采样数: {x_samples}", flush=True)

        # Y轴: 按比例采样
        y_count = int(1.0 / y_step_percent) + 1  # 采样点数
        y_positions = [int(h * i * y_step_percent) for i in range(y_count) if i * y_step_percent <= 1.0]

        # X轴: 均匀分布
        x_positions = [int(w * i / (x_samples - 1)) if x_samples > 1 else w // 2
                       for i in range(x_samples)]

        sample_size = 5  # 每个点的采样区域

        total_points = len(y_positions) * len(x_positions)
        print(f"[点阵采样] 总采样点数: {total_points} ({len(y_positions)}行 x {x_samples}列)", flush=True)

        for y in y_positions:
            for i, x in enumerate(x_positions):
                # 采样区域
                y1, y2 = max(0, y - sample_size//2), min(h, y + sample_size//2 + 1)
                x1, x2 = max(0, x - sample_size//2), min(w, x + sample_size//2 + 1)

                region = image[y1:y2, x1:x2]
                avg_color = np.mean(region, axis=(0, 1)).astype(int)

                # OpenCV使用BGR，转换为RGB
                if len(avg_color) >= 3:
                    b, g, r = avg_color[:3]
                else:
                    r = g = b = avg_color[0]

                hex_color = f"{r:02x}{g:02x}{b:02x}"

                color_grid.append({
                    'x': x,
                    'y': y,
                    'r': int(r),
                    'g': int(g),
                    'b': int(b),
                    'hex': hex_color
                })

        print(f"[点阵采样] ✓ 完成采样,共{len(color_grid)}个颜色点", flush=True)
        return color_grid

    def extract_contour_color(self, image, contour_info):
        """
        提取轮廓内部的平均颜色

        Args:
            image: numpy数组格式的图像
            contour_info: 轮廓信息字典,包含 'contour' 和 'bounding_box'

        Returns:
            颜色字典: {'r': r, 'g': g, 'b': b, 'hex': hex}
        """
        h, w = image.shape[:2]

        # 创建掩码
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [contour_info['contour']], -1, 255, -1)

        # 计算轮廓内部的平均颜色
        masked_pixels = image[mask == 255]

        if len(masked_pixels) > 0:
            avg_color = np.mean(masked_pixels, axis=0).astype(int)

            # OpenCV使用BGR，转换为RGB
            if len(avg_color) >= 3:
                b, g, r = avg_color[:3]
            else:
                r = g = b = avg_color[0]

            hex_color = f"{r:02x}{g:02x}{b:02x}"

            return {
                'r': int(r),
                'g': int(g),
                'b': int(b),
                'hex': hex_color
            }
        else:
            # 如果没有像素，返回默认颜色（灰色）
            return {
                'r': 128,
                'g': 128,
                'b': 128,
                'hex': '808080'
            }
