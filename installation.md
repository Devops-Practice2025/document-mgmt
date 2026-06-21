Great, then Phase 1 will be **FastAPI + SQLAlchemy ORM + real AWS S3**, with MySQL running in Docker. We’ll wire everything so it’s easy to lift into EKS later.

***

## 1. Environment & config

Use env vars so you can later inject from GitHub Actions / Kubernetes:

```env
# .env (for local dev only; later move to Secrets Manager)
DB_USER=bankdocs
DB_PASSWORD=bankdocs
DB_HOST=localhost
DB_PORT=3306
DB_NAME=bankdocs

AWS_REGION=eu-central-1
AWS_S3_BUCKET=bankdocs-documents
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

In Docker/EKS you’ll **not** hardcode keys; IAM role / IRSA will replace `AWS_ACCESS_KEY_ID`/`SECRET` later.

***

## 2. SQLAlchemy setup

### `database.py` – engine & session

```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### `models.py` – documents table

```python
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
```

### `deps.py` – DB dependency for FastAPI

```python
# backend/app/deps.py
from .database import SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

And in `startup` (e.g., in `main.py`):

```python
from fastapi import FastAPI
from .database import Base, engine

app = FastAPI(...)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
```

***

## 3. Real S3 client (boto3)

Create a small wrapper so later you can swap localstack vs real S3 easily.

```python
# backend/app/s3_client.py
import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

session = boto3.session.Session(
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

s3 = session.client("s3")

def upload_fileobj(fileobj, key: str, content_type: str):
    s3.upload_fileobj(
        Fileobj=fileobj,
        Bucket=AWS_S3_BUCKET,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )

def delete_object(key: str):
    s3.delete_object(Bucket=AWS_S3_BUCKET, Key=key)

def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
```

For production, you’ll drop explicit keys and rely on IAM role permissions attached to the pod/EC2.

***

## 4. FastAPI endpoints with SQLAlchemy + S3

### `POST /upload`

```python
# backend/app/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import uuid4
from hashlib import sha256
from datetime import datetime

from .deps import get_db
from . import models
from .s3_client import upload_fileobj, generate_presigned_url, delete_object

app = FastAPI(title="BankDocs Backend")

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

    # upload to S3
    import io
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
```

### `GET /documents`

```python
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
```

### `GET /document/{id}` (presigned URL)

```python
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
```

### `DELETE /document/{id}`

```python
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
```

***

## 5. Next small steps for you

Today you can:

1. Add `database.py`, `models.py`, `deps.py`, and `s3_client.py` as above.
2. Wire `main.py` with these endpoints.
3. Test with curl/Postman:
   - `POST /upload` with `multipart/form-data` → confirm S3 object + DB row.
   - `GET /documents` → JSON list.
   - `GET /document/{id}` → presigned URL opens in browser.
4. Once backend works, point your React UI to these real endpoints.

If you paste your current `docker-compose.yml` and `main.py`, I can adjust them to match this **real S3 + SQLAlchemy** pattern exactly.