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

HISTORY_FILE = "words_history.json"
DAYS_TO_KEEP = 60

# --- 1. Load history & filter entries older than 60 days ---
history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"Warning: Could not read history file: {e}")

cutoff_date = (datetime.now() - timedelta(days=DAYS_TO_KEEP)).strftime("%Y-%m-%d")
recent_history = [item for item in history if item.get("date", "") >= cutoff_date]
used_words = [item["word"] for item in recent_history]

# --- 2. Prompt for Gemini ---
prompt = f"""
Generate 5 French vocabulary words at B2 or C1 level.
For each word, provide:
- The word in French
- Level (B2 or C1)
- IPA transcription
- English definition
- An example sentence in French showing how to use the word
- English translation of the example sentence

CRITICAL REQUIREMENT:
Do NOT use any of the following previously sent words:
{json.dumps(used_words, ensure_ascii=False)}

Return the answer strictly as a JSON list with this exact structure:
[
  {{
    "word": "French word",
    "level": "B2 or C1",
    "ipa": "IPA transcription",
    "definition_eng": "English definition",
    "example": "French example sentence",
    "example_translation_eng": "English translation of the example sentence"
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

# --- 3. Format message in English for Telegram ---
message = "📚 *DAILY FRENCH VOCABULARY (B2/C1)*\n\n"

for idx, item in enumerate(data, 1):
    message += f"*{idx}. {item['word']}* [{item['level']}]\n"
    message += f"IPA: _{item['ipa']}_\n"
    message += f"Meaning: {item['definition_eng']}\n"
    message += f"Usage: _{item['example']}_\n"
    message += f"Translation: {item['example_translation_eng']}\n\n"

# --- 4. Send message to Telegram ---
print("Sending vocabulary words to Telegram...")
bot = Bot(token=TELEGRAM_TOKEN)

async def main():
    await bot.send_message(
        chat_id=CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )

asyncio.run(main())
print("✅ Words sent successfully to Telegram!")

# --- 5. Save used words to history ---
today_str = datetime.now().strftime("%Y-%m-%d")

for item in data:
    recent_history.append({"word": item["word"], "date": today_str})

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(recent_history, f, ensure_ascii=False, indent=2)

print(f"Saved updated history to {HISTORY_FILE}.")
