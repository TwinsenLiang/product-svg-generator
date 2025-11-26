"""
Image processing module for 产品SVG生成器
"""
import cv2
import numpy as np
from PIL import Image
import os

class ImageProcessor:
    def __init__(self, image_path):
        """
        Initialize the image processor with an image path
        """
        self.image_path = image_path
        self.original_image = None
        self.processed_image = None
        
    def load_image(self):
        """
        Load the image from the specified path
        """
        if not os.path.exists(self.image_path):
            raise FileNotFoundError(f"Image file not found: {self.image_path}")
        
        self.original_image = cv2.imread(self.image_path)
        if self.original_image is None:
            raise ValueError(f"Could not load image: {self.image_path}")
            
        self.processed_image = self.original_image.copy()
        return self.original_image
    
    def detect_main_object(self, padding=10):
        """
        Detect the main object in the image using improved contour detection
        Returns the contour and padded bounding rectangle for better visualization
        """
        if self.original_image is None:
            self.load_image()
            
        # Convert to grayscale
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise while preserving edges
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Use Otsu's thresholding for better binary separation
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Invert the image if the background is darker than the object
        # This helps if the remote is dark against a light background
        if cv2.countNonZero(thresh) > thresh.size / 2:
            thresh = cv2.bitwise_not(thresh)
        
        # Morphological operations to clean up the image
        # Use larger kernel for closing to fill gaps in the outline
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        # Use smaller kernel for opening to remove small noise
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and shape to find the main object
        valid_contours = []
        image_area = gray.shape[0] * gray.shape[1]
        # Adjust area requirements for better remote detection
        min_area = image_area * 0.03  # Minimum 3% of image area (lowered)
        max_area = image_area * 0.9   # Maximum 90% of image area (increased)
        
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