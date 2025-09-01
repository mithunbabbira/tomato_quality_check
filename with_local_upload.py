#!/usr/bin/env python3
from flask import Flask, Response, render_template_string, jsonify, request
from picamera2 import Picamera2
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
# Flask app + camera
# ---------------------------
app = Flask(__name__)
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

lock = threading.Lock()
last_frame = None

# Background thread to continuously grab frames
def capture_loop():
    global last_frame
    while True:
        frame = picam2.capture_array()
        with lock:
            last_frame = frame
        time.sleep(0.03)  # ~30 FPS

threading.Thread(target=capture_loop, daemon=True).start()

def gen_frames():
    global last_frame
    while True:
        with lock:
            if last_frame is None:
                continue
            frame = cv2.cvtColor(last_frame, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame)
            jpg = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')

@app.route('/')
def index():
    return render_template_string('''
    <html>
      <head>
        <title>Tomato Ripeness Analyzer</title>
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
        <h2>🍅 Live Tomato Stream</h2>
        <img src="/video" width="640" height="480"><br><br>

        <button onclick="processCamera()">Process Current Frame</button>
        <br><br>

        <h3>Or Upload an Image</h3>
        <input type="file" id="fileInput" accept="image/*">
        <button onclick="uploadImage()">Analyze Image</button>

        <div id="results" style="margin-top:20px;"></div>
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
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
