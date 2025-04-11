import threading
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import List
from sqlalchemy.pool import NullPool

from app import stream

SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:@localhost:3306/predict_camera"

engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Room(Base):
    __tablename__ = "room"

    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String(100), unique=True, index=True)

    cameras = relationship("Camera", back_populates="room", cascade="all, delete-orphan")

class LineToken(Base):
    __tablename__ = "line_token"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True)

    cameras = relationship("Camera", back_populates="line_token_obj")

class MessageTemplate(Base):
    __tablename__ = "message_template"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(255), unique=True)

    cameras = relationship("Camera", back_populates="message_obj")


class Camera(Base):
    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String(100), index=True)
    stream_url = Column(String(255), unique=True)

    room_id = Column(Integer, ForeignKey("room.id", ondelete="CASCADE", onupdate="CASCADE"))
    room = relationship("Room", back_populates="cameras")

    message_id = Column(Integer, ForeignKey("message_template.id", ondelete="SET NULL", onupdate="CASCADE"))
    message_obj = relationship("MessageTemplate", back_populates="cameras")

    line_token_id = Column(Integer, ForeignKey("line_token.id", ondelete="SET NULL", onupdate="CASCADE"))
    line_token_obj = relationship("LineToken", back_populates="cameras")

    is_streaming = Column(Boolean, default=True)
    is_notification = Column(Boolean, default=True)


app = FastAPI()

class RoomCreate(BaseModel):
    room_name: str

class LineTokenCreate(BaseModel):
    token: str

class MessageTemplateCreate(BaseModel):
    content: str

class CameraCreate(BaseModel):
    camera_name: str
    stream_url: str
    room_id: int
    message_id: int = None
    line_token_id: int = None
    is_streaming: bool = True
    is_notification: bool = True

class CameraUpdateWithDetails(BaseModel):
    camera_name: str
    stream_url: str
    is_streaming: bool
    is_notification: bool
    room_name: str
    message: str
    line_token: str

class CameraDetail(BaseModel):
    id: int
    camera_name: str
    stream_url: str
    is_streaming: bool
    is_notification: bool
    room_name: str
    message: str = None
    line_token: str = None

    class Config:
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/rooms/", response_model=RoomCreate)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    db_room = db.query(Room).filter(Room.room_name == room.room_name).first()
    if db_room:
        raise HTTPException(status_code=400, detail="Room already exists")

    db_room = Room(room_name=room.room_name)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@app.get("/rooms/", response_model=List[RoomCreate])
def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()

@app.get("/rooms/{room_name}", response_model=RoomCreate)
def get_room_by_name(room_name: str, db: Session = Depends(get_db)):
    db_room = db.query(Room).filter(Room.room_name == room_name).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room

@app.put("/rooms/{room_id}", response_model=RoomCreate)
def update_room(room_id: int, room: RoomCreate, db: Session = Depends(get_db)):

    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    db_room.room_name = room.room_name
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@app.delete("/rooms/{room_id}", response_model=RoomCreate)
def delete_room(room_id: int, db: Session = Depends(get_db)):

    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    db.delete(db_room)
    db.commit()
    return db_room

@app.post("/message_templates/", response_model=MessageTemplateCreate)
def create_message_template(message_template: MessageTemplateCreate, db: Session = Depends(get_db)):

    db_message = db.query(MessageTemplate).filter(MessageTemplate.content == message_template.content).first()
    if db_message:
        raise HTTPException(status_code=400, detail="Message template already exists")
 
    db_message_template = MessageTemplate(content=message_template.content)
    db.add(db_message_template)
    db.commit()
    db.refresh(db_message_template)
    return db_message_template

@app.get("/message_templates/", response_model=List[MessageTemplateCreate])
def get_message_templates(db: Session = Depends(get_db)):
    return db.query(MessageTemplate).all()

@app.get("/message_templates/{template_id}", response_model=MessageTemplateCreate)
def get_message_template(template_id: int, db: Session = Depends(get_db)):
    db_message_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_message_template:
        raise HTTPException(status_code=404, detail="Message template not found")
    return db_message_template

@app.put("/message_templates/{template_id}", response_model=MessageTemplateCreate)
def update_message_template(template_id: int, message_template: MessageTemplateCreate, db: Session = Depends(get_db)):
    db_message_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_message_template:
        raise HTTPException(status_code=404, detail="Message template not found")

    db_message_template.content = message_template.content
    db.add(db_message_template)
    db.commit()
    db.refresh(db_message_template)
    return db_message_template

@app.delete("/message_templates/{template_id}", response_model=MessageTemplateCreate)
def delete_message_template(template_id: int, db: Session = Depends(get_db)):
    db_message_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_message_template:
        raise HTTPException(status_code=404, detail="Message template not found")

    db.delete(db_message_template)
    db.commit()
    return db_message_template

@app.post("/line_tokens/", response_model=LineTokenCreate)
def create_line_token(line_token: LineTokenCreate, db: Session = Depends(get_db)):
    db_token = db.query(LineToken).filter(LineToken.token == line_token.token).first()
    if db_token:
        raise HTTPException(status_code=400, detail="Token already exists")

    db_line_token = LineToken(token=line_token.token)
    db.add(db_line_token)
    db.commit()
    db.refresh(db_line_token)
    return db_line_token

@app.get("/line_tokens/", response_model=List[LineTokenCreate])
def get_line_tokens(db: Session = Depends(get_db)):
    return db.query(LineToken).all()

@app.get("/line_tokens/{token_id}", response_model=LineTokenCreate)
def get_line_token(token_id: int, db: Session = Depends(get_db)):
    db_line_token = db.query(LineToken).filter(LineToken.id == token_id).first()
    if not db_line_token:
        raise HTTPException(status_code=404, detail="Line token not found")
    return db_line_token

@app.put("/line_tokens/{token_id}", response_model=LineTokenCreate)
def update_line_token(token_id: int, line_token: LineTokenCreate, db: Session = Depends(get_db)):
    db_line_token = db.query(LineToken).filter(LineToken.id == token_id).first()
    if not db_line_token:
        raise HTTPException(status_code=404, detail="Line token not found")

    db_line_token.token = line_token.token
    db.add(db_line_token)
    db.commit()
    db.refresh(db_line_token)
    return db_line_token

@app.delete("/line_tokens/{token_id}", response_model=LineTokenCreate)
def delete_line_token(token_id: int, db: Session = Depends(get_db)):
    db_line_token = db.query(LineToken).filter(LineToken.id == token_id).first()
    if not db_line_token:
        raise HTTPException(status_code=404, detail="Line token not found")

    db.delete(db_line_token)
    db.commit()
    return db_line_token

@app.get("/cameras/", response_model=List[CameraCreate])
def get_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()

@app.get("/cameras/{camera_id}", response_model=CameraCreate)
def get_camera_by_id(camera_id: int, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return db_camera

@app.delete("/cameras/{camera_id}", response_model=CameraCreate)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.delete(db_camera)
    db.commit()
    return db_camera

@app.get("/cameras/detail/", response_model=List[CameraDetail])
def get_camera_details(db: Session = Depends(get_db)):

    result = db.query(Camera, Room.room_name, MessageTemplate.content, LineToken.token).\
        join(Room, Camera.room_id == Room.id).\
        join(MessageTemplate, Camera.message_id == MessageTemplate.id, isouter=True).\
        join(LineToken, Camera.line_token_id == LineToken.id, isouter=True).\
        all()

    camera_details = [
        CameraDetail(
            id=cam.id,
            camera_name=cam.camera_name,
            stream_url=cam.stream_url,
            is_streaming=cam.is_streaming,
            is_notification=cam.is_notification,
            room_name=room_name,
            message=message_content,
            line_token=line_token
        )
        for cam, room_name, message_content, line_token in result
    ]

    return camera_details

@app.get("/cameras/detail/{camera_id}", response_model=CameraDetail)
def get_camera_detail(camera_id: int, db: Session = Depends(get_db)):
    result = db.query(Camera, Room.room_name, MessageTemplate.content, LineToken.token).\
        join(Room, Camera.room_id == Room.id).\
        join(MessageTemplate, Camera.message_id == MessageTemplate.id, isouter=True).\
        join(LineToken, Camera.line_token_id == LineToken.id, isouter=True).\
        filter(Camera.id == camera_id).\
        first() 

    if not result:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam, room_name, message_content, line_token = result

    return CameraDetail(
        id=cam.id,
        camera_name=cam.camera_name,
        stream_url=cam.stream_url,
        is_streaming=cam.is_streaming,
        is_notification=cam.is_notification,
        room_name=room_name,
        message=message_content,
        line_token=line_token
    )

class CameraCreateWithDetails(BaseModel):
    camera_name: str
    stream_url: str
    is_streaming: bool = True
    is_notification: bool = True
    room_name: str
    message: str
    line_token: str

    class Config:
        from_attributes = True

@app.post("/cameras/", response_model=CameraDetail)
def create_camera(camera_data: CameraCreateWithDetails, db: Session = Depends(get_db)):

    room = db.query(Room).filter(Room.room_name == camera_data.room_name).first()

    if not room:
        room = Room(room_name=camera_data.room_name)
        db.add(room)
        db.commit()
        db.refresh(room)


    message_template = db.query(MessageTemplate).filter(MessageTemplate.content == camera_data.message).first()
    if not message_template:
        message_template = MessageTemplate(content=camera_data.message)
        db.add(message_template)
        db.commit()
        db.refresh(message_template)

    line_token_obj = db.query(LineToken).filter(LineToken.token == camera_data.line_token).first()
    if not line_token_obj:
        line_token_obj = LineToken(token=camera_data.line_token)
        db.add(line_token_obj)
        db.commit()
        db.refresh(line_token_obj)

    new_camera = Camera(
        camera_name=camera_data.camera_name,
        stream_url=camera_data.stream_url,
        is_streaming=camera_data.is_streaming,
        is_notification=camera_data.is_notification,
        room_id=room.id,
        message_id=message_template.id,
        line_token_id=line_token_obj.id
    )
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)

    return CameraDetail(
        id=new_camera.id,
        camera_name=new_camera.camera_name,
        stream_url=new_camera.stream_url,
        is_streaming=new_camera.is_streaming,
        is_notification=new_camera.is_notification,
        room_name=room.room_name,
        message=message_template.content,
        line_token=line_token_obj.token
    )

@app.put("/cameras/", response_model=CameraDetail)
def update_camera(camera_data: CameraDetail, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.room_name == camera_data.room_name).first()

    if not room:
        room = Room(room_name=camera_data.room_name)
        db.add(room)
        db.commit()
        db.refresh(room)
    message_template = db.query(MessageTemplate).filter(MessageTemplate.content == camera_data.message).first()
    if not message_template:
 
        message_template = MessageTemplate(content=camera_data.message)
        db.add(message_template)
        db.commit()
        db.refresh(message_template)

    line_token_obj = db.query(LineToken).filter(LineToken.token == camera_data.line_token).first()
    if not line_token_obj:

        line_token_obj = LineToken(token=camera_data.line_token)
        db.add(line_token_obj)
        db.commit()
        db.refresh(line_token_obj)


    new_camera = Camera(
        camera_name=camera_data.camera_name,
        stream_url=camera_data.stream_url,
        is_streaming=camera_data.is_streaming,
        is_notification=camera_data.is_notification,
        room_id=room.id,
        message_id=message_template.id,
        line_token_id=line_token_obj.id
    )
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)

@app.patch("/cameras/{camera_id}/update_streaming", response_model=CameraDetail)
async def update_camera_streaming(camera_id: int, body: dict, db: Session = Depends(get_db)):
  
    is_streaming = body.get('is_streaming')

    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    

    db_camera.is_streaming = is_streaming

    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

    return CameraDetail(
        id=db_camera.id,
        camera_name=db_camera.camera_name,
        stream_url=db_camera.stream_url,
        is_streaming=db_camera.is_streaming,
        is_notification=db_camera.is_notification,
        room_name=db_camera.room.room_name if db_camera.room else None,
        message=db_camera.message_obj.content if db_camera.message_obj else None,
        line_token=db_camera.line_token_obj.token if db_camera.line_token_obj else None
    )

@app.patch("/cameras/{camera_id}/update_notification", response_model=CameraDetail)
async def update_camera_notification(camera_id: int, body: dict, db: Session = Depends(get_db)):
    is_notification = body.get('is_notification')
  
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_camera.is_notification = is_notification

    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

    return CameraDetail(
        id=db_camera.id,
        camera_name=db_camera.camera_name,
        stream_url=db_camera.stream_url,
        is_streaming=db_camera.is_streaming,
        is_notification=db_camera.is_notification,
        room_name=db_camera.room.room_name if db_camera.room else None,
        message=db_camera.message_obj.content if db_camera.message_obj else None,
        line_token=db_camera.line_token_obj.token if db_camera.line_token_obj else None
    )

@app.put("/cameras/{camera_id}", response_model=CameraDetail)
def update_camera(camera_id: int, camera_data: CameraUpdateWithDetails, db: Session = Depends(get_db)):

    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    room = db.query(Room).filter(Room.room_name == camera_data.room_name).first()
    if not room:
        room = Room(room_name=camera_data.room_name)
        db.add(room)
        db.commit()
        db.refresh(room)

    message_template = db.query(MessageTemplate).filter(MessageTemplate.content == camera_data.message).first()
    if not message_template:
        message_template = MessageTemplate(content=camera_data.message)
        db.add(message_template)
        db.commit()
        db.refresh(message_template)

    line_token_obj = db.query(LineToken).filter(LineToken.token == camera_data.line_token).first()
    if not line_token_obj:
        line_token_obj = LineToken(token=camera_data.line_token)
        db.add(line_token_obj)
        db.commit()
        db.refresh(line_token_obj)

    db_camera.camera_name = camera_data.camera_name
    db_camera.stream_url = camera_data.stream_url
    db_camera.is_streaming = camera_data.is_streaming
    db_camera.is_notification = camera_data.is_notification
    db_camera.room_id = room.id
    db_camera.message_id = message_template.id
    db_camera.line_token_id = line_token_obj.id

    db.commit()
    db.refresh(db_camera)

    return CameraDetail(
        id=db_camera.id,
        camera_name=db_camera.camera_name,
        stream_url=db_camera.stream_url,
        is_streaming=db_camera.is_streaming,
        is_notification=db_camera.is_notification,
        room_name=room.room_name,
        message=message_template.content,
        line_token=line_token_obj.token
    )


Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

camera_threads = {}
camera_flags = {}

@app.post("/cameras/start")
def start_all_rtsp_streams(db: Session = Depends(get_db)):
    # stop_flags = []
    camera_threads.clear() 
    camera_flags.clear()

    cameras = get_camera_details(db)
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

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request, db: Session = Depends(get_db)):
    rooms = db.query(Room).all()  # Fetch all rooms from the database
    return templates.TemplateResponse("index.html", {"request": request})

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