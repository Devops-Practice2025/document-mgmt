# backend/app/main.py
# backend/app/main.py  — add these 2 lines at the very top
from dotenv import load_dotenv
load_dotenv()
import io
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from hashlib import sha256
from datetime import datetime

from .deps import get_db
from . import models
from .database import Base, engine
from .s3_client import upload_fileobj, generate_presigned_url, delete_object

app = FastAPI(title="BankDocs Backend")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_document(
    customer_id: str,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    checksum = sha256(contents).hexdigest()
    document_uuid = str(uuid4())
    s3_key = f"{customer_id}/{document_uuid}_{file.filename}"

    upload_fileobj(io.BytesIO(contents), key=s3_key, content_type=file.content_type)

    doc = models.Document(
        document_id=document_uuid,
        customer_id=customer_id,
        file_name=file.filename,
        upload_date=datetime.utcnow(),
        document_type=document_type,
        status="ACTIVE",
        checksum=checksum,
        s3_path=s3_key,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.document_id}


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(models.Document).filter(models.Document.status == "ACTIVE").all()
    return [
        {
            "document_id": d.document_id,
            "customer_id": d.customer_id,
            "file_name": d.file_name,
            "upload_date": d.upload_date,
            "document_type": d.document_type,
            "status": d.status,
        }
        for d in docs
    ]


@app.get("/document/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = (
        db.query(models.Document)
        .filter(models.Document.document_id == document_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    url = generate_presigned_url(doc.s3_path)
    return {"url": url}


@app.delete("/document/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = (
        db.query(models.Document)
        .filter(models.Document.document_id == document_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_object(doc.s3_path)
    doc.status = "DELETED"
    db.commit()
    return {"deleted": True}