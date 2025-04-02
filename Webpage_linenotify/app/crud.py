from sqlalchemy.orm import Session
from . import models, schemas

# ฟังก์ชั่นสำหรับดึงข้อมูลกล้องทั้งหมด
def get_cameras(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Camera).offset(skip).limit(limit).all()

# ฟังก์ชั่นสำหรับดึงกล้องตาม ID
def get_camera_by_id(db: Session, camera_id: int):
    return db.query(models.Camera).filter(models.Camera.id == camera_id).first()

# ฟังก์ชั่นสำหรับสร้างกล้อง
def create_camera(db: Session, camera: schemas.CameraBase):
    db_camera = models.Camera(
        stream_url=camera.stream_url,
        camera_name=camera.camera_name,
        room_name=camera.room_name,
        message=camera.message,
        line_token=camera.line_token,
        is_streaming=camera.is_streaming,
        is_notification=camera.is_notification,
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

# ฟังก์ชั่นสำหรับอัปเดตข้อมูลกล้อง
def update_camera(db: Session, camera_id: int, camera: schemas.CameraBase):
    db_camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if db_camera:
        db_camera.stream_url = camera.stream_url
        db_camera.camera_name = camera.camera_name
        db_camera.room_name = camera.room_name
        db_camera.message = camera.message
        db_camera.line_token = camera.line_token
        db_camera.is_streaming = camera.is_streaming
        db_camera.is_notification = camera.is_notification
        db.commit()
        db.refresh(db_camera)
        return db_camera
    return None

# ฟังก์ชั่นสำหรับลบกล้อง
def delete_camera(db: Session, camera_id: int):
    db_camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if db_camera:
        db.delete(db_camera)
        db.commit()
        return db_camera
    return None

# อัปเดตสถานะ streaming ในฐานข้อมูล
def update_streaming_status(db: Session, camera_id: int, status: bool):
    db_camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if db_camera:
        db_camera.is_streaming = status
        db.commit()
        db.refresh(db_camera)
        return db_camera
    return None

# อัปเดตสถานะ notification ในฐานข้อมูล
def update_notification_status(db: Session, camera_id: int, status: bool):
    db_camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if db_camera:
        db_camera.is_notification = status
        db.commit()
        db.refresh(db_camera)
        return db_camera
    return None

# ฟังก์ชั่นสำหรับดึงข้อมูลสถานะตาม ID
def get_status_by_id(db: Session, status_id: int):
    return db.query(models.Status).filter(models.Status.id == status_id).first()

def update_status(db: Session,id:int, is_active: bool):
    db_status = db.query(models.Status).filter(models.Status.id == id).first()
    if db_status:
        db_status.is_active = is_active
        db.commit()
        db.refresh(db_status)
        return db_status
    return None
