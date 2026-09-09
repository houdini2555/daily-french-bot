import os
import json
import time
import random
import sys
import traceback
import requests
from google import genai
from html2image import Html2Image

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Validate environment variables
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is not set")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

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

# רשימת מודלים: משתמשים רק ב-gemini-3.6-flash
model = "gemini-3.6-flash"

# Retry/backoff configuration - 10 attempts with progressive backoff
MAX_ATTEMPTS_PER_MODEL = 10

# Backoff schedule in seconds: [attempt1, attempt2, ..., attempt10]
BACKOFF_SCHEDULE = [
    0,          # attempt 1: no wait
    10,         # attempt 2: 10s
    30,         # attempt 3: 30s
    60,         # attempt 4: 60s (1 min)
    180,        # attempt 5: 180s (3 min)
    360,        # attempt 6: 360s (6 min) - increase 6
    540,        # attempt 7: 540s (9 min = 3 more minutes)
    900,        # attempt 8: 900s (15 min) - 5 minutes more
    1500,       # attempt 9: 1500s (25 min) - 15 minutes more
    2700,       # attempt 10: 2700s (45 min) - wait but continue for 35 minutes more
]


def _is_retryable_error(err_text: str) -> bool:
    """Return True if the error text suggests a transient/retryable problem."""
    if not err_text:
        return False
    t = err_text.lower()
    # Non-retryable: not found / removed models
    if "404" in t or "not_found" in t or "no longer available" in t or "not found" in t:
        return False
    # Retryable: server errors, rate limit, unavailable, timeout
    if "503" in t or "unavailable" in t or "rate" in t or "rate limit" in t or "429" in t or "timeout" in t or "temporar" in t:
        return True
    # Fallback: if it contains '5'xx but not 404
    if "5" in t:
        return True
    return False


def generate_with_retries(model: str, prompt: str) -> str | None:
    """Try to generate content from the given model with retries and progressive backoff.

    Returns the response text on success, or None if all attempts fail or if the error is non-retryable.
    """
    for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
        try:
            print(f"[{model}] Attempt {attempt}/{MAX_ATTEMPTS_PER_MODEL}...")
            res = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            # Some SDKs provide .text, some .response; follow existing behavior
            text = getattr(res, "text", None) or getattr(res, "response", None) or None
            if text:
                return text.strip()
            # If no text but no exception, treat as failure and retry
            err_msg = f"empty response from model {model}"
            print(f"[{model}] {err_msg}")
            # continue to retry
        except Exception as e:
            # Try to extract useful info from the exception
            err_text = "".join(traceback.format_exception_only(type(e), e))
            print(f"[{model}] Error on attempt {attempt}: {err_text}")

            # If the error is non-retryable (e.g., 404 NOT_FOUND for a model), stop trying this model
            if not _is_retryable_error(err_text):
                print(f"[{model}] Non-retryable error detected. Skipping remaining attempts for this model.")
                return None

            # Otherwise use the backoff schedule
            if attempt < MAX_ATTEMPTS_PER_MODEL:
                wait_time = BACKOFF_SCHEDULE[attempt]
                print(f"[{model}] Retryable error. Waiting {wait_time}s ({wait_time//60}m {wait_time%60}s) before next attempt...")
                time.sleep(wait_time)
            else:
                print(f"[{model}] Attempt {attempt} failed. No more retries available.")

    print(f"[{model}] All attempts exhausted.")
    return None


response_text = None
print(f"Trying model: {model}")
result = generate_with_retries(model, prompt)
if result:
    response_text = result
    print(f"Successfully got response from {model}")
else:
    print(f"No usable response from {model}.")

if not response_text:
    # Send a Telegram notification about failure and exit with non-zero code so CI still fails but with better context
    failure_message = "Daily French Bot: failed to generate content from Gemini model. See logs for details."
    try:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(tg_url, data={"chat_id": CHAT_ID, "text": failure_message})
        print("Sent failure notification to Telegram.")
    except Exception as e:
        print(f"Failed to send Telegram failure notification: {e}")
    # Exit with a clear message
    print("Exiting: could not obtain model output from Gemini model.")
    sys.exit(1)

# If the model returned backticks-wrapped JSON, strip them
if response_text.startswith("```"):
    lines = response_text.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    response_text = "\n".join(lines).strip()

# Try parsing JSON and handle parse errors
try:
    data = json.loads(response_text)
except Exception as e:
    print(f"Failed to parse JSON from model response: {e}")
    # send response_text to Telegram for debugging
    debug_msg = "Daily French Bot: Model returned invalid JSON. Dumping response (truncated):\n" + (response_text[:1900] + "..." if len(response_text) > 1900 else response_text)
    try:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(tg_url, data={"chat_id": CHAT_ID, "text": debug_msg})
        print("Sent debug response to Telegram.")
    except Exception as e2:
        print(f"Failed to send debug response to Telegram: {e2}")
    # fail loudly for CI
    raise

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
        <div class="example">\"{item['example']}\"</div>
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

# --- שליחה לטלגרם ---
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
print(f"Sending to Telegram URL: https://api.telegram.org/bot****/sendPhoto")
with open("card.png", "rb") as img_file:
    res = requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img_file})
    print(f"Telegram response status: {res.status_code}")
