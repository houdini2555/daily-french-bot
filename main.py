import os
import requests
from google import genai
from PIL import Image, ImageDraw, ImageFont

# שליפת מפתחות
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

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
)

text_content = response.text

# --- יצירת תמונה מתוך הטקסט ---
img_width = 1080
img_height = 1920
image = Image.new("RGB", (img_width, img_height), color=(24, 24, 27)) # רקע כהה מודרני
draw = ImageDraw.Draw(image)

# טעינת פונט ברירת מחדל
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 22)
except IOError:
    font = ImageFont.load_default()

# כתיבת הטקסט על התמונה
margin = 40
offset = 50
for line in text_content.split("\n"):
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
