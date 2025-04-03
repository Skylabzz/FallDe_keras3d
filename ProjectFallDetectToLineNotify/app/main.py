from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import threading
from . import stream
from . import models, crud, schemas
from .database import SessionLocal, engine
from typing import List

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

camera_threads = {}
camera_flags = {}

@app.post("/cameras/start")
def start_all_rtsp_streams(db: Session = Depends(get_db)):
    # stop_flags = []
    camera_threads.clear() 
    camera_flags.clear()

    cameras = crud.get_cameras(db)
    if not cameras:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")

    streaming_cameras = [camera for camera in cameras if camera.is_streaming]
    if not streaming_cameras:
        return {"message": "ไม่มีการสตรีมจากกล้องใดๆ"}

    # notification_message = "🎉 *โปรแกรมได้เริ่มการสตรีมจากกล้องทั้งหมด*"

    for camera in streaming_cameras:
        rtsp_url = camera.stream_url
        # line_message = f"กล้อง: {camera.camera_name}\nRTSP URL: {rtsp_url}\nโปรดตรวจสอบการเชื่อมต่อ"
  
        # stream.send_message_to_line(camera.line_token, line_message)

        stop_flag = threading.Event()
        camera_flags[camera.camera_name] = stop_flag

        thread = threading.Thread(target=stream.start_rtsp_stream, args=(
            rtsp_url, camera.camera_name, camera.line_token, camera.message, camera.room_name,
            camera.is_notification, camera_threads, stop_flag), daemon=True)

        camera_threads[camera.camera_name] = thread
        thread.start()

    # stream.send_message_to_line(camera.line_token, notification_message)
    return {"message": f"เริ่มการสตรีมจาก {len(streaming_cameras)} กล้อง"}


@app.post("/cameras/stop")
def stop_all_rtsp_streams():
    global camera_flags
    for camera_name, stop_flag in camera_flags.items():
        stop_flag.set()

    for camera_name, thread in camera_threads.items():
        thread.join()

    return {"message": "หยุดการสตรีมทั้งหมด"}

@app.get("/cameras/{camera_id}", response_model=schemas.Camera)
async def get_camera_by_id(camera_id: int, db: Session = Depends(get_db)):
    db_camera = crud.get_camera_by_id(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")
    return db_camera

@app.get("/cameras/", response_model=List[schemas.Camera])
def read_cameras(db: Session = Depends(get_db)):
    cameras = crud.get_cameras(db)
    return cameras

@app.post("/cameras/new", response_model=schemas.Camera)
def create_camera(camera: schemas.CameraCreate, db: Session = Depends(get_db)):
    db_camera = crud.create_camera(db=db, camera=camera)
    return db_camera

@app.put("/cameras/{camera_id}", response_model=schemas.Camera)
def update_camera(camera_id: int, camera: schemas.CameraCreate, db: Session = Depends(get_db)):
    db_camera = crud.update_camera(db=db, camera_id=camera_id, camera=camera)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")
    return db_camera

@app.delete("/cameras/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    db_camera = crud.delete_camera(db=db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")
    return {"message": "ลบกล้องเรียบร้อย"}

@app.patch("/cameras/{camera_id}/streaming")
def update_streaming_status(camera_id: int, status: bool, db: Session = Depends(get_db)):
    db_camera = crud.get_camera_by_id(db, camera_id)
    if not db_camera:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")
    
    db_camera.is_streaming = status
    db.commit()
    db.refresh(db_camera)
    return db_camera

@app.patch("/cameras/{camera_id}/notification")
def update_notification_status(camera_id: int, status: bool, db: Session = Depends(get_db)):
    db_camera = crud.get_camera_by_id(db, camera_id)
    if not db_camera:
        raise HTTPException(status_code=404, detail="ไม่พบกล้อง")

    db_camera.is_notification = status
    db.commit()
    db.refresh(db_camera)
    return db_camera

@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    return templates.TemplateResponse("homepage.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def get_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/manual", response_class=HTMLResponse)
async def get_guide_page(request: Request):
    return templates.TemplateResponse("manual.html", {"request": request})

@app.get("/ss17", response_class=HTMLResponse)
async def get_manual_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/homepage", response_class=HTMLResponse)
async def get_manual_page(request: Request):
    return templates.TemplateResponse("homepage.html", {"request": request})