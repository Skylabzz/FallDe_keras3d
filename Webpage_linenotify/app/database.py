from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


# กำหนดค่าการเชื่อมต่อกับ MySQL โดยตรง
SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:@localhost:3306/predict_camera"

# สร้างการเชื่อมต่อกับ MySQL
engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool)  # NullPool เพื่อปิดการใช้งาน connection pooling ถ้าไม่ต้องการ

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
