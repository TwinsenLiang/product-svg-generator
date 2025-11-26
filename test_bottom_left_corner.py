"""
Test script to specifically check bottom-left corner detection
"""
import sys
import os
import cv2
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from image_processor import ImageProcessor

def test_bottom_left_corner():
    # Path to the test image
    image_path = os.path.join(os.path.dirname(__file__), "static", "images", "apple_remote_original.jpg")
    
    # Initialize the image processor
    processor = ImageProcessor(image_path)
    
    try:
        # Load the image
        original_image = processor.load_image()
        print(f"Image loaded successfully. Dimensions: {original_image.shape}")
        
        # Detect the main object
        main_contour = processor.detect_main_object()
        if main_contour is not None:
            print(f"Main object detected. Contour points: {len(main_contour)}")
            
            # Draw the contour on the image for visualization
            result_image = original_image.copy()
            cv2.drawContours(result_image, [main_contour], -1, (0, 255, 0), 2)
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(main_contour)
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            # Highlight the bottom-left corner area
            # Bottom-left region of interest
            corner_x = x
            corner_y = y + h - 50  # Last 50 pixels of the height
            corner_w = 50
            corner_h = 50
            cv2.rectangle(result_image, (corner_x, corner_y), (corner_x + corner_w, corner_y + corner_h), (0, 0, 255), 2)
            cv2.putText(result_image, "Bottom-Left Corner", (corner_x, corner_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # Save the result
            cv2.imwrite("bottom_left_corner_test.jpg", result_image)
            print("Bottom-left corner test visualization saved as bottom_left_corner_test.jpg")
            print(f"Bounding rectangle: x={x}, y={y}, width={w}, height={h}")
            print(f"Bottom-left corner region: ({corner_x}, {corner_y}) to ({corner_x + corner_w}, {corner_y + corner_h})")
            
            # Check if contour points include the bottom-left area
            contour_points = main_contour.reshape(-1, 2)
            bottom_left_points = [
                point for point in contour_points 
                if (corner_x <= point[0] <= corner_x + corner_w and 
                    corner_y <= point[1] <= corner_y + corner_h)
            ]
            
            print(f"Points in bottom-left corner region: {len(bottom_left_points)}")
            if len(bottom_left_points) > 0:
                print("Bottom-left corner is properly included in the contour")
            else:
                print("Warning: Bottom-left corner may not be properly included")
                
        else:
            print("No main object detected.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bottom_left_corner()