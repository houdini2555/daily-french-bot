import os
import time
import requests
from google import genai
from google.genai.errors import APIError
from PIL import Image, ImageDraw, ImageFont

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

prompt = """
צור כרטיסיית לימוד יומית של 5 ביטויים שימושיים בצרפתית ברמת C1 (ללא מונחים טכניים/מופשטים מדי).
לכל ביטוי ספק:
1. הביטוי בצרפתית
2. תעתיק פונטי בינלאומי (IPA)
3. משפט דוגמה בצרפתית
4. תרגום לשפות: אנגלית (ENG), איטלקית (ITA), עברית (HEB), סרבית (SRP), פורטוגזית (POR), וגרמנית (GER).

עצב את התשובה בצורה קריאה, קצרה ונקייה ללא עיצוב מורכב מדי.
"""

response_text = None

# ניסיונות חוזרים עבור המודל הפעיל gemini-3.6-flash
for attempt in range(3):
    try:
        res = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        response_text = res.text
        if response_text:
            break
    except APIError as e:
        print(f"Attempt {attempt + 1} failed with API error: {e}")
        time.sleep(5)
    except Exception as e:
        print(f"Attempt {attempt + 1} failed: {e}")
        time.sleep(5)

if not response_text:
    raise Exception("Failed to generate content from Gemini API.")

# --- יצירת תמונה ---
img_width = 1080
img_height = 1920
image = Image.new("RGB", (img_width, img_height), color=(24, 24, 27))
draw = ImageDraw.Draw(image)

try:
    font = ImageFont.truetype("DejaVuSans.ttf", 22)
except IOError:
    font = ImageFont.load_default()

margin = 40
offset = 50
for line in response_text.split("\n"):
    draw.text((margin, offset), line, font=font, fill=(244, 244, 245))
    offset += 30

image_path = "card.png"
image.save(image_path)

# --- שליחת התמונה לטלגרם ---
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, "rb") as img_file:
    payload = {"chat_id": CHAT_ID}
    files = {"photo": img_file}
    requests.post(url, data=payload, files=files)
