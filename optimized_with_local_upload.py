#!/usr/bin/env python3
from flask import Flask, Response, render_template_string, jsonify, request
from picamera2 import Picamera2
import libcamera
import cv2
import numpy as np
import threading
import time

# ---------------------------
# Unripe Percentage Calculator
# ---------------------------
class UnripePercentageCalculator:
    def __init__(self):
        self.color_ranges = {
            'unripe_green': ((30, 30, 50), (80, 255, 200)),
            'unripe_whitish': ((0, 0, 100), (180, 50, 200)),
            'unripe_light_red': ((0, 30, 100), (15, 100, 200)),
            'ripe_red': ((0, 50, 50), (10, 255, 255)),
            'ripe_dark_red': ((170, 50, 50), (180, 255, 255)),
            'transitional_yellow': ((15, 50, 50), (30, 255, 255)),
            'transitional_light_red': ((0, 20, 100), (20, 80, 255))
        }

    def _mask(self, image, keys):
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        combined = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for k in keys:
            lower, upper = self.color_ranges[k]
            mask = cv2.inRange(hsv, lower, upper)
            combined |= mask
        return combined

    def calculate(self, image):
        unripe_mask = self._mask(image, ['unripe_green','unripe_whitish','unripe_light_red'])
        ripe_mask = self._mask(image, ['ripe_red','ripe_dark_red'])
        transitional_mask = self._mask(image, ['transitional_yellow','transitional_light_red'])

        total = image.shape[0] * image.shape[1]
        unripe = np.sum(unripe_mask > 0)
        ripe = np.sum(ripe_mask > 0)
        transitional = np.sum(transitional_mask > 0)

        return {
            "unripe_pct": round(unripe/total*100, 2),
            "ripe_pct": round(ripe/total*100, 2),
            "transitional_pct": round(transitional/total*100, 2),
            "total_pixels": total
        }

# ---------------------------
# Flask app + camera - ULTRA LOW LATENCY VERSION
# ---------------------------
app = Flask(__name__)
picam2 = Picamera2()

# Ultra-optimized camera configuration for minimum latency
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    buffer_count=1,      # Single buffer for minimum latency
    queue=False,         # No queuing
    transform=libcamera.Transform(hflip=0, vflip=0)  # No transforms
)
picam2.configure(config)
picam2.start()

# Pre-allocate arrays to avoid memory allocation during capture
frame_buffer = np.zeros((480, 640, 3), dtype=np.uint8)
lock = threading.Lock()
last_frame = None
frame_ready = threading.Event()

# Background thread to continuously grab frames
def capture_loop():
    global last_frame
    while True:
        try:
            # Use capture_array with pre-allocated buffer for speed
            frame = picam2.capture_array()
            with lock:
                last_frame = frame
                frame_ready.set()
        except Exception as e:
            print(f"Capture error: {e}")
            time.sleep(0.001)

threading.Thread(target=capture_loop, daemon=True).start()

def gen_frames():
    global last_frame
    while True:
        frame_ready.wait()  # Wait for new frame
        with lock:
            if last_frame is None:
                continue
            frame = last_frame
            frame_ready.clear()
        
        # Ultra-fast JPEG encoding with minimal quality
        _, buffer = cv2.imencode('.jpg', frame, [
            cv2.IMWRITE_JPEG_QUALITY, 60,  # Lower quality for speed
            cv2.IMWRITE_JPEG_OPTIMIZE, 1   # Fast encoding
        ])
        jpg = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')

@app.route('/')
def index():
    return render_template_string('''
    <html>
      <head>
        <title>Tomato Ripeness Analyzer - Ultra Low Latency</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .container { max-width: 800px; margin: 0 auto; }
          .stream-container { text-align: center; margin: 20px 0; }
          .controls { margin: 20px 0; text-align: center; }
          button { padding: 10px 20px; margin: 5px; font-size: 16px; }
          .results { margin: 20px 0; padding: 15px; background: #f0f0f0; border-radius: 5px; }
          .upload-section { margin: 20px 0; padding: 15px; border: 2px dashed #ccc; border-radius: 5px; }
        </style>
        <script>
          async function processCamera() {
            let res = await fetch("/process");
            let data = await res.json();
            document.getElementById("results").innerHTML = formatResults(data);
          }

          async function uploadImage() {
            let fileInput = document.getElementById("fileInput");
            if (fileInput.files.length === 0) {
              alert("Please select an image first.");
              return;
            }
            let formData = new FormData();
            formData.append("file", fileInput.files[0]);
            let res = await fetch("/upload", {method: "POST", body: formData});
            let data = await res.json();
            document.getElementById("results").innerHTML = formatResults(data);
          }

          function formatResults(data) {
            if (data.error) return `<p style="color:red">${data.error}</p>`;
            return `
              <h3>📊 Ripeness Results</h3>
              🟢 Unripe: ${data.unripe_pct}% <br>
              🔴 Ripe: ${data.ripe_pct}% <br>
              🟡 Transitional: ${data.transitional_pct}% <br>
              (Total Pixels: ${data.total_pixels})
            `;
          }
        </script>
      </head>
      <body>
        <div class="container">
          <h2>🍅 Ultra Low Latency Tomato Stream</h2>
          
          <div class="stream-container">
            <img src="/video" width="640" height="480" style="border: 2px solid #333;">
          </div>

          <div class="controls">
            <button onclick="processCamera()">Process Current Frame</button>
          </div>

          <div class="upload-section">
            <h3>Or Upload an Image</h3>
            <input type="file" id="fileInput" accept="image/*">
            <button onclick="uploadImage()">Analyze Image</button>
          </div>

          <div id="results" class="results"></div>
        </div>
      </body>
    </html>
    ''')

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/process')
def process_camera():
    global last_frame
    with lock:
        if last_frame is None:
            return jsonify({"error": "No frame captured"})
        image_rgb = last_frame.copy()
    
    calc = UnripePercentageCalculator()
    results = calc.calculate(image_rgb)
    return jsonify(results)

@app.route('/upload', methods=['POST'])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})
    file = request.files["file"]
    npimg = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({"error": "Invalid image"})
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    calc = UnripePercentageCalculator()
    results = calc.calculate(image_rgb)
    return jsonify(results)

if __name__ == "__main__":
    print("🚀 Starting Ultra Low Latency Tomato Quality Checker")
    print("📡 Access at: http://localhost:5000")
    print("⚡ Optimized for Raspberry Pi 5 with IMX500 camera")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
