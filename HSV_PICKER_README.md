# 🎨 HSV Color Picker Tool

A web-based tool for analyzing HSV color values at specific coordinates in uploaded images. Perfect for fine-tuning color ranges in computer vision applications like the tomato quality checker.

## Features

- **Image Upload**: Support for JPG, PNG, BMP, TIFF formats
- **Interactive Clicking**: Click anywhere on the image to get HSV values
- **Real-time Display**: Shows RGB and HSV values with color swatch
- **Coordinate Mapping**: Accurate coordinate-to-pixel mapping
- **OpenCV Integration**: Direct HSV calculation using OpenCV

## Installation

```bash
# Install dependencies
pip install -r requirements_hsv_picker.txt
```

## Usage

### 1. Start the HSV Picker Tool
```bash
python hsv_picker.py
```

### 2. Access the Web Interface
Open your browser and go to: `http://localhost:5001`

### 3. Upload and Analyze
1. Click "Choose File" and select an image
2. Click anywhere on the displayed image
3. View the HSV values and RGB color at that coordinate

## API Endpoints

### `POST /upload`
Upload an image file
- **Input**: Multipart form data with image file
- **Output**: JSON with image_id and base64 encoded image

### `POST /get_color`
Get color values at specific coordinates
- **Input**: JSON with image_id, x, y coordinates
- **Output**: JSON with RGB and HSV values

## Example Usage

```python
# Test with your existing test.jpg
python test_hsv_picker.py
```

## Use Cases

- **Color Range Tuning**: Perfect for adjusting HSV ranges in your tomato quality checker
- **Debugging**: Understand why certain pixels are/aren't detected
- **Research**: Analyze color distributions in images
- **Education**: Learn about HSV color space

## Integration with Tomato Quality Checker

Use this tool to fine-tune the color ranges in your `UnripePercentageCalculator`:

```python
# Example: After clicking on a green tomato area
# You might get HSV values like: (60, 150, 200)
# Use these to adjust your color ranges:

'unripe_green': ((30, 30, 50), (80, 255, 200))  # Adjust based on your findings
```

## Technical Details

- **Port**: 5001 (different from main tomato checker)
- **Image Storage**: In-memory (resets on restart)
- **Coordinate System**: Top-left origin (0,0)
- **Color Space**: BGR → HSV conversion using OpenCV

## Troubleshooting

- **Image not loading**: Check file format (JPG, PNG, BMP, TIFF supported)
- **Coordinates out of bounds**: Click within the image boundaries
- **Port conflict**: Change port in `hsv_picker.py` if 5001 is occupied
