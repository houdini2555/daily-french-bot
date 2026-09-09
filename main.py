import os
import json
import time
import requests
from google import genai
from google.genai.errors import APIError
from html2image import Html2Image

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

prompt = """
צור 5 ביטויים בצרפתית ברמת C1. החזר את התשובה כ-JSON נקי בלבד במבנה הבא:
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

response_text = None
for attempt in range(3):
    try:
        res = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        response_text = res.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        if response_text:
            break
    except APIError as e:
        time.sleep(5)

if not response_text:
    raise Exception("Failed to generate content.")

data = json.loads(response_text)

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

# רינדור לתמונה
hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])
hti.output_path = '.'
hti.screenshot(html_str=full_html, save_as='card.png', size=(810, 1400))

# שליחה לטלגרם
url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/sendPhoto"
with open("card.png", "rb") as img_file:
    requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img_file})
