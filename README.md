
# MyCloudX

Personal self-hosted cloud storage with Google Photos-inspired interface. Upload, organize, share, and manage your files with a beautiful, modern UI.

## Features

- 📁 **File Management**: Upload, download, rename, and delete files
- 🗂️ **Real Folders**: Create and organize files in actual directories
- 🔗 **Share Links**: Generate public links to share files without authentication
- 🖼️ **Thumbnails**: Auto-generated thumbnails for fast image loading
- 🎨 **Dark Mode**: Beautiful light and dark themes
- 🔐 **Authentication**: Token-based security
- 📊 **Storage Tracking**: Monitor your storage usage with visual indicators
- ⚡ **Performance**: Lazy loading and optimized image delivery

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install fastapi uvicorn python-multipart jinja2 qrcode pillow
```

## Run Server

```bash
source venv/bin/activate && python3 server.py
```

The server will start on:
- **Localhost**: http://127.0.0.1:8000
- **LAN**: http://[your-local-ip]:8000
- **Cloudflare Tunnel**: (if configured)

## Configuration

### Environment Variables

- `MYCLOUDX_TOKEN`: Authentication token (default: `secret123`)
- `MYCLOUDX_PUBLIC_URL`: Public URL for Cloudflare tunnel
- `STORAGE_QUOTA_GB`: Storage quota in GB (default: `10`)

### Example

```bash
export MYCLOUDX_TOKEN="your-secure-token"
export STORAGE_QUOTA_GB="50"
source venv/bin/activate && python3 server.py
```

## Usage

1. Open http://127.0.0.1:8000 in your browser
2. Click the settings icon (⚙️) in the sidebar
3. Enter your token (default: `secret123`) and click Login
4. Start uploading and managing your files!

## Features Guide

### Creating Folders
- Click "New Folder" button
- Enter folder name
- Folders are created as real directories on disk

### Sharing Files
- Click the share icon (🔗) on any file
- Link is copied to clipboard
- Share the link - no authentication required for recipients

### Renaming Files
- Click the edit icon (✏️) on any file
- Enter new name
- File is renamed on disk

### Storage Management
- View storage usage in settings
- Color-coded bar: Green (normal), Yellow (85%+), Red (95%+)
- Warnings appear when storage is low

## Tech Stack

- **Backend**: FastAPI, Uvicorn
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Image Processing**: Pillow
- **QR Codes**: qrcode library

## License

MIT
