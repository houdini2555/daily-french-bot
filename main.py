import os
import requests
from google import genai

# שליפת מפתחות
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# אתחול הלקוח
client = genai.Client(api_key=GEMINI_KEY)

# פרומפט ליצירת התוכן
prompt = """
צור כרטיסיית לימוד יומית של 5 ביטויים שימושיים בצרפתית ברמת C1 (ללא מונחים טכניים/מופשטים מדי).
לכל ביטוי ספק:
1. הביטוי בצרפתית
2. תעתיק פונטי בינלאומי (IPA)
3. משפט דוגמה בצרפתית
4. תרגום לשפות: אנגלית (ENG), איטלקית (ITA), עברית (HEB), סרבית (SRP), פורטוגזית (POR), וגרמנית (GER).

עצב את התשובה בצורה קריאה ונקייה המתאימה להודעת טלגרם (השתמש ב-Bold ובאייקונים).
"""

# קריאה למודל היציב gemini-1.5-flash
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents=prompt,
)

# שליחה לטלגרם
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": response.text,
    "parse_mode": "Markdown"
}

requests.post(url, json=payload)
