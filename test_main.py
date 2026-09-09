import os
import json
import requests
from html2image import Html2Image

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Mock data for testing (bypasses Gemini API)
data = [
    {
        "expression": "C'est du gâteau",
        "ipa": "[sɛ dy ɡɑto]",
        "example": "Cet examen était du gâteau pour lui.",
        "translations": {
            "ENG": "It's a piece of cake",
            "ITA": "È facile come bere un bicchiere d'acqua",
            "HEB": "זה קל מאוד",
            "SRP": "To je lako",
            "POR": "É moleza",
            "GER": "Das ist ein Kinderspiel"
        }
    },
    {
        "expression": "Avoir le trac",
        "ipa": "[avwaʁ lə tʁak]",
        "example": "J'ai le trac avant ma présentation.",
        "translations": {
            "ENG": "To have stage fright",
            "ITA": "Avere le farfalle nello stomaco",
            "HEB": "להיות עצבני",
            "SRP": "Biti nervozan",
            "POR": "Ter frio na espinha",
            "GER": "Lampenfieber haben"
        }
    },
    {
        "expression": "Avoir un chat dans la gorge",
        "ipa": "[avwaʁ œ̃ ʃa dɑ̃ la ɡɔʁʒ]",
        "example": "Excuse-moi, j'ai un chat dans la gorge.",
        "translations": {
            "ENG": "To have a frog in one's throat",
            "ITA": "Avere il gatto in gola",
            "HEB": "להיות שיהוק",
            "SRP": "Imati mačku u grlu",
            "POR": "Ter um sapo na garganta",
            "GER": "Einen Frosch im Hals haben"
        }
    },
    {
        "expression": "Mettre les pieds dans le plat",
        "ipa": "[mɛtʁ le pje dɑ̃ lə pla]",
        "example": "Il a mis les pieds dans le plat en posant cette question.",
        "translations": {
            "ENG": "To put one's foot in one's mouth",
            "ITA": "Mettere i piedi in una scodella",
            "HEB": "להגיד משהו בחוסר טact",
            "SRP": "Napraviti grešku",
            "POR": "Meter os pés pelas mãos",
            "GER": "Ins Fettnäpfchen treten"
        }
    },
    {
        "expression": "Être sur le fil du rasoir",
        "ipa": "[ɛtʁ syʁ lə fil dy ʁazwaʁ]",
        "example": "La situation politique est sur le fil du rasoir.",
        "translations": {
            "ENG": "To be on a knife's edge",
            "ITA": "Essere sul filo del rasoio",
            "HEB": "להיות במצב קריטי",
            "SRP": "Biti na liniji između",
            "POR": "Estar na corda bamba",
            "GER": "Auf Messers Schneide stehen"
        }
    }
]

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
print("Rendering HTML to image...")
hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])
hti.output_path = '.'
hti.screenshot(html_str=full_html, save_as='card.png', size=(810, 1400))
print("✓ Image rendered successfully: card.png")

# --- שליחה לטלגרם ---
print("\nTesting Telegram API URL format...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
print(f"URL format check: {url[:50]}...{url[-20:]}")

if TELEGRAM_TOKEN and CHAT_ID:
    print("\nSending to Telegram...")
    with open("card.png", "rb") as img_file:
        res = requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img_file})
        print(f"✓ Telegram response status: {res.status_code}")
        if res.status_code != 200:
            print(f"Response: {res.text}")
else:
    print("⚠ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set - skipping actual send")
    print("✓ URL format is valid and properly constructed")
