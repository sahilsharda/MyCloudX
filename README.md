# MyCloudX

**Your Personal Cloud Sanctuary**

Experience the freedom of self-hosted cloud storage. MyCloudX combines the elegance of modern design with the privacy of personal hosting. Manage your photos, videos, and documents with a beautiful, Google Photos-inspired interface that puts you in control.

## ✨ Features

- **🎨 Stunning UI**: A modern, dark-themed interface designed for visual comfort and ease of use.
- **📁 Smart Management**: Create folders, rename files, and organize your digital life with intuitive controls.
- **🖼️ Visual Gallery**: Auto-generated thumbnails for images provide a rich, gallery-like browsing experience.
- **🔗 Seamless Sharing**: Generate instant public links to share files with friends and family—no account required for them.
- **🔐 Secure & Private**: Token-based authentication ensures your personal data remains accessible only to you.
- **📊 Storage Insights**: Real-time visualization of your storage usage with color-coded alerts.
- **⚡ High Performance**: Optimized with lazy loading for a snappy, responsive experience on any device.

## 🖥️ System Requirements

Before you begin, ensure your system meets these minimum requirements:

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+ recommended).
- **Python**: Version 3.8 or higher.
- **RAM**: Minimum 512MB (1GB+ recommended for heavy image usage).
- **Disk Space**: 100MB for the application + storage space for your files.
- **Network**: Local network connection (Wi-Fi/LAN) for accessing across devices.

## 🚀 Quick Setup

Choose your platform below for specific commands to get started.

### 🍎 macOS

1.  **Open Terminal** and navigate to the project folder.
2.  **Run the following commands:**

    ```bash
    # Create virtual environment
    python3 -m venv venv

    # Activate environment
    source venv/bin/activate

    # Install dependencies
    pip install fastapi uvicorn python-multipart jinja2 qrcode pillow

    # Run the server
    python3 server.py
    ```

### 🪟 Windows

1.  **Open PowerShell** or Command Prompt and navigate to the project folder.
2.  **Run the following commands:**

    ```powershell
    # Create virtual environment
    python -m venv venv

    # Activate environment
    .\venv\Scripts\activate

    # Install dependencies
    pip install fastapi uvicorn python-multipart jinja2 qrcode pillow

    # Run the server
    python server.py
    ```

### 🍓 Raspberry Pi / Linux

1.  **Open Terminal**.
2.  **Run the following commands:**

    ```bash
    # Update system and install python3-venv if needed
    sudo apt-get update
    sudo apt-get install -y python3-venv

    # Create virtual environment
    python3 -m venv venv

    # Activate environment
    source venv/bin/activate

    # Install dependencies
    pip install fastapi uvicorn python-multipart jinja2 qrcode pillow

    # Run the server
    python3 server.py
    ```

Once started, the server will be accessible at:
- **Localhost**: `http://127.0.0.1:8000` (This computer)
- **Network**: `http://[your-local-ip]:8000` (Other devices on Wi-Fi)

> **Tip**: The terminal will display the exact URLs you can use to access the app.

## ⚙️ Configuration

Customize MyCloudX using environment variables. You can set these in your terminal before running the server.

| Variable | Description | Default |
|----------|-------------|---------|
| `MYCLOUDX_TOKEN` | Your secret login password | `secret123` |
| `STORAGE_QUOTA_GB` | Maximum storage limit in GB | `10` |
| `MYCLOUDX_PUBLIC_URL` | Custom public URL (e.g., for Cloudflare) | *None* |

**Example:**
```bash
export MYCLOUDX_TOKEN="my-super-secret-password"
export STORAGE_QUOTA_GB="50"
python3 server.py
```

## 📖 Usage Guide

1. **Access**: Open the provided URL in your web browser.
2. **Login**: Click the **Settings (⚙️)** icon in the sidebar and enter your token.
3. **Upload**: Drag and drop files or use the upload button.
4. **Share**: Click the **Link (🔗)** icon on any file to copy a shareable link.
5. **Manage**: Right-click or use the action buttons to rename or delete files.

## 🛠️ Tech Stack

Built with robust, modern technologies:
- **Backend**: FastAPI (High-performance Python framework)
- **Server**: Uvicorn (ASGI server)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (No heavy frameworks)
- **Imaging**: Pillow (Python Imaging Library)

## 📄 License

This project is open-source and available under the **MIT License**.
