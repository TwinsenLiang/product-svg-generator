"""
Debug script for image detection
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from image_processor import ImageProcessor
import cv2

def main():
    # Path to the test image (relative to project root)
    image_path = os.path.join(os.path.dirname(__file__), "static", "images", "apple_remote_original.jpg")
    
    # Initialize the image processor
    processor = ImageProcessor(image_path)
    
    try:
        print("=== Debug Image Detection ===")
        # Load the image
        original_image = processor.load_image()
        height, width = original_image.shape[:2]
        print(f"Image loaded successfully. Dimensions: {width}x{height}")
        
        print("\n--- Detecting main object ---")
        # Detect the main object
        main_contour = processor.detect_main_object()
        if main_contour is not None:
            print(f"Main object detected. Contour points: {len(main_contour)}")
            # Print more details about the contour
            x, y, w, h = cv2.boundingRect(main_contour)
            print(f"Bounding rectangle: x={x}, y={y}, width={w}, height={h}")
        else:
            print("No main object detected.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()