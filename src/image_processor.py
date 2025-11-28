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

        # === 策略1: Otsu阈值（检测主体） ===
        _, thresh_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Invert the image if the background is darker than the object
        if cv2.countNonZero(thresh_otsu) > thresh_otsu.size / 2:
            thresh_otsu = cv2.bitwise_not(thresh_otsu)

        # === 策略2: Canny边缘检测（只检测强边缘=产品边框，忽略阴影渐变） ===
        # 提高阈值,只捕获产品主体的强边缘,排除阴影等弱边缘
        edges = cv2.Canny(blurred, 50, 150)  # 从(20,80)提高到(50,150)

        # 膨胀边缘以连接断开的线条(减少iterations避免过度膨胀)
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges_dilated = cv2.dilate(edges, kernel_dilate, iterations=2)  # 从3降到2

        # === 合并两种策略的结果 ===
        combined = cv2.bitwise_or(thresh_otsu, edges_dilated)

        # 形态学操作清理图像
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, self.morph_close_kernel)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, self.morph_open_kernel)
        morph = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open)

        # Find contours - 使用 RETR_EXTERNAL 只检测外部轮廓（主体）
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
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
                
                # 产品通常满足：
                # 1. 宽高比在合理范围内 (0.1 - 6.0)
                # 2. 填充率较高 extent > 0.3
                # 3. 基本凸性 convexity > 0.5 (降低以支持有凸起的产品如 Game Boy)
                # 4. 面积足够大
                if (0.1 <= aspect_ratio <= 6.0 and
                    extent > 0.3 and
                    convexity > 0.5 and  # 从 0.6 降低到 0.5
                    area > 3000):
                    valid_contours.append({
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'convexity': convexity,
                        'bounding_rect': (x, y, w, h)
                    })
                    print(f"  Added to valid contours")
        
        # Return the contour that best matches the main product
        if len(valid_contours) > 0:
            # Score contours based on area, extent, and convexity (通用产品检测，不限定形状)
            # 优先选择面积最大、填充率高、凸度好的轮廓
            img_area = self.original_image.shape[0] * self.original_image.shape[1]

            for contour_info in valid_contours:
                # 面积分数：面积越大越好（相对于图片总面积）
                area_ratio = contour_info['area'] / img_area
                area_score = min(1.0, area_ratio * 5)  # 面积占20%以上得满分

                # Extent分数：填充率越高越好（目标0.8左右）
                extent_score = max(0, 1.0 - abs(contour_info['extent'] - 0.8) / 0.8)

                # 凸度分数：越接近1越好
                convexity_score = contour_info['convexity']

                # 加权评分：面积(50%) + extent(25%) + 凸度(25%)
                contour_info['score'] = (0.5 * area_score + 0.25 * extent_score + 0.25 * convexity_score)

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

            # 提取层级信息 (hierarchy格式: [next, previous, first_child, parent])
            h_info = hierarchy[0][i] if hierarchy is not None else [-1, -1, -1, -1]
            parent_idx = h_info[3]  # 父轮廓索引
            first_child_idx = h_info[2]  # 第一个子轮廓索引

            all_contours.append({
                'contour': contour,
                'type': 'unknown',  # 稍后分类
                'area': int(area),
                'bounding_box': (int(x), int(y), int(w), int(h)),
                'aspect_ratio': round(aspect_ratio, 2),
                'extent': round(extent, 2),
                'circularity': round(circularity, 2),
                'convexity': round(convexity, 2),
                'center_y': cy,
                'contour_id': i,  # 轮廓在原始列表中的索引
                'parent_id': parent_idx,  # 父轮廓索引(-1表示顶层)
                'first_child_id': first_child_idx,  # 第一个子轮廓索引(-1表示无子轮廓)
                'children': []  # 稍后填充子轮廓列表
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

        # === 构建父子关系(循环卷积矩阵的基础) ===
        # 创建contour_id到轮廓的映射
        contour_map = {c['contour_id']: c for c in all_contours}

        # 为每个轮廓填充children列表
        for contour_info in all_contours:
            parent_id = contour_info.get('parent_id', -1)
            if parent_id != -1 and parent_id in contour_map:
                # 将当前轮廓添加到父轮廓的children列表
                parent = contour_map[parent_id]
                parent['children'].append(contour_info)

        # 打印层级关系调试信息
        for contour_info in all_contours:
            if len(contour_info['children']) > 0:
                print(f"[层级关系] {contour_info['type']}: 有 {len(contour_info['children'])} 个子轮廓", flush=True)

        # 为每个轮廓添加形状分类和阴影检测
        for contour_info in all_contours:
            shape_type = self.classify_shape(contour_info)
            contour_info['shape'] = shape_type

            # 检测阴影（仅对按钮和主体进行检测）
            if contour_info['type'] in ['button', 'body', 'circle_control']:
                shadow_info = self.detect_shadow(contour_info)
                contour_info['shadow'] = shadow_info
                if shadow_info['has_inner_shadow'] or shadow_info['has_outer_shadow']:
                    print(f"[阴影检测] {contour_info['type']}: 内阴影={shadow_info['has_inner_shadow']}({shadow_info['inner_strength']}), 外阴影={shadow_info['has_outer_shadow']}({shadow_info['outer_strength']})", flush=True)

            print(f"[形状识别] {contour_info['type']}: {shape_type}", flush=True)

        print(f"[轮廓检测] 最终分类: {len(all_contours)} 个有效轮廓", flush=True)
        return all_contours

    def classify_shape(self, contour_info):
        """
        分类轮廓形状：circle(圆形), cross(十字), rectangle(矩形), triangle(三角形), line(线条), complex(复杂形状)

        Args:
            contour_info: 轮廓信息字典

        Returns:
            形状类型字符串
        """
        contour = contour_info['contour']
        circularity = contour_info.get('circularity', 0)
        aspect_ratio = contour_info.get('aspect_ratio', 0)
        extent = contour_info.get('extent', 0)
        contour_type = contour_info.get('type', 'unknown')

        # 0. 主体body始终视为矩形（产品外形都是规则矩形）
        if contour_type == 'body':
            return 'rectangle'

        # 1. 圆形判断：圆度 > 0.85（提高阈值，避免将方形误判为圆形）
        if circularity > 0.85:
            return 'circle'

        # 2. 近似多边形
        epsilon = 0.04 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        vertices = len(approx)

        # 3. 线条判断（如 "-" 号）：宽高比极端 + 面积小
        # 注意：只对小型button应用此规则，不对body应用
        if aspect_ratio > 3.0 or aspect_ratio < 0.33:
            if extent > 0.5:  # 填充率合理
                return 'line'

        # 4. 三角形判断
        if vertices == 3:
            return 'triangle'

        # 5. 矩形/正方形判断（放宽条件）
        if vertices == 4:
            # 检查是否接近矩形
            x, y, w, h = cv2.boundingRect(contour)
            rect_area = w * h
            contour_area = cv2.contourArea(contour)
            extent_calc = contour_area / rect_area if rect_area > 0 else 0

            if extent_calc > 0.75:  # 降低阈值从0.85到0.75
                return 'rectangle'

        # 6. 圆度在 0.6-0.85 之间 + 矩形特征 → 方形按钮
        if 0.6 < circularity < 0.85 and extent > 0.70:  # 降低到0.70
            # 检查是否为圆角矩形
            if 0.7 < aspect_ratio < 1.4:
                return 'rectangle'

        # 7. 十字形判断：检查凸缺陷
        hull = cv2.convexHull(contour, returnPoints=False)
        if len(hull) > 3 and len(contour) > 10:
            try:
                defects = cv2.convexityDefects(contour, hull)
                if defects is not None and len(defects) >= 4:
                    # 有4个或更多凸缺陷，可能是十字形
                    # 进一步检查：十字形的宽高比应该接近1
                    if 0.7 < aspect_ratio < 1.3:
                        # 检查凸度（十字形凸度较低，约0.6-0.8）
                        if 0.5 < contour_info.get('convexity', 1) < 0.85:
                            return 'cross'
            except:
                pass

        # 8. 复杂形状
        return 'complex'

    def detect_corner_radius(self, contour_info):
        """
        检测主体的圆角半径(支持动态检测和分段圆角)

        Args:
            contour_info: 轮廓信息字典

        Returns:
            dict: {
                'uniform': int,  # 统一圆角半径
                'corners': {     # 四个角的单独半径
                    'top_left': int,
                    'top_right': int,
                    'bottom_left': int,
                    'bottom_right': int
                },
                'use_uniform': bool  # 是否使用统一圆角
            }
        """
        x, y, w, h = contour_info['bounding_box']
        contour = contour_info.get('contour')

        # 如果没有轮廓信息,使用默认值
        if contour is None or len(contour) < 4:
            min_side = min(w, h)
            default_radius = max(5, min(int(min_side * 0.08), 50))
            return {
                'uniform': default_radius,
                'corners': {
                    'top_left': default_radius,
                    'top_right': default_radius,
                    'bottom_left': default_radius,
                    'bottom_right': default_radius
                },
                'use_uniform': True
            }

        # === 方案1:基于轮廓点分析四个角的曲率 ===
        # 定义四个角的区域(缩小到1/6宽高,更精确定位角部)
        corner_size = min(w // 6, h // 6)  # 使用更小的区域
        corner_regions = {
            'top_left': (x, y, x + corner_size, y + corner_size),
            'top_right': (x + w - corner_size, y, x + w, y + corner_size),
            'bottom_left': (x, y + h - corner_size, x + corner_size, y + h),
            'bottom_right': (x + w - corner_size, y + h - corner_size, x + w, y + h)
        }

        corner_radii = {}

        for corner_name, (x1, y1, x2, y2) in corner_regions.items():
            # 提取该角区域内的轮廓点
            corner_points = []
            for point in contour:
                px, py = point[0]
                if x1 <= px <= x2 and y1 <= py <= y2:
                    corner_points.append(point)

            if len(corner_points) < 5:  # 提高最低点数要求
                # 如果点太少,使用默认值
                radius = int(min(w, h) * 0.08)
            else:
                # 计算该角的近似圆角半径
                # 方法:拟合圆弧,计算半径
                try:
                    # 计算点到角点的距离,使用下四分位数(更保守)
                    corner_x = x1 if 'left' in corner_name else x2
                    corner_y = y1 if 'top' in corner_name else y2

                    distances = []
                    for point in corner_points:
                        px, py = point[0]
                        dist = np.sqrt((px - corner_x)**2 + (py - corner_y)**2)
                        distances.append(dist)

                    # 使用25%分位数(Q1)作为圆角半径,更稳健,避免异常值影响
                    if len(distances) > 0:
                        radius = int(np.percentile(distances, 25))
                    else:
                        radius = int(min(w, h) * 0.08)
                except:
                    radius = int(min(w, h) * 0.08)

            # 限制范围
            radius = max(5, min(radius, min(w, h) // 3))
            corner_radii[corner_name] = radius

            # 调试日志
            print(f"[圆角检测] {corner_name}: 轮廓点数={len(corner_points)}, 半径={radius}px", flush=True)

        # === 判断是否使用统一圆角 ===
        radii_values = list(corner_radii.values())
        avg_radius = int(np.mean(radii_values))
        std_radius = np.std(radii_values)

        # 如果标准差小于平均值的20%,认为圆角统一
        use_uniform = (std_radius < avg_radius * 0.2)

        print(f"[圆角检测] 平均半径={avg_radius}px, 标准差={std_radius:.1f}, 使用统一圆角={use_uniform}", flush=True)

        return {
            'uniform': avg_radius,
            'corners': corner_radii,
            'use_uniform': use_uniform
        }

    def detect_shadow(self, contour_info, sample_distance=10, num_samples=20):
        """
        基于规则矩形边界检测阴影效果（分方向：上下左右）

        Args:
            contour_info: 轮廓信息字典
            sample_distance: 采样距离（像素）
            num_samples: 每条边的采样点数量

        Returns:
            阴影属性字典 {
                'has_inner_shadow': bool,
                'has_outer_shadow': bool,
                'inner_strength': float (0-1),
                'outer_strength': float (0-1),
                'blur_radius': int,
                'direction_info': {  # 各方向详细信息
                    'top': {...},
                    'bottom': {...},
                    'left': {...},
                    'right': {...}
                }
            }
        """
        if self.original_image is None:
            self.load_image()

        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        x, y, w, h = contour_info['bounding_box']
        contour_type = contour_info.get('type', 'unknown')

        # 图像中心亮度（作为参考基准）
        img_h, img_w = gray.shape
        center_samples = []
        for _ in range(10):
            cx = np.random.randint(x + w//4, x + 3*w//4)
            cy = np.random.randint(y + h//4, y + 3*h//4)
            if 0 <= cx < img_w and 0 <= cy < img_h:
                center_samples.append(gray[cy, cx])
        center_brightness = np.mean(center_samples) if len(center_samples) > 0 else 128

        # 分方向检测
        direction_info = {}

        # === 上边 (Top) ===
        top_inner = []
        top_outer = []
        for i in range(num_samples):
            px = x + int(w * (i + 0.5) / num_samples)
            py = y
            # 向内采样
            if 0 <= px < img_w and 0 <= py + sample_distance < img_h:
                top_inner.append(gray[py + sample_distance, px])
            # 向外采样
            if 0 <= px < img_w and 0 <= py - sample_distance < img_h:
                top_outer.append(gray[py - sample_distance, px])

        direction_info['top'] = {
            'inner_avg': np.mean(top_inner) if len(top_inner) > 0 else center_brightness,
            'outer_avg': np.mean(top_outer) if len(top_outer) > 0 else center_brightness
        }

        # === 下边 (Bottom) ===
        bottom_inner = []
        bottom_outer = []
        for i in range(num_samples):
            px = x + int(w * (i + 0.5) / num_samples)
            py = y + h - 1
            # 向内采样
            if 0 <= px < img_w and 0 <= py - sample_distance < img_h:
                bottom_inner.append(gray[py - sample_distance, px])
            # 向外采样
            if 0 <= px < img_w and 0 <= py + sample_distance < img_h:
                bottom_outer.append(gray[py + sample_distance, px])

        direction_info['bottom'] = {
            'inner_avg': np.mean(bottom_inner) if len(bottom_inner) > 0 else center_brightness,
            'outer_avg': np.mean(bottom_outer) if len(bottom_outer) > 0 else center_brightness
        }

        # === 左边 (Left) ===
        left_inner = []
        left_outer = []
        for i in range(num_samples):
            px = x
            py = y + int(h * (i + 0.5) / num_samples)
            # 向内采样
            if 0 <= px + sample_distance < img_w and 0 <= py < img_h:
                left_inner.append(gray[py, px + sample_distance])
            # 向外采样
            if 0 <= px - sample_distance < img_w and 0 <= py < img_h:
                left_outer.append(gray[py, px - sample_distance])

        direction_info['left'] = {
            'inner_avg': np.mean(left_inner) if len(left_inner) > 0 else center_brightness,
            'outer_avg': np.mean(left_outer) if len(left_outer) > 0 else center_brightness
        }

        # === 右边 (Right) ===
        right_inner = []
        right_outer = []
        for i in range(num_samples):
            px = x + w - 1
            py = y + int(h * (i + 0.5) / num_samples)
            # 向内采样
            if 0 <= px - sample_distance < img_w and 0 <= py < img_h:
                right_inner.append(gray[py, px - sample_distance])
            # 向外采样
            if 0 <= px + sample_distance < img_w and 0 <= py < img_h:
                right_outer.append(gray[py, px + sample_distance])

        direction_info['right'] = {
            'inner_avg': np.mean(right_inner) if len(right_inner) > 0 else center_brightness,
            'outer_avg': np.mean(right_outer) if len(right_outer) > 0 else center_brightness
        }

        # === 综合判断 ===
        has_inner_shadow = False
        has_outer_shadow = False
        inner_strength = 0.0
        outer_strength = 0.0

        # 内阴影：边缘内侧比中心暗（排除左右边，因为可能是产品弧度）
        inner_darkness_list = []
        for direction in ['top', 'bottom']:  # 只检测上下边
            inner_avg = direction_info[direction]['inner_avg']
            if center_brightness - inner_avg > 10:  # 内侧比中心暗10+
                inner_darkness_list.append(center_brightness - inner_avg)

        if len(inner_darkness_list) > 0:
            has_inner_shadow = True
            inner_strength = min(1.0, np.mean(inner_darkness_list) / 50.0)

        # 外阴影：边缘外侧比背景暗（检测所有方向）
        outer_darkness_list = []
        for direction in ['top', 'bottom', 'left', 'right']:
            outer_avg = direction_info[direction]['outer_avg']
            # 外侧暗度 = 255 - 外侧亮度
            outer_darkness = 255 - outer_avg
            if outer_darkness > 30:  # 外侧暗度 > 30
                outer_darkness_list.append(outer_darkness)

        if len(outer_darkness_list) > 0:
            has_outer_shadow = True
            outer_strength = min(1.0, np.mean(outer_darkness_list) / 100.0)

        # 估算模糊半径
        blur_radius = int(2 + max(inner_strength, outer_strength) * 3)

        return {
            'has_inner_shadow': has_inner_shadow,
            'has_outer_shadow': has_outer_shadow,
            'inner_strength': round(inner_strength, 2),
            'outer_strength': round(outer_strength, 2),
            'blur_radius': blur_radius,
            'direction_info': direction_info
        }