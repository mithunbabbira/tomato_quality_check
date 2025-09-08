#!/usr/bin/env python3
"""
HSV Color Picker Tool
Allows users to upload an image and click on any coordinate to get HSV values
"""

from flask import Flask, render_template_string, request, jsonify
import cv2
import numpy as np
import os
import base64
from io import BytesIO

app = Flask(__name__)

# Store uploaded images in memory (in production, use proper file storage)
uploaded_images = {}

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle image upload and return base64 encoded image"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'})
        
        # Read image data
        file_data = file.read()
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Invalid image file'})
        
        # Generate unique ID for this image
        import uuid
        image_id = str(uuid.uuid4())
        
        # Store image in memory
        uploaded_images[image_id] = image
        
        # Convert to base64 for display
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'image_id': image_id,
            'image_data': image_base64,
            'dimensions': {
                'width': image.shape[1],
                'height': image.shape[0]
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'})

@app.route('/get_color', methods=['POST'])
def get_color_at_coordinate():
    """Get HSV and RGB values at specific coordinates"""
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        
        if image_id not in uploaded_images:
            return jsonify({'error': 'Image not found'})
        
        image = uploaded_images[image_id]
        
        # Check if coordinates are within image bounds
        if x < 0 or x >= image.shape[1] or y < 0 or y >= image.shape[0]:
            return jsonify({'error': 'Coordinates out of bounds'})
        
        # Get BGR values at the coordinate
        bgr_values = image[y, x]
        
        # Convert BGR to RGB
        rgb_values = [int(bgr_values[2]), int(bgr_values[1]), int(bgr_values[0])]
        
        # Convert BGR to HSV
        bgr_pixel = np.uint8([[bgr_values]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)
        hsv_values = [int(hsv_pixel[0][0][0]), int(hsv_pixel[0][0][1]), int(hsv_pixel[0][0][2])]
        
        return jsonify({
            'rgb': rgb_values,
            'hsv': hsv_values,
            'coordinates': {'x': x, 'y': y}
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting color: {str(e)}'})

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>HSV Color Picker Tool</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .upload-section {
                margin-bottom: 30px;
                padding: 20px;
                border: 2px dashed #ddd;
                border-radius: 10px;
                text-align: center;
            }
            .image-container {
                text-align: center;
                margin: 20px 0;
            }
            #uploadedImage {
                max-width: 100%;
                max-height: 600px;
                border: 2px solid #ddd;
                border-radius: 5px;
                cursor: crosshair;
            }
            .info-panel {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }
            .color-display {
                display: inline-block;
                width: 30px;
                height: 30px;
                border: 2px solid #333;
                border-radius: 50%;
                margin-right: 10px;
                vertical-align: middle;
            }
            .hsv-values {
                font-family: monospace;
                font-size: 16px;
                margin: 10px 0;
            }
            .coordinate-info {
                font-size: 14px;
                color: #666;
                margin: 5px 0;
            }
            .instructions {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .error {
                color: #d32f2f;
                background: #ffebee;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 HSV Color Picker Tool</h1>
            
            <div class="instructions">
                <h3>Instructions:</h3>
                <ol>
                    <li>Upload an image using the file input below</li>
                    <li>Click anywhere on the displayed image</li>
                    <li>View the HSV values and RGB color at that coordinate</li>
                    <li>Use this tool to fine-tune color ranges for your tomato quality checker</li>
                </ol>
            </div>

            <div class="upload-section">
                <h3>Upload Image</h3>
                <input type="file" id="imageInput" accept="image/*" onchange="uploadImage()">
                <p>Supported formats: JPG, PNG, BMP, TIFF</p>
            </div>

            <div id="imageContainer" class="image-container" style="display: none;">
                <img id="uploadedImage" onclick="getColorAtClick(event)" alt="Uploaded image">
            </div>

            <div id="colorInfo" class="info-panel" style="display: none;">
                <h3>Color Information</h3>
                <div id="colorDisplay"></div>
                <div id="coordinateInfo" class="coordinate-info"></div>
                <div id="hsvValues" class="hsv-values"></div>
            </div>

            <div id="errorMessage" class="error" style="display: none;"></div>
        </div>

        <script>
            let currentImageId = null;

            async function uploadImage() {
                const fileInput = document.getElementById('imageInput');
                const file = fileInput.files[0];
                
                if (!file) {
                    showError('Please select an image file.');
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    
                    if (result.error) {
                        showError(result.error);
                        return;
                    }

                    // Display the uploaded image
                    const imageContainer = document.getElementById('imageContainer');
                    const uploadedImage = document.getElementById('uploadedImage');
                    
                    uploadedImage.src = `data:image/jpeg;base64,${result.image_data}`;
                    currentImageId = result.image_id;
                    
                    imageContainer.style.display = 'block';
                    document.getElementById('colorInfo').style.display = 'none';
                    hideError();

                } catch (error) {
                    showError('Error uploading image: ' + error.message);
                }
            }

            async function getColorAtClick(event) {
                if (!currentImageId) {
                    showError('Please upload an image first.');
                    return;
                }

                const img = event.target;
                const rect = img.getBoundingClientRect();
                
                // Calculate click coordinates relative to the image
                const x = Math.round((event.clientX - rect.left) * (img.naturalWidth / img.clientWidth));
                const y = Math.round((event.clientY - rect.top) * (img.naturalHeight / img.clientHeight));

                try {
                    const response = await fetch('/get_color', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            image_id: currentImageId,
                            x: x,
                            y: y
                        })
                    });

                    const result = await response.json();
                    
                    if (result.error) {
                        showError(result.error);
                        return;
                    }

                    displayColorInfo(result, x, y);
                    hideError();

                } catch (error) {
                    showError('Error getting color information: ' + error.message);
                }
            }

            function displayColorInfo(colorData, x, y) {
                const colorInfo = document.getElementById('colorInfo');
                const colorDisplay = document.getElementById('colorDisplay');
                const coordinateInfo = document.getElementById('coordinateInfo');
                const hsvValues = document.getElementById('hsvValues');

                // Display color swatch
                const rgbColor = `rgb(${colorData.rgb[0]}, ${colorData.rgb[1]}, ${colorData.rgb[2]})`;
                colorDisplay.innerHTML = `
                    <div class="color-display" style="background-color: ${rgbColor}"></div>
                    <strong>RGB: (${colorData.rgb[0]}, ${colorData.rgb[1]}, ${colorData.rgb[2]})</strong>
                `;

                // Display coordinates
                coordinateInfo.innerHTML = `Clicked at: (${x}, ${y})`;

                // Display HSV values
                hsvValues.innerHTML = `
                    <strong>HSV Values:</strong><br>
                    <strong>H (Hue):</strong> ${colorData.hsv[0]}°<br>
                    <strong>S (Saturation):</strong> ${colorData.hsv[1]}<br>
                    <strong>V (Value):</strong> ${colorData.hsv[2]}<br><br>
                    <strong>For OpenCV color ranges:</strong><br>
                    <code>lower: (${colorData.hsv[0]}, ${colorData.hsv[1]}, ${colorData.hsv[2]})</code><br>
                    <code>upper: (${colorData.hsv[0]}, 255, 255)</code>
                `;

                colorInfo.style.display = 'block';
            }

            function showError(message) {
                const errorDiv = document.getElementById('errorMessage');
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
            }

            function hideError() {
                document.getElementById('errorMessage').style.display = 'none';
            }
        </script>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    print("🎨 HSV Color Picker Tool")
    print("Access the tool at: http://localhost:5001")
    print("Upload an image and click on any coordinate to get HSV values!")
    app.run(host='0.0.0.0', port=5001, debug=True)
