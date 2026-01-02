from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os, shutil, socket, qrcode, base64
from dotenv import load_dotenv
load_dotenv()

from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import uuid
from PIL import Image, ImageOps

# Database imports
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


app = FastAPI(title="MyCloudX - MVP")

# Base directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: UPLOAD_DIR is now just a base, specific uploads go into user folders
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
THUMB_DIR = os.path.join(BASE_DIR, "thumbnails")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# --- Production Hardening Settings ---
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_MIME_TYPES = [
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    "application/pdf", "text/plain",
    "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip", "application/x-zip-compressed"
]

# Ensure folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./mycloudx.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in environment or .env file")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True) # Nullable for OAuth users
    google_id = Column(String, unique=True, index=True, nullable=True)
    disabled = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth Utils ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Share links storage (Legacy json support or migrate to DB later)
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
# Note: We might want to protect /files if we want strict privacy, 
# but for now keeping it mounted for serving
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# CORS setup - Allow localhost, LAN, and Cloudflare tunnel
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
]

# Read Cloudflare URL if available and add to CORS
if os.path.exists("public_url.txt"):
    with open("public_url.txt") as f:
        cf_url = f.read().strip()
        if cf_url:
            ALLOWED_ORIGINS.append(cf_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for tunnel access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_thumbnail(filename, user_id):
    """Generate a thumbnail for an image file inside user's folder"""
    try:
        # Structure: uploads/user_id/filename
        # Thumb:     thumbnails/user_id/filename
        user_upload_dir = os.path.join(UPLOAD_DIR, str(user_id))
        user_thumb_dir = os.path.join(THUMB_DIR, str(user_id))
        
        file_path = os.path.join(user_upload_dir, filename)
        thumb_path = os.path.join(user_thumb_dir, filename)
        
        if os.path.exists(thumb_path):
            return
            
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        
        with Image.open(file_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img = ImageOps.fit(img, (300, 300), Image.Resampling.LANCZOS)
            img.save(thumb_path, "JPEG", quality=70)
    except Exception as e:
        print(f"Thumbnail generation failed for {filename}: {e}")

# 🏠 Home route
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Auth Routes ---

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/google")
def google_auth(credential: str = Form(...), db: Session = Depends(get_db)):
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured on server")
    
    try:
        # Verify the ID Token from frontend
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        
        # Check if user exists
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if not user:
            # Create new user for this Google account
            user = User(username=email, google_id=google_id)
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Issue our own JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "username": user.username}
        
    except ValueError:
        # Invalid token
        raise HTTPException(status_code=400, detail="Invalid Google token")


# 📤 Upload file (Protected & Scoped)
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    user: User = Depends(get_current_user)
):
    # 1. Validate File Size
    # Note: SpooledTemporaryFile might not have .size, so we seek or check headers
    # Better to check Content-Length header for preliminary check
    content_length = file.size if hasattr(file, 'size') else 0
    if content_length > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max allowed: {MAX_FILE_SIZE/(1024*1024)}MB")

    # 2. Validate MIME Type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_folder, exist_ok=True)

    filename = os.path.basename(file.filename)
    file_path = os.path.join(user_folder, filename)
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    # Generate thumbnail
    ext = filename.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp']:
        generate_thumbnail(filename, user.id)
        
    return {"filename": filename}

# 📂 List files (Protected & Scoped)
@app.get("/list")
def list_files(user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_folder, exist_ok=True)
    
    files_data = []
    
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file.startswith('.'): continue
            
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, user_folder) # Relative to user folder
            
            try:
                stat = os.stat(filepath)
                ext = file.lower().split('.')[-1] if '.' in file else ''
                
                # Check for existing thumbnail
                thumb_path = os.path.join(THUMB_DIR, str(user.id), rel_path)
                has_thumb = os.path.exists(thumb_path)

                files_data.append({
                    "name": rel_path,
                    "size": stat.st_size,
                    "size_formatted": format_bytes(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": get_file_type(ext),
                    "has_thumbnail": has_thumb
                })
            except OSError:
                continue
    
    files_data.sort(key=lambda x: x["modified"], reverse=True)
    
    return {
        "files": [f["name"] for f in files_data], 
        "files_detailed": files_data,
        "folders": [] # Todo: implement nested folder logic for scoped structure
    }

# 📁 Folder Operations (Protected & Scoped)
@app.post("/folders/create")
def create_folder(name: str = Form(...), user: User = Depends(get_current_user)):
    # user folder base
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_folder, exist_ok=True)

    safe_name = os.path.normpath(name).lstrip(os.sep)
    if '..' in safe_name:
        raise HTTPException(status_code=400, detail="Invalid folder name")
        
    path = os.path.join(user_folder, safe_name)
    try:
        os.makedirs(path, exist_ok=True)
        return {"created": safe_name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/folders/delete")
def delete_folder(name: str, user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    path = os.path.join(user_folder, name)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Security check: ensure path is inside user_folder
    if not os.path.abspath(path).startswith(os.path.abspath(user_folder)):
         raise HTTPException(status_code=403, detail="Access denied")

    try:
        shutil.rmtree(path)
        return {"deleted": name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✏️ Rename (Protected & Scoped)
@app.post("/rename")
def rename_item(old_name: str = Form(...), new_name: str = Form(...), user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    
    old_path = os.path.join(user_folder, old_name)
    new_path = os.path.join(user_folder, new_name)
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Item not found")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Destination already exists")
        
    if not os.path.abspath(new_path).startswith(os.path.abspath(user_folder)):
        raise HTTPException(status_code=400, detail="Invalid destination")
        
    try:
        os.rename(old_path, new_path)
        return {"renamed": new_name}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔗 Sharing (TODO: Update to support user context, keeping simple for now)
@app.post("/share")
def create_share(path: str = Form(...), user: User = Depends(get_current_user)):
    # Note: Sharing logic needs to handle user ID in path now
    # We will store: "user_id/filename"
    
    relative_path = os.path.join(str(user.id), path)
    full_path = os.path.join(UPLOAD_DIR, relative_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    shares = load_shares()
    # Check existing
    for link_id, file_path in shares.items():
        if file_path == relative_path:
            return {"link_id": link_id}
            
    link_id = str(uuid.uuid4())[:8]
    shares[link_id] = relative_path
    save_shares(shares)
    
    return {"link_id": link_id}

@app.get("/shared/{link_id}")
def get_shared(link_id: str):
    shares = load_shares()
    if link_id not in shares:
        raise HTTPException(status_code=404, detail="Link not found or expired")
        
    # shares[link_id] is "user_id/filename"
    stored_path = shares[link_id]
    path = os.path.join(UPLOAD_DIR, stored_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path, filename=os.path.basename(path))

# ⬇️ Download file (Protected & Scoped)
@app.get("/download/{name}")
def download_file(name: str, user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    path = os.path.join(user_folder, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=name)

# 🖼️ Get Thumbnail (Protected & Scoped)
@app.get("/thumbnail/{name:path}")
def get_thumbnail(name: str, user: User = Depends(get_current_user)):
    # Structure: thumbnails/user_id/name
    thumb_path = os.path.join(THUMB_DIR, str(user.id), name)
    
    if not os.path.exists(thumb_path):
        # Try generate
        generate_thumbnail(name, user.id)
    
    if os.path.exists(thumb_path):
        return FileResponse(thumb_path)
    else:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

# 🗑️ Delete file (Protected & Scoped)
@app.delete("/delete/{name}")
def delete_file(name: str, user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    path = os.path.join(user_folder, name)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check using abspath
    if not os.path.abspath(path).startswith(os.path.abspath(user_folder)):
         raise HTTPException(status_code=403, detail="Access denied")

    os.remove(path)
    return {"deleted": name}

# 💾 Storage stats (Protected & Scoped)
@app.get("/storage-stats")
def storage_stats(user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_folder, exist_ok=True)
    
    total_size = 0
    file_count = 0
    type_breakdown = {
        "images": {"size": 0, "count": 0},
        "videos": {"size": 0, "count": 0},
        "documents": {"size": 0, "count": 0},
        "other": {"size": 0, "count": 0}
    }
    
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file.startswith('.'): continue
            filepath = os.path.join(root, file)
            try:
                size = os.path.getsize(filepath)
                total_size += size
                file_count += 1
                
                ext = file.lower().split('.')[-1] if '.' in file else ''
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
                    cat = "images"
                elif ext in ['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv']:
                    cat = "videos"
                elif ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']:
                    cat = "documents"
                else:
                    cat = "other"
                
                type_breakdown[cat]["size"] += size
                type_breakdown[cat]["count"] += 1
            except OSError:
                continue
    
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

# 📄 File info (Protected & Scoped)
@app.get("/file-info/{name:path}")
def file_info(name: str, user: User = Depends(get_current_user)):
    user_folder = os.path.join(UPLOAD_DIR, str(user.id))
    path = os.path.join(user_folder, name)
    
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
