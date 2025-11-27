"""
图像处理模块
"""
import cv2
import numpy as np
import os
from config import IMAGE_PROCESSING


class ImageProcessor:
    """图像处理器，负责图像加载、主体检测和特征提取"""

    def __init__(self, image_path):
        """
        初始化图像处理器

        Args:
            image_path: 图像文件路径
        """
        self.image_path = image_path
        self.original_image = None
        self.processed_image = None

        # 从配置加载参数
        self.min_area_ratio = IMAGE_PROCESSING['min_area_ratio']
        self.max_area_ratio = IMAGE_PROCESSING['max_area_ratio']
        self.gaussian_kernel = IMAGE_PROCESSING['gaussian_blur_kernel']
        self.morph_close_kernel = IMAGE_PROCESSING['morph_close_kernel']
        self.morph_open_kernel = IMAGE_PROCESSING['morph_open_kernel']
        
    def load_image(self):
        """
        加载图像文件

        Returns:
            加载的图像数组

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 无法加载图像
        """
        if not os.path.exists(self.image_path):
            raise FileNotFoundError(f"图像文件不存在: {self.image_path}")

        self.original_image = cv2.imread(self.image_path)
        if self.original_image is None:
            raise ValueError(f"无法加载图像: {self.image_path}")

        self.processed_image = self.original_image.copy()
        return self.original_image
    
    def crop_to_main_object(self, padding=10):
        """
        裁剪图像到主体对象

        Args:
            padding: 边距大小（像素）

        Returns:
            (cropped_image, (x, y, w, h)): 裁剪后的图像和裁剪坐标
        """
        if self.original_image is None:
            self.load_image()

        # 检测主体对象
        detection_result = self.detect_main_object(padding=padding)

        if detection_result is None:
            # 未检测到对象，返回原图
            h, w = self.original_image.shape[:2]
            return self.original_image, (0, 0, w, h)

        # 获取带边距的矩形坐标
        padded_rect = detection_result['padded_rect']
        x, y, w, h = padded_rect

        # 裁剪图像
        cropped_image = self.original_image[y:y+h, x:x+w]

        return cropped_image, (x, y, w, h)
    
    def detect_main_object(self, padding=10):
        """
        Detect the main object in the image using improved contour detection
        Returns the contour and padded bounding rectangle for better visualization
        """
        if self.original_image is None:
            self.load_image()
            
        # 转为灰度图
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)

        # 应用高斯模糊降噪
        blurred = cv2.GaussianBlur(gray, self.gaussian_kernel, 0)
        
        # Use Otsu's thresholding for better binary separation
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Invert the image if the background is darker than the object
        # This helps if the remote is dark against a light background
        if cv2.countNonZero(thresh) > thresh.size / 2:
            thresh = cv2.bitwise_not(thresh)
        
        # 形态学操作清理图像
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, self.morph_close_kernel)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, self.morph_open_kernel)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open)
        
        # Find contours - 使用 RETR_LIST 检测所有轮廓(包括内部按钮)
        contours, _ = cv2.findContours(morph, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # 根据面积和形状筛选轮廓
        valid_contours = []
        image_area = gray.shape[0] * gray.shape[1]
        min_area = image_area * self.min_area_ratio
        max_area = image_area * self.max_area_ratio
        
        print(f"Found {len(contours)} contours")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            print(f"Contour {i}: area = {area}")
            
            if min_area < area < max_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate aspect ratio
                aspect_ratio = float(w) / h
                
                # Calculate extent (ratio of contour area to bounding rectangle area)
                rect_area = w * h
                extent = float(area) / rect_area
                
                # Calculate convex hull ratio (how close to convex shape)
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                convexity = float(area) / hull_area if hull_area > 0 else 0
                
                print(f"  Bounding rect: x={x}, y={y}, w={w}, h={h}")
                print(f"  Aspect ratio: {aspect_ratio:.2f}, Extent: {extent:.2f}, Convexity: {convexity:.2f}")
                
                # Remote controls are typically:
                # 1. Rectangular shape with aspect ratio between 0.1 and 6.0
                # 2. Solid shape with extent > 0.3 (lowered to capture shadow areas)
                # 3. Convex or nearly convex shape with convexity > 0.6 (lowered)
                # 4. Large enough to be the main object
                if (0.1 <= aspect_ratio <= 6.0 and 
                    extent > 0.3 and 
                    convexity > 0.6 and
                    area > 3000):  # Minimum area lowered
                    valid_contours.append({
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'convexity': convexity,
                        'bounding_rect': (x, y, w, h)
                    })
                    print(f"  Added to valid contours")
        
        # Return the contour that best matches a remote control
        if len(valid_contours) > 0:
            # Score contours based on how well they match a remote control
            # Ideal remote control: aspect ratio ~ 0.25 (vertical), extent ~ 0.8, convexity ~ 1.0
            for contour_info in valid_contours:
                aspect_score = max(0, 1.0 - abs(contour_info['aspect_ratio'] - 0.25) / 0.25)  # Target 0.25
                extent_score = max(0, 1.0 - abs(contour_info['extent'] - 0.7) / 0.7)  # Target 0.7 (lowered)
                convexity_score = contour_info['convexity']  # Higher is better
                # Weighted score: aspect ratio (30%), extent (30%), convexity (40%)
                contour_info['score'] = (0.3 * aspect_score + 0.3 * extent_score + 0.4 * convexity_score)
            
            # Sort by score (highest first)
            valid_contours.sort(key=lambda x: x['score'], reverse=True)
            selected_contour = valid_contours[0]['contour']
            original_x, original_y, original_w, original_h = valid_contours[0]['bounding_rect']
            
            # Apply padding to the bounding rectangle
            img_height, img_width = self.original_image.shape[:2]
            padded_x = max(0, original_x - padding)
            padded_y = max(0, original_y - padding)
            padded_w = min(img_width - padded_x, original_w + 2 * padding)
            padded_h = min(img_height - padded_y, original_h + 2 * padding)
            
            # Store both original and padded rectangles
            result_info = {
                'contour': selected_contour,
                'original_rect': (original_x, original_y, original_w, original_h),
                'padded_rect': (padded_x, padded_y, padded_w, padded_h)
            }
            
            print(f"Selected contour with score: {valid_contours[0]['score']:.2f}")
            print(f"Original rect: ({original_x}, {original_y}, {original_w}, {original_h})")
            print(f"Padded rect: ({padded_x}, {padded_y}, {padded_w}, {padded_h})")
            
            # Post-process the contour to make it more rectangular and remove noise
            # Use a more conservative approximation to preserve corner details
            epsilon = 0.003 * cv2.arcLength(selected_contour, True)
            approximated_contour = cv2.approxPolyDP(selected_contour, epsilon, True)
            
            # If the approximated contour is too simple, use a less aggressive approximation
            if len(approximated_contour) < 4:
                epsilon = 0.001 * cv2.arcLength(selected_contour, True)
                approximated_contour = cv2.approxPolyDP(selected_contour, epsilon, True)
            
            result_info['contour'] = approximated_contour if len(approximated_contour) >= 4 else selected_contour
            return result_info
        
        # Fallback: try Canny edge detection with adjusted parameters
        edges = cv2.Canny(blurred, 20, 80)  # Even lower thresholds
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours again with looser criteria
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                rect_area = w * h
                extent = float(area) / rect_area if rect_area > 0 else 0
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                convexity = float(area) / hull_area if hull_area > 0 else 0
                
                # Even looser criteria for fallback
                if 0.1 <= aspect_ratio <= 8.0 and extent > 0.2 and convexity > 0.5:
                    valid_contours.append({
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'convexity': convexity,
                        'bounding_rect': (x, y, w, h)
                    })
        
        if len(valid_contours) > 0:
            # Score fallback contours
            for contour_info in valid_contours:
                aspect_score = max(0, 1.0 - abs(contour_info['aspect_ratio'] - 0.25) / 0.25)
                extent_score = max(0, 1.0 - abs(contour_info['extent'] - 0.6) / 0.6)  # Target 0.6
                convexity_score = contour_info['convexity']
                contour_info['score'] = (0.3 * aspect_score + 0.3 * extent_score + 0.4 * convexity_score)
            
            valid_contours.sort(key=lambda x: x['score'], reverse=True)
            selected_contour = valid_contours[0]['contour']
            original_x, original_y, original_w, original_h = valid_contours[0]['bounding_rect']
            
            # Apply padding to the bounding rectangle
            img_height, img_width = self.original_image.shape[:2]
            padded_x = max(0, original_x - padding)
            padded_y = max(0, original_y - padding)
            padded_w = min(img_width - padded_x, original_w + 2 * padding)
            padded_h = min(img_height - padded_y, original_h + 2 * padding)
            
            # Store both original and padded rectangles
            result_info = {
                'contour': selected_contour,
                'original_rect': (original_x, original_y, original_w, original_h),
                'padded_rect': (padded_x, padded_y, padded_w, padded_h)
            }
            
            print(f"Fallback: Selected contour with score: {valid_contours[0]['score']:.2f}")
            print(f"Original rect: ({original_x}, {original_y}, {original_w}, {original_h})")
            print(f"Padded rect: ({padded_x}, {padded_y}, {padded_w}, {padded_h})")
            
            # Post-process the fallback contour
            epsilon = 0.003 * cv2.arcLength(selected_contour, True)
            approximated_contour = cv2.approxPolyDP(selected_contour, epsilon, True)
            
            if len(approximated_contour) < 4:
                epsilon = 0.001 * cv2.arcLength(selected_contour, True)
                approximated_contour = cv2.approxPolyDP(selected_contour, epsilon, True)
            
            result_info['contour'] = approximated_contour if len(approximated_contour) >= 4 else selected_contour
            return result_info
        
        print("No suitable contour found")
        return None
            
    def detect_features(self):
        """
        Detect features like buttons and icons in the image using enhanced detection
        """
        if self.original_image is None:
            self.load_image()
            
        # Convert to grayscale
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and shape to find significant features
        features = []
        image_area = gray.shape[0] * gray.shape[1]
        min_area = image_area * 0.0001  # Minimum 0.01% of image area
        max_area = image_area * 0.02    # Maximum 2% of image area
        
        print(f"Found {len(contours)} potential features with Canny edge detection")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            # Debug print for first few candidates
            if i < 20:
                print(f"  Feature candidate {i}: area={area:.1f}")
            
            if min_area < area < max_area and area > 0:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate aspect ratio
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # Calculate extent (ratio of contour area to bounding rectangle area)
                rect_area = w * h
                extent = float(area) / rect_area if rect_area > 0 else 0
                
                # Debug print for first few candidates that pass area filter
                if len(features) < 10:
                    print(f"  Feature candidate {i}: area={area:.1f}, bbox=({x},{y},{w},{h}), "
                          f"aspect={aspect_ratio:.2f}, extent={extent:.2f}")
                
                # Accept features with reasonable characteristics
                if 0.01 < extent <= 1.0 and 0.01 < aspect_ratio < 100.0:
                    # Additional circularity check
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 0
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                    
                    # Accept features that meet basic criteria
                    features.append({
                        'contour': contour,
                        'bounding_box': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'circularity': circularity if perimeter > 0 else 0
                    })
                    if len(features) <= 5:  # Print first 5 accepted features
                        print(f"  Accepted feature: area={area:.1f}, aspect={aspect_ratio:.2f}, "
                              f"extent={extent:.2f}, circularity={circularity:.2f}")
                
        # Sort features by area (largest first)
        features.sort(key=lambda x: x['area'], reverse=True)
        print(f"Found {len(features)} valid features")
        
        # Limit to top 50 features to avoid overwhelming the SVG
        return features[:50]

    def detect_all_contours(self):
        """
        检测所有轮廓并分类（采用边缘卷积方法增强圆形检测）
        分类原则：1.先整体再局部 2.从上到下

        Returns:
            所有轮廓列表,包含类型分类
        """
        if self.original_image is None:
            self.load_image()

        # 转为灰度图
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)

        # 应用高斯模糊降噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # === 方法1: Otsu阈值检测主体 ===
        _, thresh_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if cv2.countNonZero(thresh_otsu) > thresh_otsu.size / 2:
            thresh_otsu = cv2.bitwise_not(thresh_otsu)

        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph_otsu = cv2.morphologyEx(thresh_otsu, cv2.MORPH_CLOSE, kernel_close)
        morph_otsu = cv2.morphologyEx(morph_otsu, cv2.MORPH_OPEN, kernel_open)

        # === 方法2: Canny边缘检测圆形区域（更敏感） ===
        edges = cv2.Canny(blurred, 30, 100)

        # 形态学操作连接边缘
        kernel_circle = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_circle, iterations=2)

        # 合并两种检测结果
        combined = cv2.bitwise_or(morph_otsu, edges_closed)

        # 检测所有轮廓
        contours, hierarchy = cv2.findContours(combined, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        all_contours = []
        image_area = gray.shape[0] * gray.shape[1]
        h_img, w_img = gray.shape

        print(f"[轮廓检测] 原始检测到 {len(contours)} 个轮廓", flush=True)

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # 过滤太小的噪点（降低阈值以检测小圆点）
            if area < 10:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0

            # 计算extent
            rect_area = w * h
            extent = float(area) / rect_area if rect_area > 0 else 0

            # 计算圆度 (4πA/P²)
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

            # 计算凸包比率
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            convexity = float(area) / hull_area if hull_area > 0 else 0

            # 计算中心位置（用于从上到下排序）
            M = cv2.moments(contour)
            cy = int(M['m01'] / M['m00']) if M['m00'] != 0 else y + h // 2

            # 🔍 调试：打印所有轮廓特征（降低阈值到100以便检测小点）
            if area > 100:
                print(f"[轮廓] 面积={int(area)}, 位置=({x},{y},{w},{h}), "
                      f"圆度={circularity:.2f}, 凸度={convexity:.2f}, "
                      f"宽高比={aspect_ratio:.2f}, center_y={cy}", flush=True)

            all_contours.append({
                'contour': contour,
                'type': 'unknown',  # 稍后分类
                'area': int(area),
                'bounding_box': (int(x), int(y), int(w), int(h)),
                'aspect_ratio': round(aspect_ratio, 2),
                'extent': round(extent, 2),
                'circularity': round(circularity, 2),
                'convexity': round(convexity, 2),
                'center_y': cy
            })

        # === 按照"先整体再局部，从上到下"原则分类 ===

        # 1. 先找主体（最大的轮廓）
        all_contours.sort(key=lambda c: c['area'], reverse=True)
        if len(all_contours) > 0:
            all_contours[0]['type'] = 'body'
            print(f"[轮廓分类] 主体: 面积={all_contours[0]['area']}, 位置={all_contours[0]['bounding_box']}", flush=True)

        # 2. 局部区域：圆形检测（支持大圆、中圆、小圆点）
        circular_regions = []
        small_dots = []  # 小圆点（面积 < 500）

        for c in all_contours[1:]:  # 跳过主体
            # 圆形判断条件：
            # - 宽高比接近1 (0.6-1.4)
            # - 圆度适中 (>0.4)
            # - 凸度高 (>0.75)
            is_circular = (
                0.6 <= c['aspect_ratio'] <= 1.4 and
                c['circularity'] > 0.4 and
                c['convexity'] > 0.75
            )

            if is_circular:
                # 区分小圆点和大/中圆形
                if c['area'] < 500:
                    small_dots.append(c)
                    c['type'] = 'small_dot'
                    print(f"[小圆点检测] 面积={c['area']}, 位置={c['bounding_box']}, "
                          f"圆度={c['circularity']:.2f}", flush=True)
                else:
                    circular_regions.append(c)
                    print(f"[圆形检测] 面积={c['area']}, 位置={c['bounding_box']}, "
                          f"圆度={c['circularity']:.2f}, 宽高比={c['aspect_ratio']:.2f}", flush=True)

        # 3. 分类圆形区域（基于面积和位置）
        if len(circular_regions) > 0:
            # 按面积排序，找到最大的圆形 = 控制区
            circular_regions.sort(key=lambda c: c['area'], reverse=True)

            # 最大的圆形 = 圆形控制区
            circular_regions[0]['type'] = 'circle_control'
            circle_control_bbox = circular_regions[0]['bounding_box']
            circle_x, circle_y, circle_w, circle_h = circle_control_bbox
            circle_center_x = circle_x + circle_w // 2
            circle_center_y = circle_y + circle_h // 2
            circle_radius = max(circle_w, circle_h) // 2

            print(f"[轮廓分类] 圆形控制区: 面积={circular_regions[0]['area']}, 位置={circle_control_bbox}, "
                  f"中心=({circle_center_x},{circle_center_y}), 半径={circle_radius}", flush=True)

            # 过滤小圆点：只保留在圆形控制区附近的（距离 < 半径*1.2 且不在主体最外边缘）
            # 获取主体边界用于边缘检测
            body_bbox = all_contours[0]['bounding_box']
            body_x, body_y, body_w, body_h = body_bbox
            edge_threshold = 15  # 距离主体边缘15px以内认为是边缘噪点（减小阈值）

            valid_small_dots = []
            for dot in small_dots:
                dot_x, dot_y, dot_w, dot_h = dot['bounding_box']
                dot_center_x = dot_x + dot_w // 2
                dot_center_y = dot_y + dot_h // 2

                # 计算点到圆心的距离
                distance = ((dot_center_x - circle_center_x) ** 2 +
                           (dot_center_y - circle_center_y) ** 2) ** 0.5

                # 检查是否在主体最外边缘（只检查左右边缘，因为上下边缘可能有有效点）
                is_near_edge = (
                    dot_center_x < body_x + edge_threshold or  # 左边缘
                    dot_center_x > body_x + body_w - edge_threshold  # 右边缘
                )

                # 保留条件：距离圆心近 且 不在边缘
                if distance < circle_radius * 1.2 and not is_near_edge:
                    valid_small_dots.append(dot)
                    print(f"[小圆点保留] 位置={dot['bounding_box']}, 距圆心={distance:.0f}px", flush=True)
                else:
                    dot['type'] = 'unknown'  # 标记为噪点
                    reason = "在边缘" if is_near_edge else f"距圆心{distance:.0f}px"
                    print(f"[小圆点过滤] 位置={dot['bounding_box']}, {reason} (噪点)", flush=True)

            # 剩余的圆形按从上到下排序 = 按钮
            buttons = circular_regions[1:]
            buttons.sort(key=lambda c: c['center_y'])

            for idx, btn in enumerate(buttons):
                btn['type'] = 'button'
                print(f"[轮廓分类] 按钮#{idx+1}: 面积={btn['area']}, 位置={btn['bounding_box']}", flush=True)

        # 过滤掉未分类的轮廓（包括噪点）
        all_contours = [c for c in all_contours if c['type'] != 'unknown']

        print(f"[轮廓检测] 最终分类: {len(all_contours)} 个有效轮廓", flush=True)
        return all_contours