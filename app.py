from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)
picam2 = Picamera2()

# Configure camera for preview (640x480 to keep it light)
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        frame = picam2.capture_array()
        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        # Yield as multipart stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '''
    <html>
      <head><title>Raspberry Pi AI Camera Stream</title></head>
      <body>
        <h2>Live Camera Stream</h2>
        <img src="/video" width="640" height="480">
      </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
