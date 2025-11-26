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
    
    def detect_main_object(self):
        """
        Detect the main object in the image using improved contour detection
        """
        if self.original_image is None:
            self.load_image()
            
        # Convert to grayscale
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use Otsu's thresholding for better binary separation
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Invert the image if the background is darker than the object
        # This helps if the remote is dark against a light background
        if cv2.countNonZero(thresh) > thresh.size / 2:
            thresh = cv2.bitwise_not(thresh)
        
        # Morphological operations to clean up the image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and shape to find the main object
        valid_contours = []
        image_area = gray.shape[0] * gray.shape[1]
        min_area = image_area * 0.05  # Minimum 5% of image area
        max_area = image_area * 0.8  # Maximum 80% of image area
        
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
                
                print(f"  Bounding rect: x={x}, y={y}, w={w}, h={h}")
                print(f"  Aspect ratio: {aspect_ratio:.2f}, Extent: {extent:.2f}")
                
                # Check if this looks like a remote control
                # Remote controls can be either horizontal or vertical
                # and should have a solid shape (extent > 0.5)
                # We'll accept aspect ratios between 0.2 and 5.0
                if 0.2 <= aspect_ratio <= 5.0 and extent > 0.5:
                    valid_contours.append({
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'bounding_rect': (x, y, w, h)
                    })
                    print(f"  Added to valid contours")
        
        # Return the contour that best matches a remote control
        if len(valid_contours) > 0:
            # Sort by area (largest first) as a simple heuristic
            valid_contours.sort(key=lambda x: x['area'], reverse=True)
            print(f"Selected contour with area: {valid_contours[0]['area']}")
            return valid_contours[0]['contour']
        
        # Fallback: try Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours again
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                rect_area = w * h
                extent = float(area) / rect_area
                
                if 0.2 <= aspect_ratio <= 5.0 and extent > 0.3:
                    valid_contours.append({
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'bounding_rect': (x, y, w, h)
                    })
        
        if len(valid_contours) > 0:
            valid_contours.sort(key=lambda x: x['area'], reverse=True)
            print(f"Fallback: Selected contour with area: {valid_contours[0]['area']}")
            return valid_contours[0]['contour']
        
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