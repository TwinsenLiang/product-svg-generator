"""
Test script to verify the new SVG generation functionality
"""
import requests
import json

def test_svg_generation():
    try:
        # Test the generate_svg endpoint
        response = requests.post('http://localhost:8000/generate_svg', json={})
        data = response.json()
        
        if data.get('success'):
            svg_content = data.get('svg', '')
            print("SVG Generation Test: PASSED")
            print(f"SVG Length: {len(svg_content)} characters")
            
            # Check if the SVG contains the expected elements
            if 'rect x="297" y="175"' in svg_content:
                print("✓ Correct positioning based on contour detection")
            if 'rx="' in svg_content and 'ry="' in svg_content:
                print("✓ Rounded corners (arc-shaped) included")
            if 'filter="url(#shadow)"' in svg_content:
                print("✓ Shadow effect included")
            if 'Main Remote Body based on detected shape' in svg_content:
                print("✓ Generated from detected contour")
                
            # Save the SVG to a file for visual inspection
            with open('generated_contour_svg.svg', 'w') as f:
                f.write(svg_content)
            print("SVG saved as 'generated_contour_svg.svg' for inspection")
            
        else:
            print("SVG Generation Test: FAILED")
            print(f"Error: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Test Error: {e}")

if __name__ == "__main__":
    test_svg_generation()