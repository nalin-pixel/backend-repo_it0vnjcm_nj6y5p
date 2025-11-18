import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import List

app = FastAPI(title="PulseAnime Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files statically
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


ALLOWED_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
}


@app.post("/upload")
async def upload_media(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved = []
    for f in files:
        ext = ALLOWED_MIME.get(f.content_type)
        if not ext:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
        # Create unique filename
        base = os.path.splitext(f.filename)[0].replace(" ", "_")
        safe_base = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "-")) or "file"
        i = 0
        while True:
            name = f"{safe_base}{'' if i == 0 else '-' + str(i)}{ext}"
            path = os.path.join(UPLOAD_DIR, name)
            if not os.path.exists(path):
                break
            i += 1
        with open(path, "wb") as out:
            out.write(await f.read())
        saved.append({
            "filename": name,
            "url": f"/uploads/{name}",
            "content_type": f.content_type,
            "size": os.path.getsize(path)
        })

    return {"uploaded": saved}


@app.get("/media")
def list_media():
    items = []
    for name in sorted(os.listdir(UPLOAD_DIR)):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isfile(path):
            # rudimentary content type inference
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                ct = "image"
            elif name.lower().endswith((".mp4", ".webm", ".ogv")):
                ct = "video"
            else:
                continue
            items.append({"filename": name, "url": f"/uploads/{name}", "type": ct, "size": os.path.getsize(path)})
    return {"media": items}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
