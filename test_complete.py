"""
Complete test script for Auto SVG Generator
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from image_processor import ImageProcessor
from svg_generator import SVGGenerator
import cv2

def main():
    # Path to the test image
    image_path = "static/images/apple_remote_original.jpg"
    
    # Initialize the image processor
    processor = ImageProcessor(image_path)
    
    try:
        print("Loading image...")
        # Load the image
        original_image = processor.load_image()
        height, width = original_image.shape[:2]
        print(f"Image loaded successfully. Dimensions: {width}x{height}")
        
        print("Detecting main object...")
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
            
        print("Detecting features...")
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
        
        print("Generating SVG...")
        # Initialize SVG generator
        svg_generator = SVGGenerator()
        
        # Generate SVG
        svg_content = svg_generator.generate_svg(width, height, main_contour, features)
        
        # Save SVG to file
        with open("test_output.svg", "w") as f:
            f.write(svg_content)
        print("SVG generated and saved as test_output.svg")
        
        print("Testing completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()