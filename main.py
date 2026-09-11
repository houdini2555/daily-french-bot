import os
import json
import time
import asyncio  # Replaced requests with asyncio
from google import genai
from telegram import Bot  # Added Bot import

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

prompt = """
Create 5 French expressions at C1 level. Return the answer as JSON in the following exact structure:
[
  {
    "expression": "the expression in French",
    "ipa": "IPA transcription",
    "example": "example sentence in French",
    "translations": {
      "ENG": "English",
      "ITA": "Italian",
      "HEB": "Hebrew",
      "SRP": "Serbian",
      "POR": "Portuguese",
      "GER": "German"
    }
  }
]
"""

# List of model priorities: if the first is busy, move to the next
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

# --- Format message for Telegram (text only) ---
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

bot = Bot(token=TELEGRAM_TOKEN)

async def main():
    await bot.send_message(
        chat_id=CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )

asyncio.run(main())
print("✅ Message sent successfully to Telegram!")
