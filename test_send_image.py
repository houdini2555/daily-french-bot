import os
import requests
from io import BytesIO
from html2image import Html2Image

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Simple HTML to test
simple_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {
        font-family: Arial, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        padding: 30px;
        width: 750px;
        margin: 0 auto;
    }
    .header {
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        color: #38bdf8;
        margin-bottom: 25px;
        border-bottom: 2px solid #334155;
        padding-bottom: 10px;
    }
    .card {
        background: #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-right: 5px solid #38bdf8;
    }
</style>
</head>
<body>
    <div class="header">🇫🇷 Test Image - French Daily Bot</div>
    <div class="card">
        <h2>Test Card 1</h2>
        <p>This is a test image to verify the Telegram integration works!</p>
    </div>
    <div class="card">
        <h2>Test Card 2</h2>
        <p>If you see this, the image generation and Telegram sending is working correctly.</p>
    </div>
</body>
</html>
"""

# Generate image
print("Rendering HTML to image...")
hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])
img_bytes = hti.screenshot(html_str=simple_html, size=(810, 600))[0]
print(f"Image generated successfully ({len(img_bytes)} bytes)")

# Send to Telegram
print("Sending image to Telegram...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
files = {"photo": ("test_card.png", BytesIO(img_bytes), "image/png")}
res = requests.post(url, data={"chat_id": CHAT_ID}, files=files)
print(f"Telegram response status: {res.status_code}")
if res.status_code == 200:
    print("✅ Image sent successfully to Telegram!")
else:
    print(f"❌ Failed to send image: {res.text}")
