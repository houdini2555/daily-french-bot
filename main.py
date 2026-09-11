import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from google import genai
from telegram import Bot

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HISTORY_FILE = "history.json"
DAYS_TO_KEEP = 60

# --- 1. טעינת היסטוריה וסינון ביטויים ישנים מ-60 יום ---
history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"Warning: Could not read history file: {e}")

cutoff_date = (datetime.now() - timedelta(days=DAYS_TO_KEEP)).strftime("%Y-%m-%d")
# שומרים רק ביטויים מה-60 ימים האחרונים
recent_history = [item for item in history if item.get("date", "") >= cutoff_date]
used_expressions = [item["expression"] for item in recent_history]

# --- 2. עדכון הפרומפט ל-Gemini ---
prompt = f"""
Create 5 French expressions at C1 level.

CRITICAL REQUIREMENT:
Do NOT use any of the following expressions:
{json.dumps(used_expressions, ensure_ascii=False)}

Return the answer as JSON in the following exact structure:
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
"""

client = genai.Client(api_key=GEMINI_KEY)
models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
response_text = None

for model in models_to_try:
    print(f"Trying model: {model}")
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json"}
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
    raise Exception("Failed to generate content from all Gemini models.")

if response_text.startswith("```"):
    lines = response_text.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    response_text = "\n".join(lines).strip()

data = json.loads(response_text)

# --- 3. עיצוב ושליחה ל-Telegram ---
message = "🇫🇷 *DAILY FRENCH VOCABULARY - C1 LEVEL*\n\n"
for idx, item in enumerate(data, 1):
    message += f"*[{idx}] {item['expression']}*\n"
    message += f"_IPA: {item['ipa']}_\n"
    message += f"_Example: {item['example']}_\n"
    message += "Translations:\n"
    for lang, translation in item['translations'].items():
        message += f"  • {lang}: {translation}\n"
    message += "\n"

print("Sending text message to Telegram...")
bot = Bot(token=TELEGRAM_TOKEN)

async def main():
    await bot.send_message(
        chat_id=CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )

asyncio.run(main())
print("✅ Message sent successfully to Telegram!")

# --- 4. שמירת הביטויים החדשים לקובץ ההיסטוריה ---
today_str = datetime.now().strftime("%Y-%m-%d")
for item in data:
    recent_history.append({
        "expression": item["expression"],
        "date": today_str
    })

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(recent_history, f, ensure_ascii=False, indent=2)

print(f"Saved {len(data)} new expressions to history.")
