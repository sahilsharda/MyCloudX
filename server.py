from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os, shutil, socket, qrcode, base64
from io import BytesIO

app = FastAPI(title="MyCloudX - MVP")

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ensure static directory exists
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Default token
TOKEN = os.getenv("MYCLOUDX_TOKEN", "secret123")

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def require_token(given: str):
    if given != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Home route
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Authentication
@app.post("/auth")
def auth(token: str = Form(...)):
    require_token(token)
    return {"ok": True}

# Upload file
@app.post("/upload")
def upload_file(token: str = Form(...), file: UploadFile = File(...)):
    require_token(token)
    # Sanitize filename
    filename = os.path.basename(file.filename)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": filename}

# List files
@app.get("/list")
def list_files(token: str):
    require_token(token)
    return {"files": sorted(os.listdir(UPLOAD_DIR))}

# Download file
@app.get("/download/{name}")
def download_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=name)

# Delete file
@app.delete("/delete/{name}")
def delete_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"deleted": name}

# QR page
@app.get("/qr")
def get_qr():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    url = f"http://{local_ip}:8000"
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    html = f"""
    <html><body style='display:flex;justify-content:center;align-items:center;height:100vh;background:#0f2027;color:white;font-family:sans-serif;'>
      <div style='text-align:center;background:rgba(255,255,255,0.1);padding:20px;border-radius:20px;backdrop-filter:blur(8px);'>
        <h2>📱 Scan to Access MyCloudX</h2>
        <img src="data:image/png;base64,{img_base64}" style='width:240px;height:240px;margin-top:10px;border-radius:10px;background:white;padding:10px;'>
        <p>{url}</p>
      </div>
    </body></html>
    """
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    print(f"\n🌐 MyCloudX is live at:\n➡️  http://127.0.0.1:8000\n➡️  http://{local_ip}:8000 (Wi-Fi access)\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
