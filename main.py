import os
import json
import time
import requests
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 1. Environment Variables & Token Cleaning
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
RAW_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# Strip any brackets, quotes, or URLs if passed wrapped by GitHub
TELEGRAM_TOKEN = RAW_TOKEN.split("bot")[-1].replace("[", "").replace("]", "").replace("*", "").strip()

HISTORY_FILE = "history.json"
client = genai.Client(api_key=GEMINI_KEY)

# 2. History Management (60-Day Window)
recent_history = {}
cutoff_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            full_history = json.load(f)
            recent_history = {
                expr: date for expr, date in full_history.items() 
                if date >= cutoff_date
            }
    except Exception as e:
        print(f"Warning: Could not read history file: {e}")

used_expressions = list(recent_history.keys())
avoid_clause = ""
if used_expressions:
    avoid_clause = (
        "\nDo NOT use any of the following expressions previously sent in the last 60 days:\n"
        + json.dumps(used_expressions, ensure_ascii=False)
    )

# 3. Prompt Construction
prompt = f"""
Create 5 French expressions at C1 level. Return the answer as JSON in the following exact structure:
[
  {{
    "expression": "the expression in French",
    "ipa": "IPA transcription",
    "example": "example sentence in French",
    "translations": {{
      "ENG": "English",
      "ITA": "Italian",
      "HEB": "Hebrew",
      "SRP": "Serbian",
      "POR": "Portuguese",
      "GER": "German"
    }}
  }}
]
{avoid_clause}
"""

MODEL_NAME = "gemini-3.6-flash"
MAX_RETRIES = 5
response_text = None

# 4. Generate Content with Retries
print(f"Targeting model: {MODEL_NAME}")
for attempt in range(1, MAX_RETRIES + 1):
    try:
        res = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        if res.text:
            response_text = res.text.strip()
            print(f"✅ Success on attempt {attempt}")
            break
    except Exception as e:
        wait_time = attempt * 10
        print(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}. Retrying in {wait_time}s...")
        time.sleep(wait_time)

if not response_text:
    raise Exception(f"Failed to generate content from {MODEL_NAME} after {MAX_RETRIES} attempts.")

if response_text.startswith("```"):
    lines = response_text.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    response_text = "\n".join(lines).strip()

data = json.loads(response_text)

# 5. Save History
today_str = datetime.now().strftime("%Y-%m-%d")
for item in data:
    recent_history[item["expression"].strip().lower()] = today_str

try:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(recent_history, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"Warning: Could not save updated history: {e}")

# 6. Build Telegram Message
message = "🇫🇷 *DAILY FRENCH VOCABULARY - C1 LEVEL*\n\n"
for idx, item in enumerate(data, 1):
    message += f"*[{idx}] {item['expression']}*\n"
    message += f"_IPA: {item['ipa']}_\n"
    message += f"_Example: {item['example']}_\n"
    message += "Translations:\n"
    for lang, translation in item['translations'].items():
        message += f"  • {lang}: {translation}\n"
    message += "\n"

# 7. Post to Telegram
print("Sending text message to Telegram...")
url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": message,
    "parse_mode": "Markdown"
}

res = requests.post(url, json=payload)
print(f"Telegram response status: {res.status_code}")
if res.status_code == 200:
    print("✅ Message sent successfully to Telegram!")
else:
    print(f"❌ Failed to send message: {res.text}")
