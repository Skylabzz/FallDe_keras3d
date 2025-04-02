from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import relationship
from .database import Base

class Camera(Base):
    __tablename__ = "camera"
    
    id = Column(Integer, primary_key=True, index=True)
    stream_url   = Column(String(255))
    camera_name = Column(String(100), index=True)
    room_name   = Column(String(100))
    message     = Column(String(255))
    line_token  = Column(String(255))
    is_streaming    = Column(Boolean, default=True)  # เปิด/ปิด การดึงภาพจากกล้อง
    is_notification = Column(Boolean, default=True)  # เปิด/ปิด การส่งภาพแจ้งเตือน
    
class Status(Base):
    __tablename__ = "status"
    
    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=False)  # สถานะการทำงานของกล้อง
    