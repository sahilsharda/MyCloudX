#!/bin/bash
# MyCloudX - Start server with Cloudflare public URL
# Usage: ./start.sh

cd "$(dirname "$0")"

# Kill any existing processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null

# Remove old URL file
rm -f public_url.txt

# Activate virtual environment
source venv/bin/activate

# Start the server in background
echo "🚀 Starting MyCloudX server..."
python server.py &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Start Cloudflare tunnel and capture the URL
echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:8000 2>&1 | while read line; do
    # Look for the URL in output
    if echo "$line" | grep -q "trycloudflare.com"; then
        URL=$(echo "$line" | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com")
        if [ ! -z "$URL" ]; then
            echo "$URL" > public_url.txt
            echo ""
            echo "═══════════════════════════════════════════════════"
            echo "  🌐 MyCloudX is live!"
            echo "═══════════════════════════════════════════════════"
            echo ""
            echo "  📱 Local:    http://localhost:8000"
            echo "  🌍 Public:   $URL"
            echo ""
            echo "  📲 Scan QR:  http://localhost:8000/qr"
            echo ""
            echo "  ⚠️  Note: URL changes each restart"
            echo "  Press Ctrl+C to stop"
            echo "═══════════════════════════════════════════════════"
        fi
    fi
done &
CF_PID=$!

# Handle Ctrl+C to stop all processes
trap "kill $SERVER_PID $CF_PID 2>/dev/null; pkill -f 'cloudflared tunnel'; exit" SIGINT SIGTERM

# Wait for any process to exit
wait
