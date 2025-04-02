from pydantic import BaseModel
from typing import Optional

# Base class ที่ใช้ในทั้ง CameraBase และ CameraCreate
class CameraBase(BaseModel):
    stream_url: str
    camera_name: str
    room_name: str
    message: Optional[str] = None
    line_token: Optional[str] = None
    is_streaming: bool = True  
    is_notification: bool = True

# ใช้ในการสร้าง Camera ใหม่
class CameraCreate(CameraBase):
    pass  

# ใช้ในการแสดงข้อมูลกล้อง (หลังจากบันทึกแล้ว)
class Camera(CameraBase):
    id: int  # กำหนด id ที่ต้องการ

    class Config:
        from_attributes = True

class Status(BaseModel):
    id : int
    is_active : bool

    class Config:
        orm_mode = True