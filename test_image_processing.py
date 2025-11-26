"""
Test script for image processing functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from image_processor import ImageProcessor
import cv2

def main():
    # Path to the test image
    image_path = "../apple_remote_original.jpg"
    
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
            
            # Save the result
            cv2.imwrite("test_output_main_object.jpg", result_image)
            print("Main object detection result saved as test_output_main_object.jpg")
        else:
            print("No main object detected.")
            
        # Detect features
        features = processor.detect_features()
        print(f"Detected {len(features)} features.")
        
        if len(features) > 0:
            # Draw features on the image for visualization
            result_image = original_image.copy()
            for feature in features:
                x, y, w, h = feature['bounding_box']
                cv2.rectangle(result_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            # Save the result
            cv2.imwrite("test_output_features.jpg", result_image)
            print("Feature detection result saved as test_output_features.jpg")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()