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
        # If we have a main contour, use it to create a more accurate remote control shape
        if main_contour is not None and len(main_contour) >= 4:
            # Get bounding rectangle of the contour
            import cv2
            x, y, w, h = cv2.boundingRect(main_contour)
            
            # Calculate rounded corners based on the actual contour
            # For a remote control, we typically want moderate rounding
            rx = min(30, w // 10)  # Radius X, max 30px
            ry = min(30, h // 20)  # Radius Y, max 30px
            
            # Create SVG with rounded rectangle that matches the detected contour
            svg_content = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Remote Control Body based on detected contour -->
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
      <feOffset dx="3" dy="3" result="offsetblur"/>
      <feFlood flood-color="rgba(0,0,0,0.3)"/>
      <feComposite in2="offsetblur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Main Remote Body based on detected shape -->
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="#333" stroke="#000" stroke-width="2" filter="url(#shadow)"/>
  
  <!-- Center indicator line -->
  <line x1="{x + w//2}" y1="{y}" x2="{x + w//2}" y2="{y + h}" stroke="#555" stroke-width="1" stroke-dasharray="5,5"/>
</svg>'''
        else:
            # Fallback to default template if no contour detected
            svg_content = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Default Remote Control Body -->
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
      <feOffset dx="3" dy="3" result="offsetblur"/>
      <feFlood flood-color="rgba(0,0,0,0.3)"/>
      <feComposite in2="offsetblur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Default Main Remote Body -->
  <rect x="320" y="200" width="320" height="880" rx="20" ry="20" fill="#333" stroke="#000" stroke-width="2" filter="url(#shadow)"/>
</svg>'''
        
        return svg_content