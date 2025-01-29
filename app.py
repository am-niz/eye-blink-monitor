from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import cv2
import uvicorn
from eye_cls_opn import process_frame, CHECK_INTERVAL, HEALTHY_BLINKS_PER_MINUTE, last_check_time, BLINK_COUNT
from time import time
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables
camera = None
is_monitoring = False
current_blink_count = 0
last_alert_sent = 0

def init_camera():
    global camera
    if camera is None:
        try:
            for index in range(-1, 2):
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    camera = cap
                    print(f"Successfully opened camera at index {index}")
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    return camera
            print("No camera found!")
        except Exception as e:
            print(f"Camera initialization error: {e}")
    return camera

def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None

def gen_frames():
    global current_blink_count, is_monitoring, last_alert_sent
    camera = init_camera()
    
    if camera is None:
        print("Failed to initialize camera")
        return

    while is_monitoring:
        try:
            success, frame = camera.read()
            if not success:
                print("Failed to read frame")
                break
            
            frame, blink_count, should_alert = process_frame(frame)
            current_blink_count = blink_count
            
            if should_alert:
                last_alert_sent = time()
            
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Failed to encode frame")
                continue
                
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error in gen_frames: {e}")
            break

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(gen_frames(), 
                           media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/start")
async def start_monitoring():
    global is_monitoring, last_check_time, current_blink_count, last_alert_sent
    is_monitoring = True
    last_check_time = time()
    current_blink_count = 0
    last_alert_sent = 0
    init_camera()
    return {"status": "started"}

@app.get("/api/stop")
async def stop_monitoring():
    global is_monitoring
    is_monitoring = False
    release_camera()
    return {"status": "stopped"}

@app.get("/api/blink-data")
async def get_blink_data():
    global last_alert_sent
    current_time = time()
    should_alert = (is_monitoring and 
                   last_alert_sent > 0 and
                   current_time - last_alert_sent < 1)
    
    if should_alert:
        last_alert_sent = 0
        
    return {
        "blink_count": current_blink_count,
        "blink_rate": current_blink_count,
        "should_alert": should_alert,
        "is_production": os.getenv("RENDER", "false") == "true"
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
