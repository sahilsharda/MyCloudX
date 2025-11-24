from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os, shutil, socket, qrcode, base64
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json
import uuid
from PIL import Image, ImageOps

app = FastAPI(title="MyCloudX - MVP")

# Base directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
THUMB_DIR = os.path.join(BASE_DIR, "thumbnails")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Ensure folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Token for auth
TOKEN = os.getenv("MYCLOUDX_TOKEN", "secret123")

# Share links storage
SHARES_FILE = os.path.join(BASE_DIR, "shares.json")
if not os.path.exists(SHARES_FILE):
    with open(SHARES_FILE, "w") as f:
        json.dump({}, f)

def load_shares():
    try:
        with open(SHARES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_shares(shares):
    with open(SHARES_FILE, "w") as f:
        json.dump(shares, f)

# Mount static + template dirs
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth check helper
def require_token(given: str):
    if given != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def generate_thumbnail(filename):
    """Generate a thumbnail for an image file"""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        thumb_path = os.path.join(THUMB_DIR, filename)
        
        # Skip if thumb exists
        if os.path.exists(thumb_path):
            return
            
        # Ensure thumb dir structure exists for nested files
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        
        with Image.open(file_path) as img:
            # Convert to RGB if needed (e.g. PNG with alpha)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Create thumbnail
            img = ImageOps.fit(img, (300, 300), Image.Resampling.LANCZOS)
            img.save(thumb_path, "JPEG", quality=70)
    except Exception as e:
        print(f"Thumbnail generation failed for {filename}: {e}")

# 🏠 Home route
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 🔐 Auth route
@app.post("/auth")
def auth(token: str = Form(...)):
    require_token(token)
    return {"ok": True}

# 📤 Upload file
@app.post("/upload")
def upload_file(token: str = Form(...), file: UploadFile = File(...)):
    require_token(token)
    filename = os.path.basename(file.filename)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    # Generate thumbnail if image
    ext = filename.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp']:
        generate_thumbnail(filename)
        
    return {"filename": filename}

# 📂 List files
@app.get("/list")
def list_files(token: str):
    require_token(token)
    files_data = []
    
    for root, dirs, files in os.walk(UPLOAD_DIR):
        for file in files:
            if file.startswith('.'):  # Skip hidden files
                continue
            
            # Get relative path from UPLOAD_DIR
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, UPLOAD_DIR)
            
            try:
                stat = os.stat(filepath)
                ext = file.lower().split('.')[-1] if '.' in file else ''
                
                files_data.append({
                    "name": rel_path,
                    "size": stat.st_size,
                    "size_formatted": format_bytes(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": get_file_type(ext)
                })
            except OSError:
                continue
    
    # Sort by modification date (newest first)
    files_data.sort(key=lambda x: x["modified"], reverse=True)
    
    # Add directories
    dirs_data = []
    for root, dirs, files in os.walk(UPLOAD_DIR):
        for d in dirs:
            if d.startswith('.'): continue
            dirpath = os.path.join(root, d)
            rel_path = os.path.relpath(dirpath, UPLOAD_DIR)
            dirs_data.append(rel_path)
            
    return {
        "files": [f["name"] for f in files_data], 
        "files_detailed": files_data,
        "folders": dirs_data
    }

# 📁 Folder Operations
@app.post("/folders/create")
def create_folder(name: str = Form(...), token: str = Form(...)):
    require_token(token)
    # Prevent directory traversal
    safe_name = os.path.normpath(name).lstrip(os.sep)
    if '..' in safe_name:
        raise HTTPException(status_code=400, detail="Invalid folder name")
        
    path = os.path.join(UPLOAD_DIR, safe_name)
    try:
        os.makedirs(path, exist_ok=True)
        return {"created": safe_name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/folders/delete")
def delete_folder(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Folder not found")
    try:
        shutil.rmtree(path)
        return {"deleted": name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✏️ Rename
@app.post("/rename")
def rename_item(old_name: str = Form(...), new_name: str = Form(...), token: str = Form(...)):
    require_token(token)
    
    old_path = os.path.join(UPLOAD_DIR, old_name)
    new_path = os.path.join(UPLOAD_DIR, new_name)
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Item not found")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Destination already exists")
        
    # Ensure we stay in upload dir
    if not os.path.abspath(new_path).startswith(os.path.abspath(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid destination")
        
    try:
        os.rename(old_path, new_path)
        return {"renamed": new_name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔗 Sharing
@app.post("/share")
def create_share(path: str = Form(...), token: str = Form(...)):
    require_token(token)
    
    full_path = os.path.join(UPLOAD_DIR, path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    shares = load_shares()
    
    # Check if already shared
    for link_id, file_path in shares.items():
        if file_path == path:
            return {"link_id": link_id}
            
    # Create new share
    link_id = str(uuid.uuid4())[:8]
    shares[link_id] = path
    save_shares(shares)
    
    return {"link_id": link_id}

@app.get("/shared/{link_id}")
def get_shared(link_id: str):
    shares = load_shares()
    if link_id not in shares:
        raise HTTPException(status_code=404, detail="Link not found or expired")
        
    path = os.path.join(UPLOAD_DIR, shares[link_id])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path, filename=os.path.basename(path))

# ⬇️ Download file
@app.get("/download/{name}")
def download_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=name)

# 🖼️ Get Thumbnail
@app.get("/thumbnail/{name:path}")
def get_thumbnail(name: str, token: str):
    require_token(token)
    path = os.path.join(THUMB_DIR, name)
    
    # If thumbnail doesn't exist, try to generate it
    if not os.path.exists(path):
        orig_path = os.path.join(UPLOAD_DIR, name)
        if os.path.exists(orig_path):
            generate_thumbnail(name)
    
    if os.path.exists(path):
        return FileResponse(path)
    else:
        # Fallback to original if generation failed or not possible
        # Or return 404 to let frontend show icon
        raise HTTPException(status_code=404, detail="Thumbnail not found")

# 🗑️ Delete file
@app.delete("/delete/{name}")
def delete_file(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"deleted": name}

# 💾 Storage stats
@app.get("/storage-stats")
def storage_stats(token: str):
    require_token(token)
    
    total_size = 0
    file_count = 0
    type_breakdown = {
        "images": {"size": 0, "count": 0},
        "videos": {"size": 0, "count": 0},
        "documents": {"size": 0, "count": 0},
        "other": {"size": 0, "count": 0}
    }
    
    # Walk through all files in upload directory
    for root, dirs, files in os.walk(UPLOAD_DIR):
        for file in files:
            if file.startswith('.'):  # Skip hidden files
                continue
            filepath = os.path.join(root, file)
            try:
                size = os.path.getsize(filepath)
                total_size += size
                file_count += 1
                
                # Categorize by extension
                ext = file.lower().split('.')[-1] if '.' in file else ''
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
                    type_breakdown["images"]["size"] += size
                    type_breakdown["images"]["count"] += 1
                elif ext in ['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv']:
                    type_breakdown["videos"]["size"] += size
                    type_breakdown["videos"]["count"] += 1
                elif ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']:
                    type_breakdown["documents"]["size"] += size
                    type_breakdown["documents"]["count"] += 1
                else:
                    type_breakdown["other"]["size"] += size
                    type_breakdown["other"]["count"] += 1
            except OSError:
                continue
    
    # Storage quota (10GB default, can be configured via env)
    quota = int(os.getenv("STORAGE_QUOTA_GB", "10")) * 1024 * 1024 * 1024
    remaining = max(0, quota - total_size)
    
    return {
        "total_size": total_size,
        "total_size_formatted": format_bytes(total_size),
        "file_count": file_count,
        "quota": quota,
        "quota_formatted": format_bytes(quota),
        "remaining": remaining,
        "remaining_formatted": format_bytes(remaining),
        "usage_percent": round((total_size / quota * 100), 2) if quota > 0 else 0,
        "breakdown": type_breakdown
    }

# 📄 File info
@app.get("/file-info/{name:path}")
def file_info(name: str, token: str):
    require_token(token)
    path = os.path.join(UPLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    stat = os.stat(path)
    ext = name.lower().split('.')[-1] if '.' in name else ''
    
    info = {
        "name": name,
        "size": stat.st_size,
        "size_formatted": format_bytes(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "extension": ext,
        "type": get_file_type(ext)
    }
    
    # Add image dimensions if it's an image
    if info["type"] == "image":
        try:
            from PIL import Image
            with Image.open(path) as img:
                info["width"] = img.width
                info["height"] = img.height
        except:
            pass
    
    return info

# Helper functions
def format_bytes(bytes_size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_file_type(ext: str) -> str:
    """Get file type category from extension"""
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
        return "image"
    elif ext in ['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv']:
        return "video"
    elif ext in ['mp3', 'wav', 'ogg', 'flac', 'm4a']:
        return "audio"
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']:
        return "document"
    else:
        return "other"

# 📱 QR Page - Cloudflare / Wi-Fi Dynamic
@app.get("/qr")
def get_qr():
    """
    Generate QR code for Cloudflare public URL if available,
    otherwise fall back to local Wi-Fi IP.
    """
    # Step 1: get local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    # Step 2: try reading Cloudflare public URL
    public_url = os.getenv("MYCLOUDX_PUBLIC_URL", "").strip()
    if not public_url and os.path.exists("public_url.txt"):
        with open("public_url.txt", "r") as f:
            public_url = f.read().strip()

    # Step 3: decide which link to show
    if public_url:
        target_url = public_url
        label = "🌍 Cloudflare Public Access"
    else:
        target_url = f"http://{local_ip}:8000"
        label = "📶 Local Wi-Fi Access"

    # Step 4: create QR code
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Step 5: HTML for display
    html = f"""
    <html>
      <body style='display:flex;justify-content:center;align-items:center;height:100vh;background:#0f2027;color:white;font-family:sans-serif;'>
        <div style='text-align:center;background:rgba(255,255,255,0.1);padding:25px;border-radius:20px;backdrop-filter:blur(8px);'>
          <h2>{label}</h2>
          <img src="data:image/png;base64,{img_base64}" style='width:240px;height:240px;margin-top:10px;border-radius:10px;background:white;padding:10px;'>
          <p style='margin-top:10px;color:#ccc;'>{target_url}</p>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(html)

# 🚀 Run server
if __name__ == "__main__":
    import uvicorn

    # Detect local IP for info print
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    print("\n🌐 MyCloudX is live at:\n")
    print(f"➡️  Localhost: http://127.0.0.1:8000")
    print(f"➡️  Wi-Fi LAN: http://{local_ip}:8000")

    # Print Cloudflare URL if file exists
    if os.path.exists("public_url.txt"):
        with open("public_url.txt") as f:
            link = f.read().strip()
            print(f"➡️  Cloudflare: {link}\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
