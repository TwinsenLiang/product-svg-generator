"""
Test script to compare contour detection before and after optimization
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from image_processor import ImageProcessor
import cv2

def main():
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
            
            # Save the result
            cv2.imwrite("optimized_contour_visualization.jpg", result_image)
            print("Optimized contour visualization saved as optimized_contour_visualization.jpg")
            print(f"Bounding rectangle: x={x}, y={y}, width={w}, height={h}")
            
            # Calculate and display statistics
            area = cv2.contourArea(main_contour)
            aspect_ratio = float(w) / h
            rect_area = w * h
            extent = float(area) / rect_area
            hull = cv2.convexHull(main_contour)
            hull_area = cv2.contourArea(hull)
            convexity = float(area) / hull_area if hull_area > 0 else 0
            
            print(f"Contour statistics:")
            print(f"  Area: {area:.1f}")
            print(f"  Aspect ratio: {aspect_ratio:.2f}")
            print(f"  Extent: {extent:.2f}")
            print(f"  Convexity: {convexity:.2f}")
        else:
            print("No main object detected.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()