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
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Morphological operations to clean up the image
        kernel = np.ones((5,5), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort contours by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Return the largest contour as the main object
        if len(contours) > 0:
            # Filter out very small contours
            largest_area = cv2.contourArea(contours[0])
            if largest_area > 1000:  # Minimum area threshold
                return contours[0]
        
        # If no large contour found, try Canny edge detection as fallback
        edges = cv2.Canny(filtered, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        if len(contours) > 0:
            return contours[0]
            
        return None
            
    def detect_features(self):
        """
        Detect features like buttons and icons in the image using enhanced detection
        """
        if self.original_image is None:
            self.load_image()
            
        # Convert to grayscale
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Morphological operations to clean up the image
        kernel = np.ones((3,3), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and shape to find significant features
        features = []
        min_area = 50  # Minimum area for a feature
        max_area = 3000  # Maximum area for a feature
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate aspect ratio
                aspect_ratio = float(w) / h
                
                # Calculate extent (ratio of contour area to bounding rectangle area)
                rect_area = w * h
                extent = float(area) / rect_area
                
                # Filter based on shape characteristics
                # Buttons and icons often have specific aspect ratios and extents
                if 0.01 < extent < 0.9 and 0.2 < aspect_ratio < 5.0:
                    # Additional circularity check for round buttons
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        # Circularity range for round buttons (0=perfect circle, 1=line)
                        if circularity > 0.3 or (0.8 < aspect_ratio < 1.2 and extent > 0.7):
                            features.append({
                                'contour': contour,
                                'bounding_box': (x, y, w, h),
                                'area': area,
                                'aspect_ratio': aspect_ratio,
                                'extent': extent,
                                'circularity': circularity if perimeter > 0 else 0
                            })
                
        # Sort features by area (largest first)
        features.sort(key=lambda x: x['area'], reverse=True)
        
        return features