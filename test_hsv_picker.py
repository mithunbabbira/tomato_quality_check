#!/usr/bin/env python3
"""
Test script to demonstrate HSV color picker functionality
"""

import cv2
import numpy as np

def test_hsv_values():
    """Test HSV calculation on the test.jpg image"""
    try:
        # Load the test image
        image = cv2.imread('test.jpg')
        if image is None:
            print("❌ Could not load test.jpg")
            return
        
        print("✅ Successfully loaded test.jpg")
        print(f"Image dimensions: {image.shape[1]}x{image.shape[0]}")
        
        # Convert to HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Test a few sample points
        test_points = [
            (100, 100),  # Top-left area
            (image.shape[1]//2, image.shape[0]//2),  # Center
            (image.shape[1]-100, image.shape[0]-100)  # Bottom-right area
        ]
        
        print("\n🎨 Sample HSV values from test.jpg:")
        print("-" * 50)
        
        for i, (x, y) in enumerate(test_points):
            if x < image.shape[1] and y < image.shape[0]:
                bgr = image[y, x]
                hsv = hsv_image[y, x]
                
                print(f"Point {i+1} at ({x}, {y}):")
                print(f"  RGB: ({bgr[2]}, {bgr[1]}, {bgr[0]})")
                print(f"  HSV: ({hsv[0]}, {hsv[1]}, {hsv[2]})")
                print()
        
        print("💡 To use the interactive HSV picker:")
        print("   1. Run: python hsv_picker.py")
        print("   2. Open: http://localhost:5001")
        print("   3. Upload test.jpg and click on different areas")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_hsv_values()
