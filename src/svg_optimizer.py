"""
SVG智能优化模块
通过图像相似度对比迭代优化SVG生成参数
使用OpenCV内置方法，无需额外依赖
"""
import cv2
import numpy as np
import io
from PIL import Image


class SVGOptimizer:
    """SVG智能优化器，通过迭代对比提升生成质量"""

    def __init__(self, similarity_threshold=0.95, max_iterations=10):
        """
        初始化优化器

        Args:
            similarity_threshold: 相似度阈值（0-1），达到此值停止优化
            max_iterations: 最大迭代次数，防止死循环
        """
        self.similarity_threshold = similarity_threshold
        self.max_iterations = max_iterations

    def svg_to_image(self, svg_content, width, height):
        """
        将SVG转换为numpy图像数组

        注意：此方法需要SVG渲染库支持
        目前返回None，可以后续集成SVG渲染

        Args:
            svg_content: SVG字符串
            width, height: 目标尺寸

        Returns:
            numpy数组格式的图像，失败返回None
        """
        # TODO: 集成SVG渲染库（如cairosvg、svglib等）
        # 暂时返回None，先实现框架
        print(f"[SVG_OPT] SVG渲染功能待实现", flush=True)
        return None

    def calculate_similarity(self, img1, img2):
        """
        计算两张图像的相似度 (使用OpenCV内置方法)

        Args:
            img1, img2: numpy数组格式的图像

        Returns:
            相似度分数（0-1）和详细指标
        """
        # 确保两张图像尺寸一致
        if img1.shape != img2.shape:
            print(f"[SVG_OPT] 图像尺寸不匹配: {img1.shape} vs {img2.shape}", flush=True)
            return 0.0, {}

        # 转换为灰度图
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY) if len(img2.shape) == 3 else img2

        # 1. 均方误差 (MSE)
        mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)

        # 2. 峰值信噪比 (PSNR)
        if mse == 0:
            psnr = 100
        else:
            max_pixel = 255.0
            psnr = 20 * np.log10(max_pixel / np.sqrt(mse))

        # 3. 颜色直方图相似度
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # 4. 模板匹配相似度
        template_match = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]

        # 综合相似度 (权重: PSNR 40%, 直方图 30%, 模板匹配 30%)
        psnr_normalized = min(psnr / 50.0, 1.0)  # 归一化到0-1
        overall_similarity = (
            0.4 * psnr_normalized +
            0.3 * hist_similarity +
            0.3 * max(0, template_match)  # 确保非负
        )

        metrics = {
            'mse': float(mse),
            'psnr': float(psnr),
            'hist_similarity': float(hist_similarity),
            'template_match': float(template_match),
            'overall': float(overall_similarity)
        }

        return overall_similarity, metrics

    def extract_color_from_image(self, image, x, y, sample_size=5):
        """
        从图像指定位置提取颜色

        Args:
            image: numpy数组格式的图像
            x, y: 坐标
            sample_size: 采样区域大小（取周围像素平均值）

        Returns:
            RGB颜色元组
        """
        h, w = image.shape[:2]

        # 确保坐标在范围内
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))

        # 定义采样区域
        x1 = max(0, x - sample_size // 2)
        x2 = min(w, x + sample_size // 2 + 1)
        y1 = max(0, y - sample_size // 2)
        y2 = min(h, y + sample_size // 2 + 1)

        # 提取区域并计算平均颜色
        region = image[y1:y2, x1:x2]

        if len(region.shape) == 3:
            avg_color = np.mean(region, axis=(0, 1))
            return tuple(avg_color.astype(int))
        else:
            avg_gray = np.mean(region)
            return (int(avg_gray), int(avg_gray), int(avg_gray))

    def optimize_svg_parameters(self, original_image, svg_generator, initial_params):
        """
        迭代优化SVG生成参数

        Args:
            original_image: 原始图像 (numpy数组)
            svg_generator: SVG生成器实例
            initial_params: 初始参数字典

        Returns:
            优化后的参数和优化历史
        """
        best_params = initial_params.copy()
        best_similarity = 0.0
        history = []

        h, w = original_image.shape[:2]

        print(f"\n[SVG_OPT] ========== 开始智能优化 ==========", flush=True)
        print(f"[SVG_OPT] 相似度阈值: {self.similarity_threshold}", flush=True)
        print(f"[SVG_OPT] 最大迭代次数: {self.max_iterations}", flush=True)

        for iteration in range(self.max_iterations):
            print(f"\n[SVG_OPT] --- 迭代 {iteration + 1}/{self.max_iterations} ---", flush=True)

            # 生成当前参数的SVG
            svg_content = svg_generator.generate_svg(**best_params)

            # 将SVG转换为图像
            svg_image = self.svg_to_image(svg_content, w, h)

            if svg_image is None:
                print(f"[SVG_OPT] SVG转换失败，停止优化", flush=True)
                break

            # 计算相似度
            similarity, metrics = self.calculate_similarity(original_image, svg_image)

            print(f"[SVG_OPT] 相似度: {similarity:.4f}", flush=True)
            print(f"[SVG_OPT] SSIM: {metrics['ssim']:.4f}, PSNR: {metrics['psnr']:.2f}, "
                  f"直方图: {metrics['hist_similarity']:.4f}", flush=True)

            # 记录历史
            history.append({
                'iteration': iteration + 1,
                'similarity': similarity,
                'metrics': metrics,
                'params': best_params.copy()
            })

            # 检查是否达到阈值
            if similarity >= self.similarity_threshold:
                print(f"[SVG_OPT] ✓ 达到相似度阈值 {self.similarity_threshold}，停止优化", flush=True)
                best_similarity = similarity
                break

            # 更新最佳参数
            if similarity > best_similarity:
                best_similarity = similarity

            # 这里可以添加参数调整逻辑
            # 例如：根据误差调整圆角、位置、尺寸等参数
            # TODO: 实现参数优化算法

        print(f"\n[SVG_OPT] ========== 优化完成 ==========", flush=True)
        print(f"[SVG_OPT] 最终相似度: {best_similarity:.4f}", flush=True)
        print(f"[SVG_OPT] 迭代次数: {len(history)}", flush=True)

        return best_params, history
