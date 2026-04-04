
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# --- CONFIGURAZIONE ---


import os
TOKEN = os.getenv("TELEGRAM_TOKEN")
logging.basicConfig(level=logging.INFO)

# --- STATI DELLA CONVERSAZIONE ---
PRE, POST, TEMPO = range(3)

# --- TESTO INFO KELIM ---
KELIM_INFO = """
ℹ️ *KELIM Score*

Il KELIM è un indicatore matematico che misura la velocità di caduta del marcatore Ca-125.

*Formula:*
`KELIM = ln(Ca125_pre / Ca125_post) / tempo`

*Interpretazione:*
• > 1.0 → Risposta molto buona ✅
• 0.5 – 1.0 → Buona risposta 🟢
• 0.1 – 0.5 → Risposta moderata 🟡
• < 0.1 → Risposta scarsa 🟠
• < 0.0 → Malattia in progressione 🔴
"""

# --- HANDLER /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Benvenuto nel *KELIM Score Calculator* 🧪\n\n"
        "Usa /calcola per iniziare il calcolo\n"
        "Usa /info per sapere cos'è il KELIM Score",
        parse_mode="Markdown"
    )

# --- HANDLER /info ---
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(KELIM_INFO, parse_mode="Markdown")

# --- INIZIO CONVERSAZIONE ---
async def calcola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔬 *Calcolo KELIM Score*\n\n"
        "Inserisci il Ca-125 *PRE-chemioterapia* (mg/dL):\n"
        "_Usa il punto per i decimali, es: 450.5_",
        parse_mode="Markdown"
    )
    return PRE

# --- STEP 1: ricevo PRE ---
async def ricevo_pre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pre = float(update.message.text.replace(",", "."))
        if pre <= 0:
            raise ValueError
        context.user_data["pre"] = pre
        await update.message.reply_text(
            f"✅ Ca-125 PRE: *{pre} mg/dL*\n\n"
            "Ora inserisci il Ca-125 *POST-chemioterapia* (mg/dL):",
            parse_mode="Markdown"
        )
        return POST
    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *450* o *450.5*",
            parse_mode="Markdown"
        )
        return PRE

# --- STEP 2: ricevo POST ---
async def ricevo_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        post = float(update.message.text.replace(",", "."))
        if post <= 0:
            raise ValueError
        context.user_data["post"] = post
        await update.message.reply_text(
            f"✅ Ca-125 POST: *{post} mg/dL*\n\n"
            "Ora inserisci il *tempo in settimane*:",
            parse_mode="Markdown"
        )
        return TEMPO
    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *120* o *45.5*",
            parse_mode="Markdown"
        )
        return POST

# --- STEP 3: ricevo TEMPO e calcolo ---
async def ricevo_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        t = float(update.message.text.replace(",", "."))
        if t <= 0:
            raise ValueError

        pre = context.user_data["pre"]
        post = context.user_data["post"]

        risultato = math.log(pre / post) / t

        # Interpretazione
        if risultato > 1.0:
            commento = "✅ Risposta *molto buona* alla chemioterapia\nRapida riduzione dei livelli di Ca-125"
            emoji = "🟢"
        elif 0.5 <= risultato <= 1.0:
            commento = "🟢 *Buona risposta* alla chemioterapia\nRiduzione significativa dei livelli di Ca-125"
            emoji = "🟢"
        elif 0.1 <= risultato < 0.5:
            commento = "🟡 Risposta *moderata* alla chemioterapia\nRiduzione lenta dei livelli di Ca-125"
            emoji = "🟡"
        elif risultato < 0.0:
            commento = "🔴 *Malattia in progressione*\nI livelli di Ca-125 stanno aumentando nonostante la chemioterapia"
            emoji = "🔴"
        else:
            commento = "🟠 Risposta *scarsa* alla chemioterapia\nRiduzione molto lenta dei livelli di Ca-125"
            emoji = "🟠"

        messaggio = (
            f"📊 *RISULTATO KELIM SCORE* {emoji}\n"
            f"{'─' * 28}\n"
            f"• Ca-125 PRE:  *{pre} mg/dL*\n"
            f"• Ca-125 POST: *{post} mg/dL*\n"
            f"• Tempo:       *{t} settimane*\n"
            f"{'─' * 28}\n"
            f"• KELIM Score: *{risultato:.4f}*\n"
            f"{'─' * 28}\n\n"
            f"{commento}\n\n"
            f"_Usa /calcola per un nuovo calcolo_"
        )

        await update.message.reply_text(messaggio, parse_mode="Markdown")
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *3* o *2.5*",
            parse_mode="Markdown"
        )
        return TEMPO

# --- ANNULLA ---
async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Calcolo annullato.\nUsa /calcola per ricominciare."
    )
    return ConversationHandler.END

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("calcola", calcola)],
        states={
            PRE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_pre)],
            POST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_post)],
            TEMPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_tempo)],
        },
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(conv_handler)

    print("✅ Bot KELIM avviato...")
    app.run_polling()
