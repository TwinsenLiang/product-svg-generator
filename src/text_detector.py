"""
文本和图标检测模块
使用 OCR 检测按钮上的文字和图标
"""
import cv2
import numpy as np
from PIL import Image
import pytesseract


class TextDetector:
    """文本和图标检测器"""

    def __init__(self):
        # 配置 Tesseract
        self.tesseract_config = '--psm 6 --oem 3'

    def detect_button_content(self, image, contour_info):
        """
        检测按钮区域内的文字或图标

        Args:
            image: numpy数组格式的图像
            contour_info: 轮廓信息字典

        Returns:
            检测结果: {'type': 'text/icon', 'content': '...', 'confidence': 0.0-1.0}
        """
        x, y, w, h = contour_info['bounding_box']

        # 裁剪按钮区域（扩展一点边距以便更好地识别）
        padding = 5
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(image.shape[1], x + w + padding)
        y2 = min(image.shape[0], y + h + padding)

        button_region = image[y1:y2, x1:x2]

        # 预处理图像以提高 OCR 准确度
        # 1. 转换为灰度
        gray = cv2.cvtColor(button_region, cv2.COLOR_BGR2GRAY)

        # 2. 反转颜色（如果按钮是深色背景）
        avg_color = np.mean(gray)
        if avg_color < 128:
            gray = cv2.bitwise_not(gray)

        # 3. 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 4. 放大图像以提高识别率
        scale = 3
        resized = cv2.resize(binary, (binary.shape[1] * scale, binary.shape[0] * scale),
                            interpolation=cv2.INTER_CUBIC)

        # 使用 Tesseract 进行 OCR
        try:
            text = pytesseract.image_to_string(resized, config=self.tesseract_config).strip()

            if text:
                # 清理识别结果
                text = text.upper().replace('\n', ' ').strip()

                # 检测是否为已知的按钮文字
                if 'MENU' in text:
                    return {
                        'type': 'text',
                        'content': 'MENU',
                        'confidence': 0.9
                    }
                elif any(char in text for char in ['▶', '||', '►', '⏸']):
                    return {
                        'type': 'icon',
                        'content': 'play_pause',
                        'confidence': 0.8
                    }
                else:
                    return {
                        'type': 'text',
                        'content': text,
                        'confidence': 0.5
                    }
        except Exception as e:
            print(f"[OCR错误] {e}", flush=True)

        return None

    def identify_button_by_position(self, contour_info, image_height):
        """
        根据位置推断按钮类型（当 OCR 失败时的备选方案）

        Args:
            contour_info: 轮廓信息
            image_height: 图像高度

        Returns:
            按钮标识: 'menu' 或 'play_pause'
        """
        x, y, w, h = contour_info['bounding_box']
        center_x = x + w / 2
        center_y = y + h / 2

        # 检测区域是否在下半部分（按钮通常在遥控器下方）
        is_lower_half = center_y > image_height * 0.5

        if not is_lower_half:
            return None

        # 根据水平位置判断（左边=MENU，右边=播放）
        # 假设图像宽度被分为左右两部分
        if center_x < contour_info.get('image_width', 1000) / 2:
            return 'menu'
        else:
            return 'play_pause'

    def generate_svg_text(self, content, cx, cy, r, fill_color='white'):
        """
        生成 SVG 文本元素

        Args:
            content: 文本内容
            cx, cy: 圆心坐标
            r: 圆半径
            fill_color: 文字颜色

        Returns:
            SVG text 元素字符串
        """
        font_size = int(r * 0.4)  # 字体大小约为半径的40%

        return (
            f'  <text x="{cx}" y="{cy}" '
            f'font-family="Arial, sans-serif" font-size="{font_size}" '
            f'fill="{fill_color}" text-anchor="middle" dominant-baseline="central">'
            f'{content}</text>'
        )

    def generate_svg_play_pause_icon(self, cx, cy, r, fill_color='white'):
        """
        生成播放/暂停图标的 SVG 元素

        Args:
            cx, cy: 圆心坐标
            r: 圆半径
            fill_color: 图标颜色

        Returns:
            SVG path 元素字符串
        """
        icon_size = r * 0.6

        # 播放三角形
        play_points = f"{cx - icon_size/4},{cy - icon_size/2} {cx - icon_size/4},{cy + icon_size/2} {cx + icon_size/3},{cy}"

        # 暂停双竖线
        pause_x1 = cx + icon_size/6
        pause_x2 = cx + icon_size/2
        pause_y1 = cy - icon_size/2
        pause_y2 = cy + icon_size/2
        pause_width = icon_size / 8

        svg = f'  <polygon points="{play_points}" fill="{fill_color}" />\n'
        svg += f'  <rect x="{pause_x1}" y="{pause_y1}" width="{pause_width}" height="{icon_size}" fill="{fill_color}" />\n'
        svg += f'  <rect x="{pause_x2}" y="{pause_y1}" width="{pause_width}" height="{icon_size}" fill="{fill_color}" />'

        return svg
