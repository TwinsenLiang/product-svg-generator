"""
SVG generator module for 产品SVG生成器
"""
import cv2
import numpy as np

class SVGGenerator:
    def __init__(self):
        """
        Initialize the SVG generator
        """
        pass
    
    def simplify_contour(self, contour, epsilon_factor=0.01):
        """
        Simplify contour using Ramer-Douglas-Peucker algorithm
        """
        if len(contour) < 3:
            return contour
            
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        return simplified
    
    def contour_to_svg_path(self, contour):
        """
        Convert a contour to an SVG path with curve approximation
        """
        if len(contour) == 0:
            return ""
            
        # Simplify the contour for cleaner SVG
        simplified_contour = self.simplify_contour(contour, epsilon_factor=0.005)
        
        if len(simplified_contour) == 0:
            return ""
            
        # Start the path
        path_data = "M "
        
        # Add the first point
        first_point = simplified_contour[0][0]
        path_data += f"{first_point[0]},{first_point[1]} "
        
        # Add the remaining points
        for i in range(1, len(simplified_contour)):
            point = simplified_contour[i][0]
            path_data += f"L {point[0]},{point[1]} "
            
        # Close the path
        path_data += "Z"
        
        return path_data
    
    def generate_svg(self, width, height, main_contour=None, features=None):
        """
        Generate an SVG from the detected contours
        """
        svg_content = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
'''
        
        # Add main object if available
        if main_contour is not None:
            path_data = self.contour_to_svg_path(main_contour)
            if path_data:
                svg_content += f'  <path d="{path_data}" fill="none" stroke="black" stroke-width="2"/>\n'
        
        # Add features if available
        if features:
            for feature in features:
                x, y, w, h = feature['bounding_box']
                svg_content += f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="blue" stroke-width="1"/>\n'
        
        svg_content += '</svg>'
        
        return svg_content