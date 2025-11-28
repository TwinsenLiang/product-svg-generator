"""
Flask Web应用主文件
"""
import os
import sys
import base64
import time

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from flask import Flask, render_template, jsonify, request
import cv2

from config import TEMPLATE_DIR, STATIC_DIR, IMAGES_DIR, UPLOADS_DIR, IMAGE_PROCESSING
from image_processor import ImageProcessor
from svg_generator import SVGGenerator

# 创建Flask应用
app = Flask(__name__,
           template_folder=TEMPLATE_DIR,
           static_folder=STATIC_DIR)
app.config['JSON_AS_ASCII'] = False

# 默认测试图像路径
DEFAULT_IMAGE_NAME = "apple_remote_original.jpg"
DEFAULT_IMAGE_PATH = os.path.join(IMAGES_DIR, DEFAULT_IMAGE_NAME)

# 当前使用的图像路径（可以通过上传修改）
CURRENT_IMAGE_PATH = DEFAULT_IMAGE_PATH


def _prepare_debug_info(width, height, main_contour, features):
    """
    准备调试信息

    Args:
        width, height: 图像尺寸
        main_contour: 主体轮廓
        features: 特征列表

    Returns:
        调试信息字典
    """
    return {
        "图像尺寸": f"{width}x{height}",
        "主体轮廓点数": len(main_contour) if main_contour is not None else 0,
        "检测到的特征数": len(features),
        "SVG生成状态": "成功",
        "主要特征信息": [
            {
                "面积": f["area"],
                "宽高比": f"{f['aspect_ratio']:.2f}" if 'aspect_ratio' in f else "N/A",
                "填充度": f"{f['extent']:.2f}" if 'extent' in f else "N/A",
                "圆度": f"{f['circularity']:.2f}" if 'circularity' in f else "N/A"
            } for f in features[:5]
        ]
    }


def _prepare_crop_debug_info(x, y, w, h, main_contour, features):
    """
    准备裁剪图像的调试信息

    Args:
        x, y, w, h: 裁剪坐标和尺寸
        main_contour: 主体轮廓
        features: 特征列表

    Returns:
        调试信息字典
    """
    return {
        "裁剪后图像尺寸": f"{w}x{h}",
        "裁剪偏移": f"x:{x}, y:{y}",
        "主体轮廓点数": len(main_contour) if main_contour is not None else 0,
        "检测到的特征数": len(features),
        "SVG生成状态": "成功",
        "主要特征信息": [
            {
                "面积": f["area"],
                "宽高比": f"{f['aspect_ratio']:.2f}" if 'aspect_ratio' in f else "N/A",
                "填充度": f"{f['extent']:.2f}" if 'extent' in f else "N/A",
                "圆度": f"{f['circularity']:.2f}" if 'circularity' in f else "N/A"
            } for f in features[:5]
        ]
    }


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/generate_svg', methods=['POST'])
def generate_svg():
    """生成SVG（基于轮廓检测，每个轮廓单独绘制）"""
    try:
        from src.color_extractor import ColorExtractor

        # 初始化处理器
        processor = ImageProcessor(CURRENT_IMAGE_PATH)
        color_extractor = ColorExtractor()

        print(f"\n[基于轮廓的SVG生成] ========== 开始 ==========", flush=True)

        # 1. 先在原图上检测所有轮廓
        all_contours_original = processor.detect_all_contours()
        print(f"[SVG生成] 检测到 {len(all_contours_original)} 个轮廓", flush=True)

        # 2. 对每个轮廓提取颜色
        for i, contour_info in enumerate(all_contours_original):
            # 对圆形控制区使用环形采样，提取外圈颜色
            sample_ring = (contour_info['type'] == 'circle_control')
            color = color_extractor.extract_contour_color(
                processor.original_image, contour_info, sample_ring=sample_ring
            )
            contour_info['color'] = color
            print(f"[SVG生成] 轮廓#{i+1} ({contour_info['type']}): #{color['hex']}" +
                  (f" (环形采样)" if sample_ring else ""), flush=True)

        # 3. 获取裁剪坐标（用于SVG viewBox）
        padding = IMAGE_PROCESSING['default_padding']
        cropped_image, crop_coords = processor.crop_to_main_object(padding=padding)
        crop_x, crop_y, crop_w, crop_h = crop_coords

        # 4. 调整轮廓坐标到裁剪后的坐标系
        all_contours = []
        for contour_info in all_contours_original:
            x, y, w, h = contour_info['bounding_box']
            adjusted_x = x - crop_x
            adjusted_y = y - crop_y

            # 只保留在裁剪范围内的轮廓
            if (adjusted_x + w > 0 and adjusted_x < crop_w and
                adjusted_y + h > 0 and adjusted_y < crop_h):
                # 更新坐标
                contour_info['bounding_box'] = (adjusted_x, adjusted_y, w, h)
                # 调整轮廓points坐标
                adjusted_contour = contour_info['contour'].copy()
                adjusted_contour[:, 0, 0] -= crop_x  # X坐标
                adjusted_contour[:, 0, 1] -= crop_y  # Y坐标
                contour_info['contour'] = adjusted_contour
                all_contours.append(contour_info)

        print(f"[SVG生成] 裁剪后保留 {len(all_contours)} 个轮廓", flush=True)

        # 5. 生成SVG内容
        svg_shapes = []
        svg_texts = []  # 存储文字和图标元素

        # 按Y坐标排序，从上到下绘制
        all_contours_sorted = sorted(all_contours, key=lambda c: c['bounding_box'][1])

        # 用于识别按钮类型的辅助变量
        # 策略：排除最上方的按钮（圆形控制区内的白圈），只选择下方的2个按钮
        all_buttons = [c for c in all_contours_sorted if c['type'] == 'button']

        # 按Y坐标排序，跳过第一个（最上方的），选择后面的按钮
        buttons = all_buttons[1:] if len(all_buttons) > 2 else all_buttons

        print(f"[按钮识别] 总按钮数: {len(all_buttons)}, 筛选后: {len(buttons)}", flush=True)
        for i, btn in enumerate(buttons):
            x, y, w, h = btn['bounding_box']
            print(f"[按钮识别] 按钮{i}: 位置=({x},{y}), 尺寸={w}x{h}", flush=True)

        for contour_info in all_contours_sorted:
            contour_type = contour_info['type']
            color_hex = contour_info['color']['hex']
            x, y, w, h = contour_info['bounding_box']

            if contour_type == 'body':
                # 主体：使用规则矩形 + 动态圆角检测 + 渐变填充
                # 检测圆角半径（支持统一圆角和分段圆角）
                corner_info = processor.detect_corner_radius(contour_info)

                # 创建渐变定义（从左到右的金属质感）
                gradient_id = "bodyGradient"
                svg_shapes.insert(0,
                    f'  <defs>\n'
                    f'    <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="0%">\n'
                    f'      <stop offset="0%" style="stop-color:#{color_hex};stop-opacity:1" />\n'
                    f'      <stop offset="50%" style="stop-color:#ffffff;stop-opacity:0.3" />\n'
                    f'      <stop offset="100%" style="stop-color:#{color_hex};stop-opacity:1" />\n'
                    f'    </linearGradient>\n'
                    f'  </defs>'
                )

                # 根据检测结果选择渲染方式
                if corner_info['use_uniform']:
                    # 使用统一圆角的简单矩形
                    uniform_r = corner_info['uniform']
                    svg_shapes.append(
                        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                        f'rx="{uniform_r}" ry="{uniform_r}" '
                        f'fill="url(#{gradient_id})" />'
                    )
                    print(f"[主体渲染] 使用统一圆角: r={uniform_r}", flush=True)
                else:
                    # 使用分段圆角的path路径
                    corners = corner_info['corners']
                    r_tl = corners['top_left']
                    r_tr = corners['top_right']
                    r_bl = corners['bottom_left']
                    r_br = corners['bottom_right']

                    # 构建带四个不同圆角的路径
                    # 从左上角开始，顺时针绘制
                    path_d = (
                        f"M {x + r_tl},{y} "  # 移动到左上角弧线起点
                        f"L {x + w - r_tr},{y} "  # 上边线
                        f"Q {x + w},{y} {x + w},{y + r_tr} "  # 右上角圆弧
                        f"L {x + w},{y + h - r_br} "  # 右边线
                        f"Q {x + w},{y + h} {x + w - r_br},{y + h} "  # 右下角圆弧
                        f"L {x + r_bl},{y + h} "  # 下边线
                        f"Q {x},{y + h} {x},{y + h - r_bl} "  # 左下角圆弧
                        f"L {x},{y + r_tl} "  # 左边线
                        f"Q {x},{y} {x + r_tl},{y} Z"  # 左上角圆弧，闭合
                    )
                    svg_shapes.append(
                        f'  <path d="{path_d}" fill="url(#{gradient_id})" />'
                    )
                    print(f"[主体渲染] 使用分段圆角: tl={r_tl}, tr={r_tr}, bl={r_bl}, br={r_br}", flush=True)
            elif contour_type == 'circle_control':
                # 圆形控制区：使用圆形 + 径向渐变模拟立体感
                cx, cy = x + w // 2, y + h // 2
                r = min(w, h) // 2

                # 创建径向渐变定义（中心亮，边缘暗）
                gradient_id = "circleGradient"
                if '<defs>' not in svg_shapes[0]:
                    svg_shapes.insert(0, '  <defs>')

                # 在defs标签内插入渐变定义
                defs_content = (
                    f'    <radialGradient id="{gradient_id}">\n'
                    f'      <stop offset="30%" style="stop-color:#ffffff;stop-opacity:0.3" />\n'
                    f'      <stop offset="100%" style="stop-color:#{color_hex};stop-opacity:1" />\n'
                    f'    </radialGradient>'
                )

                # 找到defs位置并插入
                for i, shape in enumerate(svg_shapes):
                    if '</defs>' in shape:
                        svg_shapes[i] = shape.replace('</defs>', f'\n{defs_content}\n  </defs>')
                        break
                else:
                    # 如果没有找到closing defs标签，直接添加
                    svg_shapes.insert(1, defs_content)
                    svg_shapes.insert(2, '  </defs>')

                svg_shapes.append(
                    f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{gradient_id})" />'
                )
            elif contour_type == 'small_dot':
                # 小圆点：使用小圆形
                cx, cy = x + w // 2, y + h // 2
                r = min(w, h) // 2
                svg_shapes.append(
                    f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#{color_hex}" />'
                )
            elif contour_type == 'button':
                # 按钮：根据形状类型选择合适的SVG元素
                cx, cy = x + w // 2, y + h // 2
                r = min(w, h) // 2
                shape_type = contour_info.get('shape', 'circle')
                shadow_info = contour_info.get('shadow', {})

                # 根据检测到的阴影生成滤镜
                filter_id = None
                if shadow_info.get('has_inner_shadow') or shadow_info.get('has_outer_shadow'):
                    blur_radius = shadow_info.get('blur_radius', 2)

                    if shadow_info.get('has_inner_shadow'):
                        # 内阴影滤镜
                        filter_id = "innerShadow"
                        if not any(filter_id in shape for shape in svg_shapes):
                            strength = shadow_info.get('inner_strength', 0.5)
                            inner_shadow_filter = (
                                f'    <filter id="{filter_id}">\n'
                                f'      <feGaussianBlur in="SourceGraphic" stdDeviation="{blur_radius}" result="blur"/>\n'
                                f'      <feOffset in="blur" dx="0" dy="1" result="offset"/>\n'
                                f'      <feComposite in="offset" in2="SourceGraphic" operator="out" result="inverse"/>\n'
                                f'      <feFlood flood-color="black" flood-opacity="{strength}" result="color"/>\n'
                                f'      <feComposite in="color" in2="inverse" operator="in" result="shadow"/>\n'
                                f'      <feComposite in="shadow" in2="SourceGraphic" operator="over"/>\n'
                                f'    </filter>'
                            )
                            for i, shape in enumerate(svg_shapes):
                                if '</defs>' in shape:
                                    svg_shapes[i] = shape.replace('</defs>', f'\n{inner_shadow_filter}\n  </defs>')
                                    break

                    elif shadow_info.get('has_outer_shadow'):
                        # 外阴影滤镜（drop shadow）
                        filter_id = "outerShadow"
                        if not any(filter_id in shape for shape in svg_shapes):
                            strength = shadow_info.get('outer_strength', 0.5)
                            outer_shadow_filter = (
                                f'    <filter id="{filter_id}">\n'
                                f'      <feGaussianBlur in="SourceAlpha" stdDeviation="{blur_radius}"/>\n'
                                f'      <feOffset dx="0" dy="2" result="offsetblur"/>\n'
                                f'      <feComponentTransfer>\n'
                                f'        <feFuncA type="linear" slope="{strength}"/>\n'
                                f'      </feComponentTransfer>\n'
                                f'      <feMerge>\n'
                                f'        <feMergeNode/>\n'
                                f'        <feMergeNode in="SourceGraphic"/>\n'
                                f'      </feMerge>\n'
                                f'    </filter>'
                            )
                            for i, shape in enumerate(svg_shapes):
                                if '</defs>' in shape:
                                    svg_shapes[i] = shape.replace('</defs>', f'\n{outer_shadow_filter}\n  </defs>')
                                    break
                else:
                    # 没有检测到阴影，使用默认外阴影
                    filter_id = "buttonShadow"
                    if not any(filter_id in shape for shape in svg_shapes):
                        shadow_filter = (
                            f'    <filter id="{filter_id}">\n'
                            f'      <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>\n'
                            f'      <feOffset dx="0" dy="2" result="offsetblur"/>\n'
                            f'      <feComponentTransfer>\n'
                            f'        <feFuncA type="linear" slope="0.5"/>\n'
                            f'      </feComponentTransfer>\n'
                            f'      <feMerge>\n'
                            f'        <feMergeNode/>\n'
                            f'        <feMergeNode in="SourceGraphic"/>\n'
                            f'      </feMerge>\n'
                            f'    </filter>'
                        )
                        for i, shape in enumerate(svg_shapes):
                            if '</defs>' in shape:
                                svg_shapes[i] = shape.replace('</defs>', f'\n{shadow_filter}\n  </defs>')
                                break

                # 根据形状类型生成SVG
                if shape_type == 'cross':
                    # 十字形：使用路径
                    # 构建十字形路径（中心cx,cy，臂长r）
                    arm_width = r * 0.4  # 十字臂宽度
                    arm_length = r  # 十字臂长度
                    cross_path = (
                        f"M {cx - arm_width},{cy - arm_length} "
                        f"L {cx + arm_width},{cy - arm_length} "
                        f"L {cx + arm_width},{cy - arm_width} "
                        f"L {cx + arm_length},{cy - arm_width} "
                        f"L {cx + arm_length},{cy + arm_width} "
                        f"L {cx + arm_width},{cy + arm_width} "
                        f"L {cx + arm_width},{cy + arm_length} "
                        f"L {cx - arm_width},{cy + arm_length} "
                        f"L {cx - arm_width},{cy + arm_width} "
                        f"L {cx - arm_length},{cy + arm_width} "
                        f"L {cx - arm_length},{cy - arm_width} "
                        f"L {cx - arm_width},{cy - arm_width} Z"
                    )
                    filter_attr = f'filter="url(#{filter_id})"' if filter_id else ''
                    svg_shapes.append(
                        f'  <path d="{cross_path}" fill="#{color_hex}" {filter_attr} />'
                    )
                elif shape_type == 'rectangle':
                    # 矩形/方形（使用动态圆角检测）
                    corner_info = processor.detect_corner_radius(contour_info)
                    filter_attr = f'filter="url(#{filter_id})"' if filter_id else ''

                    # 按钮通常使用统一圆角，但也支持分段圆角
                    if corner_info['use_uniform']:
                        svg_shapes.append(
                            f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                            f'rx="{corner_info["uniform"]}" ry="{corner_info["uniform"]}" '
                            f'fill="#{color_hex}" {filter_attr} />'
                        )
                    else:
                        # 分段圆角path
                        corners = corner_info['corners']
                        r_tl = corners['top_left']
                        r_tr = corners['top_right']
                        r_bl = corners['bottom_left']
                        r_br = corners['bottom_right']

                        path_d = (
                            f"M {x + r_tl},{y} "
                            f"L {x + w - r_tr},{y} "
                            f"Q {x + w},{y} {x + w},{y + r_tr} "
                            f"L {x + w},{y + h - r_br} "
                            f"Q {x + w},{y + h} {x + w - r_br},{y + h} "
                            f"L {x + r_bl},{y + h} "
                            f"Q {x},{y + h} {x},{y + h - r_bl} "
                            f"L {x},{y + r_tl} "
                            f"Q {x},{y} {x + r_tl},{y} Z"
                        )
                        svg_shapes.append(
                            f'  <path d="{path_d}" fill="#{color_hex}" {filter_attr} />'
                        )
                elif shape_type == 'line':
                    # 线条（如 "-" 号）
                    # 使用矩形表示，但不添加圆角
                    filter_attr = f'filter="url(#{filter_id})"' if filter_id else ''
                    svg_shapes.append(
                        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                        f'fill="#{color_hex}" {filter_attr} />'
                    )
                elif shape_type == 'triangle':
                    # 三角形：使用轮廓近似
                    epsilon = 0.04 * cv2.arcLength(contour_info['contour'], True)
                    approx = cv2.approxPolyDP(contour_info['contour'], epsilon, True)
                    filter_attr = f'filter="url(#{filter_id})"' if filter_id else ''
                    if len(approx) == 3:
                        points = " ".join([f"{p[0][0]},{p[0][1]}" for p in approx])
                        svg_shapes.append(
                            f'  <polygon points="{points}" fill="#{color_hex}" {filter_attr} />'
                        )
                    else:
                        # 降级为圆形
                        svg_shapes.append(
                            f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#{color_hex}" {filter_attr} />'
                        )
                else:
                    # 默认：圆形或复杂形状
                    filter_attr = f'filter="url(#{filter_id})"' if filter_id else ''
                    svg_shapes.append(
                        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#{color_hex}" {filter_attr} />'
                    )

                # TODO: 集成OCR文字识别
                # 当检测到按钮上有文字时，自动提取并添加到SVG
                # 暂时移除硬编码的"MENU"和"播放/暂停"内容

        # 合并图形和文字/图标元素
        all_svg_elements = svg_shapes + svg_texts

        svg_content = f'''<svg width="{crop_w}" height="{crop_h}" viewBox="0 0 {crop_w} {crop_h}" xmlns="http://www.w3.org/2000/svg">
  <!-- 基于轮廓的SVG生成 -->
{chr(10).join(all_svg_elements)}
</svg>'''

        print(f"[基于轮廓的SVG生成] ========== 完成 ==========\n", flush=True)

        # 调试信息
        debug_info = {
            "方法": "基于轮廓检测",
            "检测到的轮廓数": len(all_contours_original),
            "绘制的轮廓数": len(all_contours),
            "SVG尺寸": f"{crop_w} x {crop_h}"
        }

        for i, c in enumerate(all_contours):
            debug_info[f"轮廓{i+1}"] = f"{c['type']} - #{c['color']['hex']}"

        return jsonify({
            "success": True,
            "svg": svg_content,
            "debug_info": debug_info
        })
    except Exception as e:
        import traceback
        print(f"[错误] {traceback.format_exc()}", flush=True)
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/generate_cropped_svg', methods=['POST'])
def generate_cropped_svg():
    """生成裁剪后的SVG"""
    try:
        # 初始化处理器
        processor = ImageProcessor(CURRENT_IMAGE_PATH)
        svg_generator = SVGGenerator()

        # 裁剪到主体对象
        padding = IMAGE_PROCESSING['default_padding']
        cropped_image, crop_coords = processor.crop_to_main_object(padding=padding)
        x, y, w, h = crop_coords

        # 更新处理器图像
        processor.original_image = cropped_image
        processor.processed_image = cropped_image

        # 在裁剪图像中检测主体（不需要额外边距）
        detection_result = processor.detect_main_object(padding=0)

        # 提取轮廓和矩形
        main_contour = detection_result['contour'] if detection_result else None
        padded_rect = detection_result['padded_rect'] if detection_result else None

        # 检测特征
        features = processor.detect_features()

        # 生成SVG（无裁剪偏移）
        svg_content = svg_generator.generate_svg(
            w, h, main_contour, features, padded_rect, crop_offset=(0, 0))

        # 调试信息
        debug_info = _prepare_crop_debug_info(x, y, w, h, main_contour, features)

        return jsonify({
            "success": True,
            "svg": svg_content,
            "debug_info": debug_info,
            "crop_info": {
                "x": x,
                "y": y,
                "width": w,
                "height": h
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/get_cropped_image', methods=['POST'])
def get_cropped_image():
    """获取裁剪后的图像"""
    try:
        # 初始化处理器
        processor = ImageProcessor(CURRENT_IMAGE_PATH)

        # 裁剪到主体对象
        padding = IMAGE_PROCESSING['default_padding']
        cropped_image, crop_coords = processor.crop_to_main_object(padding=padding)
        x, y, w, h = crop_coords

        # 编码为base64
        _, buffer = cv2.imencode('.jpg', cropped_image)
        img_str = base64.b64encode(buffer).decode()

        return jsonify({
            "success": True,
            "image_data": f"data:image/jpeg;base64,{img_str}",
            "crop_info": {
                "x": x,
                "y": y,
                "width": w,
                "height": h
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/detect_outline', methods=['POST'])
def detect_outline():
    """检测并返回所有轮廓信息"""
    try:
        # 初始化处理器
        processor = ImageProcessor(CURRENT_IMAGE_PATH)

        # 🔧 迭代3修复：先在原图检测，再裁剪并调整坐标
        # 1. 先在原图上检测所有轮廓
        all_contours_original = processor.detect_all_contours()

        # 2. 获取裁剪坐标
        padding = IMAGE_PROCESSING['default_padding']
        cropped_image, crop_coords = processor.crop_to_main_object(padding=padding)
        crop_x, crop_y, crop_w, crop_h = crop_coords

        # 3. 调整轮廓坐标到裁剪后的坐标系，并过滤掉范围外的轮廓
        all_contours = []
        for contour_info in all_contours_original:
            x, y, w, h = contour_info['bounding_box']
            # 调整坐标：减去裁剪偏移量
            adjusted_x = x - crop_x
            adjusted_y = y - crop_y

            # 过滤：只保留在裁剪范围内的轮廓（至少部分可见）
            if (adjusted_x + w > 0 and adjusted_x < crop_w and
                adjusted_y + h > 0 and adjusted_y < crop_h):
                # 更新轮廓坐标
                contour_info['bounding_box'] = (adjusted_x, adjusted_y, w, h)
                all_contours.append(contour_info)

        print(f"[轮廓调整] 原图检测到 {len(all_contours_original)} 个轮廓", flush=True)
        print(f"[轮廓调整] 裁剪后保留 {len(all_contours)} 个轮廓", flush=True)

        # 转换为前端可用的格式
        contour_list = []
        for c in all_contours:
            x, y, w, h = c['bounding_box']
            contour_list.append({
                'type': c['type'],
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'area': c['area'],
                'aspect_ratio': c['aspect_ratio'],
                'extent': c['extent'],
                'circularity': c['circularity']
            })

        # 调试信息
        type_counts = {}
        for c in all_contours:
            c_type = c['type']
            type_counts[c_type] = type_counts.get(c_type, 0) + 1

        debug_info = {
            "检测到的轮廓总数": len(all_contours),
            "轮廓类型统计": type_counts,
            "主要轮廓信息": [
                {
                    "类型": c['type'],
                    "位置": f"({c['bounding_box'][0]}, {c['bounding_box'][1]})",
                    "尺寸": f"{c['bounding_box'][2]}x{c['bounding_box'][3]}",
                    "面积": c["area"],
                    "宽高比": c["aspect_ratio"],
                    "填充度": c["extent"],
                    "圆度": c["circularity"]
                } for c in all_contours[:10]
            ]
        }

        return jsonify({
            "success": True,
            "contours": contour_list,
            "debug_info": debug_info
        })
    except Exception as e:
        import traceback
        print(f"[错误] {traceback.format_exc()}", flush=True)
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/upload_product_image', methods=['POST'])
def upload_product_image():
    """处理产品图片上传"""
    global CURRENT_IMAGE_PATH

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    try:
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })

        file = request.files['image']

        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })

        # 验证文件类型
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": "不支持的文件格式，仅支持 JPG、JPEG、PNG 格式"
            })

        if file:
            # 保存文件（带时间戳）
            timestamp = int(time.time())
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"product_{timestamp}.{ext}"
            file_path = os.path.join(UPLOADS_DIR, filename)
            file.save(file_path)

            # 更新当前使用的图像路径
            CURRENT_IMAGE_PATH = file_path

            return jsonify({
                "success": True,
                "path": f"static/uploads/{filename}",
                "message": "产品图片上传成功！"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/upload_debug_image', methods=['POST'])
def upload_debug_image():
    """处理调试图像上传"""
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    try:
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })

        file = request.files['image']

        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })

        # 验证文件类型
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": "不支持的文件格式，仅支持 JPG、JPEG、PNG 格式"
            })

        if file:
            # 保存文件（带时间戳）
            timestamp = int(time.time())
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"debug_upload_{timestamp}.{ext}"
            file_path = os.path.join(UPLOADS_DIR, filename)
            file.save(file_path)

            return jsonify({
                "success": True,
                "path": f"static/uploads/{filename}"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
