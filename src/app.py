"""
Main Flask application for 产品SVG生成器
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask, render_template, jsonify, request
from image_processor import ImageProcessor
from svg_generator import SVGGenerator
import cv2
import base64
import io
import numpy as np

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['JSON_AS_ASCII'] = False  # Support Chinese characters in JSON responses

# Path to the test image (relative to project root)
IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "apple_remote_original.jpg")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/generate_svg', methods=['POST'])
def generate_svg():
    """Generate SVG from the image"""
    try:
        # Initialize processors
        processor = ImageProcessor(IMAGE_PATH)
        svg_generator = SVGGenerator()
        
        # Load the image
        original_image = processor.load_image()
        height, width = original_image.shape[:2]
        
        # Detect the main object with padding
        detection_result = processor.detect_main_object(padding=10)
        
        # Extract contour and padded rectangle
        main_contour = detection_result['contour'] if detection_result else None
        padded_rect = detection_result['padded_rect'] if detection_result else None
        
        # Detect features
        features = processor.detect_features()
        
        # Generate SVG
        svg_content = svg_generator.generate_svg(width, height, main_contour, features, padded_rect)
        
        # Prepare debug information
        debug_info = {
            "图像尺寸": f"{width}x{height}",
            "主体轮廓点数": len(main_contour) if main_contour is not None else 0,
            "检测到的特征数": len(features),
            "SVG生成状态": "成功",
            "主要特征信息": [
                {
                    "面积": f["area"],
                    "宽高比": f"{f['aspect_ratio']:.2f}" if 'aspect_ratio' in f else "N/A",
                    "填充度": f"{f['extent']:.2f}" if 'extent' in f else "N/A",
                    "圆度": f"{f['circularity']:.2f}" if 'circularity' in f else "N/A"
                } for f in features[:5]  # Show top 5 features
            ]
        }
        
        return jsonify({
            "success": True,
            "svg": svg_content,
            "debug_info": debug_info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/detect_outline', methods=['POST'])
def detect_outline():
    """Detect and return outline information"""
    try:
        # Initialize processor
        processor = ImageProcessor(IMAGE_PATH)
        
        # Load the image
        original_image = processor.load_image()
        
        # Detect the main object with padding
        detection_result = processor.detect_main_object(padding=10)
        
        # Extract contour and rectangles
        main_contour = detection_result['contour'] if detection_result else None
        original_rect = detection_result['original_rect'] if detection_result else None
        padded_rect = detection_result['padded_rect'] if detection_result else None
        
        # Convert contour points to a serializable format
        contour_points = []
        if main_contour is not None:
            for point in main_contour:
                contour_points.append([int(point[0][0]), int(point[0][1])])
        
        # Convert feature bounding boxes to a serializable format
        feature_boxes = []
        for feature in features:
            x, y, w, h = feature['bounding_box']
            feature_boxes.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'area': int(feature['area']),
                'aspect_ratio': round(feature.get('aspect_ratio', 0), 2),
                'extent': round(feature.get('extent', 0), 2),
                'circularity': round(feature.get('circularity', 0), 2)
            })
        
        # Prepare debug information
        debug_info = {
            "主体轮廓点数": len(contour_points),
            "检测到的特征数": len(feature_boxes),
            "主要特征信息": [
                {
                    "位置": f"({f['x']}, {f['y']})",
                    "尺寸": f"{f['width']}x{f['height']}",
                    "面积": f["area"],
                    "宽高比": f["aspect_ratio"],
                    "填充度": f["extent"],
                    "圆度": f["circularity"]
                } for f in feature_boxes[:5]  # Show top 5 features
            ]
        }
        
        return jsonify({
            "success": True,
            "contour": contour_points,
            "features": feature_boxes,
            "debug_info": debug_info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/upload_debug_image', methods=['POST'])
def upload_debug_image():
    """Handle debug image uploads"""
    try:
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "没有选择图片文件"
            })
        
        if file:
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Save the file with timestamp
            import time
            timestamp = int(time.time())
            filename = f"debug_upload_{timestamp}.jpg"
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)
            
            return jsonify({
                "success": True,
                "path": f"static/uploads/{filename}"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    # Copy the test image to the static images directory
    if not os.path.exists("static/images"):
        os.makedirs("static/images")
    
    if not os.path.exists("static/images/apple_remote_original.jpg"):
        import shutil
        shutil.copy("../apple_remote_original.jpg", "static/images/apple_remote_original.jpg")
    
    app.run(host='0.0.0.0', port=8000, debug=True)