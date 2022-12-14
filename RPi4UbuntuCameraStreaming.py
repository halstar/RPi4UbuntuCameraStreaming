# Web streaming example working on a Raspberry Pi 4 with Ubuntu Mate 20.04
#
# We got a mix here of:
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming
# ...and...
# https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html

import os
import io
import sys
import cv2
import signal
import shutil
import logging
import socketserver
from http import server

PAGE="""\
<html>
<head>
</head>
<body>
<center><img src="stream.jpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        pass

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type'  , 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.jpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma'       , 'no-cache')
            self.send_header('Content-Type' , 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    ret, frame = camera.read()
                    cv2.imwrite('image.jpg', frame)
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.end_headers()
                    with open('image.jpg', 'rb') as content:
                        shutil.copyfileobj(content, self.wfile)
            except Exception as error:
                logging.warning(
                    'Removed streaming client: %s: %s',
                    self.client_address, str(error))
        else:
            self.send_error (404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads      = True

def cleanup():
    global camera

    if camera is not None:
        camera.release()

    if os.path.exists('image.jpg'):
        os.remove('image.jpg')

    logging.info('Exiting...')

    sys.exit(0)

def signalHandler(sig, frame):
    cleanup()

camera = None

signal.signal(signal.SIGINT, signalHandler)

# Open camera
camera = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L)

# Set dimensions
camera.set(cv2.CAP_PROP_FRAME_WIDTH , 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

output = StreamingOutput()

# Start streaming server
try:
    logging.getLogger().setLevel(logging.INFO)
    logging.info('Starting streaming server')
    address = ('', 8000)
    server  = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    cleanup()

