import os
import json
import time
import requests
from io import BytesIO
from google import genai
from html2image import Html2Image

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

prompt = """
צור 5 ביטויים בצרפתית ברמת C1. החזר את התשובה כ-JSON במבנה המדויק הבא:
[
  {
    "expression": "הביטוי בצרפתית",
    "ipa": "תעתיק IPA",
    "example": "משפט דוגמה בצרפתית",
    "translations": {
      "ENG": "אנגלית",
      "ITA": "איטלקית",
      "HEB": "עברית",
      "SRP": "סרבית",
      "POR": "פורטוגזית",
      "GER": "גרמנית"
    }
  }
]
"""

# רשימת מודלים עדיפות: אם הראשון עמוס, עוברים הבא
models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
response_text = None

for model in models_to_try:
    print(f"Trying model: {model}")
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            if res.text:
                response_text = res.text.strip()
                break
        except Exception as e:
            wait_time = (attempt + 1) * 10
            print(f"Attempt {attempt + 1} for {model} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
    if response_text:
        break

if not response_text:
    raise Exception("Failed to generate content from all Gemini models due to high demand.")

if response_text.startswith("```"):
    lines = response_text.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    response_text = "\n".join(lines).strip()

data = json.loads(response_text)

# --- Log the generated content ---
print("\n" + "="*60)
print("🇫🇷 DAILY FRENCH VOCABULARY - C1 LEVEL")
print("="*60)
for idx, item in enumerate(data, 1):
    print(f"\n[{idx}] {item['expression']}")
    print(f"    IPA: {item['ipa']}")
    print(f"    Example: {item['example']}")
    print(f"    Translations:")
    for lang, translation in item['translations'].items():
        print(f"      - {lang}: {translation}")
print("="*60 + "\n")

# --- בניית HTML מעוצב ---
cards_html = ""
for item in data:
    trans_html = "".join([f"<span><b>{k}:</b> {v}</span>" for k, v in item["translations"].items()])
    cards_html += f"""
    <div class="card">
        <div class="expr-header">
            <span class="expression">{item['expression']}</span>
            <span class="ipa">{item['ipa']}</span>
        </div>
        <div class="example">"{item['example']}"</div>
        <div class="translations">{trans_html}</div>
    </div>
    """

full_html = f"""
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        padding: 30px;
        width: 750px;
        margin: 0 auto;
    }}
    .header {{
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        color: #38bdf8;
        margin-bottom: 25px;
        border-bottom: 2px solid #334155;
        padding-bottom: 10px;
    }}
    .card {{
        background: #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-right: 5px solid #38bdf8;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .expr-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        direction: ltr;
        margin-bottom: 10px;
    }}
    .expression {{
        font-size: 22px;
        font-weight: bold;
        color: #f43f5e;
    }}
    .ipa {{
        font-size: 16px;
        color: #94a3b8;
        font-family: monospace;
        background: #0f172a;
        padding: 4px 8px;
        border-radius: 6px;
    }}
    .example {{
        direction: ltr;
        font-style: italic;
        color: #e2e8f0;
        font-size: 16px;
        margin-bottom: 12px;
        padding: 8px 12px;
        background: #334155;
        border-radius: 6px;
    }}
    .translations {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        font-size: 14px;
        color: #cbd5e1;
    }}
    .translations span {{
        background: #0f172a;
        padding: 6px 10px;
        border-radius: 6px;
    }}
    .translations b {{
        color: #38bdf8;
    }}
</style>
</head>
<body>
    <div class="header">🇫🇷 French C1 Daily Vocabulary</div>
    {cards_html}
</body>
</html>
"""

# רינדור לתמונה - שמור בזיכרון
print("Rendering HTML to image...")
hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])
img_bytes = hti.screenshot(html_str=full_html, size=(810, 1400))[0]
print(f"Image generated successfully ({len(img_bytes)} bytes)")

# --- שליחה לטלגרם ---
print("Sending image to Telegram...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
files = {"photo": ("card.png", BytesIO(img_bytes), "image/png")}
res = requests.post(url, data={"chat_id": CHAT_ID}, files=files)
print(f"Telegram response status: {res.status_code}")
if res.status_code == 200:
    print("✅ Image sent successfully to Telegram!")
else:
    print(f"❌ Failed to send image: {res.text}")
