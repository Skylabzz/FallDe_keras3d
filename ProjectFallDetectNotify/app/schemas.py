from pydantic import BaseModel
from typing import Optional

class CameraBase(BaseModel):
    stream_url: str
    camera_name: str
    room_name: str
    message: Optional[str] = None
    line_token: Optional[str] = None
    is_streaming: bool = True  
    is_notification: bool = True

class CameraCreate(CameraBase):
    pass  

class Camera(CameraBase):
    id: int

    class Config:
        from_attributes = True