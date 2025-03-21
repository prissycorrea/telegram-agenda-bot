import pandas as pd
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pytz
import os
import json
import requests

# === Google Sheets ===
creds_dict = json.loads(os.getenv("GSHEETS_CREDENTIALS_JSON"))
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open("agenda").sheet1
records = sheet.get_all_records()
df = pd.DataFrame(records)
df.columns = df.columns.str.strip().str.lower()

# === Telegram ===
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ID_PRISCILLA = os.getenv("TELEGRAM_PRISCILLA_ID")
ID_DANILO = os.getenv("TELEGRAM_DANILO_ID")

# === Função de envio ===
def enviar_telegram(chat_id, msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=data)
    print(f"Enviado para {chat_id}: {msg} | Status: {r.status_code}")

# === Lógica de agenda ===
fuso_brasil = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_brasil)

df["datahora"] = df.apply(lambda row: datetime.strptime(f"{row['data']} {row['hora']}", "%Y-%m-%d %H:%M"), axis=1)
df["dias_restantes"] = df["datahora"].apply(lambda dt: (dt.date() - agora.date()).days)
df["horas_restantes"] = df["datahora"].apply(lambda dt: (dt - agora).total_seconds() / 3600)

for _, row in df.iterrows():
    dias = row["dias_restantes"]
    horas = row["horas_restantes"]
    compromisso = row["compromisso"]
    data_fmt = row["datahora"].strftime("%d/%m às %H:%M")
    destinatarios = [d.strip().lower() for d in row.get("destinatarios", "").split(",")]

    mensagem = None
    if dias in [7, 5, 3, 1]:
        mensagem = f"📌 Faltam *{dias} dias* para: *{compromisso}*\n🗓️ {data_fmt}"
    elif dias == 0 and 2.5 <= horas <= 3.5:
        mensagem = f"⏰ Lembrete! Daqui a *3 horas* você tem: *{compromisso}*\n🗓️ {data_fmt}"

    if mensagem:
        if "priscilla" in destinatarios:
            enviar_telegram(ID_PRISCILLA, mensagem)
        if "danilo" in destinatarios:
            enviar_telegram(ID_DANILO, mensagem)
