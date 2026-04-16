from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uuid
import time
import os

app = FastAPI()

UPLOAD_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory store: token -> (filepath, expiry_time)
file_store = {}

EXPIRY_SECONDS = 300  # 5 minutes

@app.get("/")
def home():
    return {"message": "Temporary Secure File Vault API"}

# ---------------------------
# Upload File
# ---------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_DIR, file_id + "_" + file.filename)

        with open(filepath, "wb") as f:
            f.write(await file.read())

        expiry_time = time.time() + EXPIRY_SECONDS

        file_store[file_id] = {
            "path": filepath,
            "expires": expiry_time
        }

        return {
            "download_link": f"/download/{file_id}",
            "expires_in_seconds": EXPIRY_SECONDS
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# Download File
# ---------------------------
@app.get("/download/{file_id}")
def download_file(file_id: str):
    if file_id not in file_store:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = file_store[file_id]

    if time.time() > file_info["expires"]:
        # Delete expired file
        try:
            os.remove(file_info["path"])
        except:
            pass

        del file_store[file_id]
        raise HTTPException(status_code=403, detail="Link expired")

    return FileResponse(file_info["path"], filename=os.path.basename(file_info["path"]))

# ---------------------------
# Cleanup expired files
# ---------------------------
@app.get("/cleanup")
def cleanup():
    now = time.time()
    removed = 0

    for file_id in list(file_store.keys()):
        if now > file_store[file_id]["expires"]:
            try:
                os.remove(file_store[file_id]["path"])
            except:
                pass
            del file_store[file_id]
            removed += 1

    return {"removed_files": removed}