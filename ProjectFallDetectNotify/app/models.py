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
    is_streaming    = Column(Boolean, default=True)
    is_notification = Column(Boolean, default=True)