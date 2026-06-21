# backend/app/models.py
from sqlalchemy import Column, Integer, String, DateTime
from .database import Base
from datetime import datetime

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(36), unique=True, index=True, nullable=False)
    customer_id = Column(String(64), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    document_type = Column(String(64), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    checksum = Column(String(64), nullable=False)
    s3_path = Column(String(512), nullable=False)