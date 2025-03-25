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

# === Emojis por tipo e prioridade ===
tipo_emojis = {
    "médico": "🏥",
    "trabalho": "💼",
    "pessoal": "👤",
    "reunião": "📅",
    "evento": "🎉",
    "viagem": "✈️",
    "estudo": "📚",
    "lazer": "🎡",
    "outro": "📌"
}

prioridade_emojis = {
    "alta": "🔥",
    "média": "⚠️",
    "baixa": "🧘"
}

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


def parse_hora_com_flexibilidade(data_str, hora_str):
    formatos = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
    for fmt in formatos:
        try:
            return fuso_brasil.localize(datetime.strptime(f"{data_str} {hora_str}", fmt))
        except ValueError:
            continue
    raise ValueError(f"Formato de hora inválido: {hora_str}")

df["datahora"] = df.apply(
    lambda row: parse_hora_com_flexibilidade(row["data"], row["hora"]),
    axis=1
)

df["dias_restantes"] = df["datahora"].apply(lambda dt: (dt.date() - agora.date()).days)
df["horas_restantes"] = df["datahora"].apply(lambda dt: (dt - agora).total_seconds() / 3600)

for _, row in df.iterrows():
    dias = row["dias_restantes"]
    horas = row["horas_restantes"]
    compromisso = row["compromisso"]
    local = row.get("local", "").strip()
    tipo = row.get("tipo", "outro").strip().lower()
    prioridade = row.get("prioridade", "").strip().lower()
    obs = row.get("obs", "").strip()

    emoji_tipo = tipo_emojis.get(tipo, "📌")
    emoji_prioridade = prioridade_emojis.get(prioridade, "")

    local_msg = f"\n📍 Local: {local}" if local else ""
    tipo_msg = f"\n🏷️ Tipo: {emoji_tipo} {tipo.capitalize()}" if tipo else ""
    prioridade_msg = f"\n🔺 Prioridade: {emoji_prioridade} {prioridade.capitalize()}" if prioridade else ""
    obs_msg = f"\n📝 Obs: {obs}" if obs else ""

    data_fmt = row["datahora"].strftime("%d/%m às %H:%M")

    destinatarios_raw = row.get("destinatarios", "")
    destinatarios = [d.strip().lower() for d in destinatarios_raw.split(",")]
    print("Destinatários normalizados:", destinatarios)

    mensagem = None
    if 1 <= dias <= 3:
        mensagem = f"📌 Faltam *{dias} dias* para: *{compromisso}*\n🗓️ {data_fmt}{local_msg}{tipo_msg}{prioridade_msg}{obs_msg}"
    elif dias == 0 and 2.5 <= horas <= 3.5:
        mensagem = f"⏰ Lembrete! Daqui a *3 horas* você tem: *{compromisso}*\n🗓️ {data_fmt}{local_msg}{tipo_msg}{prioridade_msg}{obs_msg}"

    if mensagem:
        if "priscilla" in destinatarios:
            print("→ Enviando para Priscilla")
            enviar_telegram(ID_PRISCILLA, mensagem)
        if "danilo" in destinatarios:
            print("→ Enviando para Danilo")
            enviar_telegram(ID_DANILO, mensagem)
