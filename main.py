import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
from google import genai
from google.genai import types

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# Sanitize token in case full URL or extra characters were passed into environment secret
if "telegram.org" in TELEGRAM_TOKEN:
    match = re.search(r"bot([^/]+)", TELEGRAM_TOKEN)
    if match:
        TELEGRAM_TOKEN = match.group(1)

# Clean out any leftover markdown formatting/asterisks from env vars
TELEGRAM_TOKEN = re.sub(r"[^\w:-]", "", TELEGRAM_TOKEN)

HISTORY_FILE = "history.json"
client = genai.Client(api_key=GEMINI_KEY)

# --- History Management (60 Days) ---
cutoff_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
recent_history = {}

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
    avoid_clause = f"\nDo NOT use any of the following expressions previously sent in the last 60 days:\n" + json.dumps(used_expressions, ensure_ascii=False)

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

models_to_try = ["gemini-2.5-flash", "gemini-2.5-pro"]
response_text = None

for model in models_to_try:
    print(f"Trying model: {model}")
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
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

# --- Save New Expressions to History ---
today_str = datetime.now().strftime("%Y-%m-%d")
for item in data:
    recent_history[item["expression"].strip().lower()] = today_str

try:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(recent_history, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"Warning: Could not save updated history: {e}")

# --- Format message for Telegram ---
message = "🇫🇷 *DAILY FRENCH VOCABULARY - C1 LEVEL*\n\n"
for idx, item in enumerate(data, 1):
    message += f"*[{idx}] {item['expression']}*\n"
    message += f"_IPA: {item['ipa']}_\n"
    message += f"_Example: {item['example']}_\n"
    message += "Translations:\n"
    for lang, translation in item['translations'].items():
        message += f"  • {lang}: {translation}\n"
    message += "\n"

# --- Send text message to Telegram ---
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
