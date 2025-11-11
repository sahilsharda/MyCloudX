from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os, shutil, webbrowser, threading

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
TOKEN = os.getenv("MYCLOUDX_TOKEN", "secret123")

app = FastAPI(title="MyCloudX - MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

def require_token(given: str):
    if given != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auth")
def auth(token: str = Form(...)):
    require_token(token)
    return {"ok": True}

@app.post("/upload")
def upload_file(token: str = Form(...), file: UploadFile = File(...)):
    require_token(token)
    dst = os.path.join(UPLOAD_DIR, file.filename)
    with open(dst, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename, "status": "uploaded"}

@app.get("/list")
def list_files(token: str):
    require_token(token)
    items = sorted(os.listdir(UPLOAD_DIR))
    return {"files": items}

@app.get("/download/{name}")
def download_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, filename=name)

@app.delete("/delete/{name}")
def delete_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Not found")
    os.remove(path)
    return {"deleted": name}

def open_browser():
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    import uvicorn
    threading.Timer(2.0, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # <-- change host to 0.0.0.0
