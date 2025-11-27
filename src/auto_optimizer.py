"""
全自动SVG优化模块
自动提取颜色、优化参数、生成最佳SVG
"""
import cv2
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import base64
import time


class AutoSVGOptimizer:
    """全自动SVG优化器"""

    def __init__(self, use_gpu=False):
        """
        初始化优化器

        Args:
            use_gpu: 是否使用GPU加速（需要PyTorch）
        """
        self.use_gpu = use_gpu
        self.driver = None

        # 尝试导入PyTorch
        if use_gpu:
            try:
                import torch
                self.torch = torch
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                print(f"[优化器] 使用设备: {self.device}", flush=True)
            except ImportError:
                print("[优化器] PyTorch未安装，使用CPU模式", flush=True)
                self.use_gpu = False

    def init_browser(self):
        """初始化无头浏览器用于SVG渲染"""
        if self.driver is not None:
            return

        print("[优化器] 初始化Chrome浏览器...", flush=True)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("[优化器] 浏览器初始化成功", flush=True)
        except Exception as e:
            print(f"[优化器] 浏览器初始化失败: {e}", flush=True)
            self.driver = None

    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def svg_to_image(self, svg_content, width, height):
        """
        使用Selenium将SVG渲染为图像

        Args:
            svg_content: SVG字符串
            width, height: 目标尺寸

        Returns:
            numpy数组格式的图像
        """
        if self.driver is None:
            self.init_browser()

        if self.driver is None:
            print("[优化器] 无法渲染SVG，浏览器未初始化", flush=True)
            return None

        try:
            # 创建HTML页面包含SVG
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        width: {width}px;
                        height: {height}px;
                        overflow: hidden;
                    }}
                </style>
            </head>
            <body>
                {svg_content}
            </body>
            </html>
            """

            # 加载HTML
            self.driver.get("data:text/html;charset=utf-8," + html)
            time.sleep(0.5)  # 等待渲染

            # 截图
            screenshot = self.driver.get_screenshot_as_png()

            # 转换为numpy数组
            pil_image = Image.open(io.BytesIO(screenshot))
            image_array = np.array(pil_image)

            # 转换为RGB
            if image_array.shape[2] == 4:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)

            # 裁剪到指定尺寸
            image_array = image_array[:height, :width]

            return image_array

        except Exception as e:
            print(f"[优化器] SVG渲染失败: {e}", flush=True)
            return None

    def extract_colors_from_image(self, image, num_samples=5):
        """
        从图像自动提取代表性颜色

        Args:
            image: numpy数组格式的图像
            num_samples: 采样点数量

        Returns:
            颜色列表，按Y坐标排序
        """
        h, w = image.shape[:2]

        colors = []
        # 在图像高度方向均匀采样
        for i in range(num_samples):
            y = int(h * (i + 0.5) / num_samples)
            x = w // 2  # 取中心列

            # 提取5x5区域的平均颜色
            y1, y2 = max(0, y - 2), min(h, y + 3)
            x1, x2 = max(0, x - 2), min(w, x + 3)

            region = image[y1:y2, x1:x2]
            avg_color = np.mean(region, axis=(0, 1)).astype(int)

            r, g, b = avg_color[:3]
            hex_color = f"{r:02x}{g:02x}{b:02x}"

            colors.append({
                'y': y,
                'r': int(r),
                'g': int(g),
                'b': int(b),
                'hex': hex_color,
                'offset': int((i / (num_samples - 1)) * 100) if num_samples > 1 else 0
            })

            print(f"[优化器] 采样点 {i+1}/{num_samples}: Y={y}, RGB=({r},{g},{b}) #{hex_color}", flush=True)

        return colors

    def generate_gradient_svg_def(self, colors):
        """
        根据颜色列表生成SVG渐变定义

        Args:
            colors: 颜色列表

        Returns:
            SVG渐变定义字符串
        """
        gradient = '<linearGradient id="remoteGradient" x1="0%" y1="0%" x2="0%" y2="100%">\n'

        for color in colors:
            gradient += f'  <stop offset="{color["offset"]}%" style="stop-color:#{color["hex"]};stop-opacity:1" />\n'

        gradient += '</linearGradient>'

        return gradient

    def calculate_similarity(self, img1, img2):
        """
        计算两张图像的相似度

        Args:
            img1, img2: numpy数组格式的图像

        Returns:
            相似度分数（0-1）和详细指标
        """
        if img1.shape != img2.shape:
            print(f"[优化器] 图像尺寸不匹配: {img1.shape} vs {img2.shape}", flush=True)
            return 0.0, {}

        # 转换为灰度图
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY) if len(img2.shape) == 3 else img2

        # 均方误差
        mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)

        # 峰值信噪比
        if mse == 0:
            psnr = 100
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))

        # 直方图相似度
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # 综合相似度
        psnr_normalized = min(psnr / 50.0, 1.0)
        overall = 0.5 * psnr_normalized + 0.5 * hist_similarity

        metrics = {
            'mse': float(mse),
            'psnr': float(psnr),
            'hist_similarity': float(hist_similarity),
            'overall': float(overall)
        }

        return overall, metrics

    def optimize_svg(self, original_image, svg_generator, initial_params,
                     similarity_threshold=0.85, max_iterations=5):
        """
        全自动优化SVG生成

        Args:
            original_image: 原始图像（numpy数组）
            svg_generator: SVG生成器实例
            initial_params: 初始参数
            similarity_threshold: 相似度阈值
            max_iterations: 最大迭代次数

        Returns:
            优化后的SVG内容和优化历史
        """
        print(f"\n[优化器] ========== 开始全自动优化 ==========", flush=True)
        print(f"[优化器] 相似度阈值: {similarity_threshold}", flush=True)
        print(f"[优化器] 最大迭代: {max_iterations}", flush=True)

        h, w = original_image.shape[:2]
        best_svg = None
        best_similarity = 0.0
        history = []

        # 1. 自动提取颜色
        print(f"\n[优化器] 步骤1: 从原图提取颜色...", flush=True)
        colors = self.extract_colors_from_image(original_image, num_samples=5)

        # 2. 生成新的渐变色定义
        gradient_def = self.generate_gradient_svg_def(colors)
        print(f"\n[优化器] 生成的渐变色:\n{gradient_def}", flush=True)

        # 3. 迭代优化
        for iteration in range(max_iterations):
            print(f"\n[优化器] --- 迭代 {iteration + 1}/{max_iterations} ---", flush=True)

            # 生成SVG
            svg_content = svg_generator.generate_svg(**initial_params)

            # TODO: 这里可以动态替换SVG中的渐变色定义
            # 暂时使用初始SVG

            # 渲染SVG为图像
            svg_image = self.svg_to_image(svg_content, w, h)

            if svg_image is None:
                print(f"[优化器] SVG渲染失败，跳过迭代 {iteration + 1}", flush=True)
                continue

            # 计算相似度
            similarity, metrics = self.calculate_similarity(original_image, svg_image)

            print(f"[优化器] 相似度: {similarity:.4f}", flush=True)
            print(f"[优化器] PSNR: {metrics['psnr']:.2f} dB, "
                  f"直方图: {metrics['hist_similarity']:.4f}", flush=True)

            # 记录历史
            history.append({
                'iteration': iteration + 1,
                'similarity': similarity,
                'metrics': metrics
            })

            # 更新最佳结果
            if similarity > best_similarity:
                best_similarity = similarity
                best_svg = svg_content
                print(f"[优化器] ✓ 新的最佳相似度: {best_similarity:.4f}", flush=True)

            # 检查是否达到阈值
            if similarity >= similarity_threshold:
                print(f"[优化器] ✓ 达到相似度阈值 {similarity_threshold}", flush=True)
                break

        print(f"\n[优化器] ========== 优化完成 ==========", flush=True)
        print(f"[优化器] 最终相似度: {best_similarity:.4f}", flush=True)
        print(f"[优化器] 总迭代次数: {len(history)}", flush=True)

        return {
            'svg_content': best_svg,
            'similarity': best_similarity,
            'colors': colors,
            'gradient_def': gradient_def,
            'history': history
        }
