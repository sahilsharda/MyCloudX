
Personal self-hosted cloud (upload/list/download/delete) built with FastAPI.


python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn python-multipart jinja2
python3 server.py

Open: http://127.0.0.1:8000
Auth token: secret123 (set MYCLOUDX_TOKEN to change)
