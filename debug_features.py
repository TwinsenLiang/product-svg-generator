"""
Debug script for feature detection
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
        print("=== Debug Feature Detection ===")
        # Load the image
        original_image = processor.load_image()
        height, width = original_image.shape[:2]
        print(f"Image loaded successfully. Dimensions: {width}x{height}")
        
        print("\n--- Detecting features ---")
        # Detect features
        features = processor.detect_features()
        print(f"Detected {len(features)} features.")
        
        # Draw features on the image for visualization
        if len(features) > 0:
            result_image = original_image.copy()
            for i, feature in enumerate(features[:10]):  # Only draw first 10 features
                x, y, w, h = feature['bounding_box']
                cv2.rectangle(result_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
                print(f"Feature {i}: bbox=({x},{y},{w},{h}), area={feature['area']:.1f}, "
                      f"aspect={feature['aspect_ratio']:.2f}, extent={feature['extent']:.2f}")
            
            # Save the result
            cv2.imwrite("test_output_features_debug.jpg", result_image)
            print("Feature detection result saved as test_output_features_debug.jpg")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()