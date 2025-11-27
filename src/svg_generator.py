"""
SVG生成器模块
"""
import cv2
from config import SVG_CONFIG
from svg_templates import generate_remote_body, create_svg_document


class SVGGenerator:
    """SVG生成器，负责将图像处理结果转换为SVG"""

    def __init__(self):
        """初始化SVG生成器"""
        self.max_rx = SVG_CONFIG['max_corner_radius_x']
        self.max_ry = SVG_CONFIG['max_corner_radius_y']

    def simplify_contour(self, contour, epsilon_factor=0.01):
        """
        使用Ramer-Douglas-Peucker算法简化轮廓

        Args:
            contour: 轮廓点集
            epsilon_factor: 简化因子

        Returns:
            简化后的轮廓
        """
        if len(contour) < 3:
            return contour

        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        return simplified

    def contour_to_svg_path(self, contour):
        """
        将轮廓转换为SVG路径

        Args:
            contour: 轮廓点集

        Returns:
            SVG路径字符串
        """
        if len(contour) == 0:
            return ""

        # 简化轮廓
        simplified_contour = self.simplify_contour(contour, epsilon_factor=0.005)

        if len(simplified_contour) == 0:
            return ""

        # 构建路径
        path_data = "M "

        # 添加第一个点
        first_point = simplified_contour[0][0]
        path_data += f"{first_point[0]},{first_point[1]} "

        # 添加其余点
        for i in range(1, len(simplified_contour)):
            point = simplified_contour[i][0]
            path_data += f"L {point[0]},{point[1]} "

        # 闭合路径
        path_data += "Z"

        return path_data

    def _calculate_corner_radius(self, width, height):
        """
        计算圆角半径

        Args:
            width: 宽度
            height: 高度

        Returns:
            (rx, ry) 圆角半径元组
        """
        rx = min(self.max_rx, width // 10)
        ry = min(self.max_ry, height // 20)
        return rx, ry

    def _adjust_coordinates(self, x, y, offset_x, offset_y):
        """
        根据裁剪偏移调整坐标

        Args:
            x, y: 原始坐标
            offset_x, offset_y: 偏移量

        Returns:
            (adjusted_x, adjusted_y) 调整后的坐标
        """
        return x - offset_x, y - offset_y

    def generate_svg(self, width, height, main_contour=None, features=None,
                    padded_rect=None, crop_offset=(0, 0)):
        """
        生成SVG文档

        Args:
            width, height: SVG画布尺寸
            main_contour: 主体轮廓
            features: 特征列表（暂未使用）
            padded_rect: 带边距的矩形 (x, y, w, h)
            crop_offset: 裁剪偏移 (offset_x, offset_y)

        Returns:
            完整的SVG文档字符串
        """
        offset_x, offset_y = crop_offset

        # 优先使用带边距的矩形
        if padded_rect is not None:
            x, y, w, h = padded_rect
            print(f"[SVG_GEN] ========== SVG生成开始 ==========", flush=True)
            print(f"[SVG_GEN] 输入 padded_rect: x={x}, y={y}, w={w}, h={h}", flush=True)
            print(f"[SVG_GEN] 输入 crop_offset: offset_x={offset_x}, offset_y={offset_y}", flush=True)
            print(f"[SVG_GEN] 输入 canvas: width={width}, height={height}", flush=True)

            x, y = self._adjust_coordinates(x, y, offset_x, offset_y)
            rx, ry = self._calculate_corner_radius(w, h)

            print(f"[SVG_GEN] 调整后坐标: x={x}, y={y}", flush=True)
            print(f"[SVG_GEN] 矩形尺寸: w={w}, h={h}", flush=True)
            print(f"[SVG_GEN] 圆角半径: rx={rx}, ry={ry}", flush=True)
            print(f"[SVG_GEN] ========== SVG生成结束 ==========", flush=True)

            body = generate_remote_body(x, y, w, h, rx, ry)
            return create_svg_document(width, height, body,
                                      "基于带边距检测轮廓的主体")

        # 退回到使用原始轮廓
        elif main_contour is not None and len(main_contour) >= 4:
            x, y, w, h = cv2.boundingRect(main_contour)
            x, y = self._adjust_coordinates(x, y, offset_x, offset_y)
            rx, ry = self._calculate_corner_radius(w, h)

            body = generate_remote_body(x, y, w, h, rx, ry)
            return create_svg_document(width, height, body,
                                      "基于检测轮廓的主体")

        # 默认模板
        else:
            x, y, w, h = 320, 200, 320, 880
            rx, ry = self._calculate_corner_radius(w, h)

            body = generate_remote_body(x, y, w, h, rx, ry)
            return create_svg_document(width, height, body,
                                      "默认主体")