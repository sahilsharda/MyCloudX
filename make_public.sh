echo "🚀 Starting MyCloudX Public Mode..."
echo "------------------------------------"
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "✅ Virtual environment activated"
fi
pkill -f "uvicorn" >/dev/null 2>&1
pkill -f "cloudflared" >/dev/null 2>&1
echo "⚙️  Launching FastAPI server..."
python3 server.py > server.log 2>&1 &
SERVER_PID=$!
sleep 3
echo "🌍 Connecting Cloudflare tunnel..."
cloudflared tunnel --url http://127.0.0.1:8000 > tunnel.log 2>&1 &
CLOUDFLARED_PID=$!
# Wait for URL up to 30 seconds
MAX_RETRIES=30
COUNT=0
PUBLIC_URL=""

while [ $COUNT -lt $MAX_RETRIES ]; do
  PUBLIC_URL=$(grep -o "https://[-A-Za-z0-9.]*trycloudflare.com" tunnel.log | tail -n 1)
  if [ -n "$PUBLIC_URL" ]; then
    break
  fi
  sleep 1
  COUNT=$((COUNT+1))
  echo -n "."
done
echo ""
if [ -z "$PUBLIC_URL" ]; then
  echo "❌ Could not fetch Cloudflare public URL. Check tunnel.log for details."
  kill $SERVER_PID $CLOUDFLARED_PID >/dev/null 2>&1
  exit 1
fi
echo "$PUBLIC_URL" > public_url.txt
export MYCLOUDX_PUBLIC_URL="$PUBLIC_URL"

echo "------------------------------------"
echo "✅ MyCloudX is LIVE!"
echo "📡 Public URL: $PUBLIC_URL"
echo "📄 Saved to: public_url.txt"
echo "🖥️  Logs: server.log / tunnel.log"
echo "------------------------------------"

wait $SERVER_PID $CLOUDFLARED_PID
