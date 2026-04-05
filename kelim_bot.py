import math
import logging
import os
import sqlite3
import csv
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# --- STATI DELLA CONVERSAZIONE ---
ID_PAZIENTE, PRE, POST, TEMPO = range(4)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("kelim.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS calcoli (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_paziente TEXT,
        ca125_pre REAL,
        ca125_post REAL,
        settimane REAL,
        kelim REAL,
        data TEXT
    )''')
    conn.commit()
    conn.close()

def salva_calcolo(id_paziente, pre, post, t, kelim):
    conn = sqlite3.connect("kelim.db")
    c = conn.cursor()
    c.execute('''INSERT INTO calcoli 
        (id_paziente, ca125_pre, ca125_post, settimane, kelim, data)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (id_paziente, pre, post, t, kelim, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()

def esporta_csv():
    conn = sqlite3.connect("kelim.db")
    c = conn.cursor()
    c.execute("SELECT * FROM calcoli ORDER BY id DESC")
    righe = c.fetchall()
    conn.close()

    filename = "kelim_export.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID", "ID Paziente", "Ca125 PRE", "Ca125 POST", "Settimane", "KELIM", "Data"])
        writer.writerows(righe)
    return filename

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

# --- MENU PRINCIPALE ---
def menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🧪 Nuovo calcolo", callback_data="calcola")],
        [InlineKeyboardButton("📤 Esporta CSV", callback_data="export")],
        [InlineKeyboardButton("ℹ️ Info KELIM", callback_data="info")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLER /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Benvenuto nel *KELIM Score Calculator* 🧪\n\n"
        "Seleziona un'opzione:",
        parse_mode="Markdown",
        reply_markup=menu_keyboard()
    )

# --- HANDLER BOTTONI MENU ---
async def bottone_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text(KELIM_INFO, parse_mode="Markdown")

    elif query.data == "export":
        await gestisci_export(update, context)

    elif query.data == "calcola":
        await query.message.reply_text(
            "🔬 *Calcolo KELIM Score*\n\n"
            "Inserisci l'*ID paziente*:",
            parse_mode="Markdown"
        )
        return ID_PAZIENTE

    elif query.data == "salva":
        id_paziente = context.user_data["id_paziente"]
        pre = context.user_data["pre"]
        post = context.user_data["post"]
        t = context.user_data["t"]
        kelim = context.user_data["kelim"]
        salva_calcolo(id_paziente, pre, post, t, kelim)
        await query.message.reply_text(
            "✅ *Dati salvati nel database!*\n\n"
            "Seleziona un'opzione:",
            parse_mode="Markdown",
            reply_markup=menu_keyboard()
        )

    elif query.data == "non_salvare":
        await query.message.reply_text(
            "❌ Dati non salvati.\n\n"
            "Seleziona un'opzione:",
            reply_markup=menu_keyboard()
        )

    elif query.data == "nuovo":
        await query.message.reply_text(
            "🔬 *Calcolo KELIM Score*\n\n"
            "Inserisci l'*ID paziente*:",
            parse_mode="Markdown"
        )
        return ID_PAZIENTE

# --- STEP 0: ID PAZIENTE ---
async def ricevo_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["id_paziente"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ ID paziente: *{context.user_data['id_paziente']}*\n\n"
        "Inserisci il Ca-125 *PRE-chemioterapia* (mg/dL):\n"
        "_Usa il punto per i decimali, es: 450.5_",
        parse_mode="Markdown"
    )
    return PRE

# --- STEP 1: PRE ---
async def ricevo_pre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pre = float(update.message.text.replace(",", "."))
        if pre <= 0:
            raise ValueError
        context.user_data["pre"] = pre
        await update.message.reply_text(
            f"✅ Ca-125 PRE: *{pre} mg/dL*\n\n"
            "Inserisci il Ca-125 *POST-chemioterapia* (mg/dL):",
            parse_mode="Markdown"
        )
        return POST
    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *450* o *450.5*",
            parse_mode="Markdown"
        )
        return PRE

# --- STEP 2: POST ---
async def ricevo_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        post = float(update.message.text.replace(",", "."))
        if post <= 0:
            raise ValueError
        context.user_data["post"] = post
        await update.message.reply_text(
            f"✅ Ca-125 POST: *{post} mg/dL*\n\n"
            "Inserisci il *tempo in settimane*:",
            parse_mode="Markdown"
        )
        return TEMPO
    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *120* o *45.5*",
            parse_mode="Markdown"
        )
        return POST

# --- STEP 3: TEMPO e CALCOLO ---
async def ricevo_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        t = float(update.message.text.replace(",", "."))
        if t <= 0:
            raise ValueError

        pre = context.user_data["pre"]
        post = context.user_data["post"]
        id_paziente = context.user_data["id_paziente"]
        risultato = math.log(pre / post) / t
        context.user_data["t"] = t
        context.user_data["kelim"] = risultato
        data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")

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
            commento = "🔴 *Malattia in progressione*\nI livelli di Ca-125 stanno aumentando"
            emoji = "🔴"
        else:
            commento = "🟠 Risposta *scarsa* alla chemioterapia\nRiduzione molto lenta dei livelli di Ca-125"
            emoji = "🟠"

        messaggio = (
            f"📊 *RISULTATO KELIM SCORE* {emoji}\n"
            f"{'─' * 28}\n"
            f"• ID paziente:  *{id_paziente}*\n"
            f"• Data:         *{data_ora}*\n"
            f"{'─' * 28}\n"
            f"• Ca-125 PRE:  *{pre} mg/dL*\n"
            f"• Ca-125 POST: *{post} mg/dL*\n"
            f"• Tempo:       *{t} settimane*\n"
            f"{'─' * 28}\n"
            f"• KELIM Score: *{risultato:.4f}*\n"
            f"{'─' * 28}\n\n"
            f"{commento}"
        )

        keyboard = [
            [
                InlineKeyboardButton("💾 Salva", callback_data="salva"),
                InlineKeyboardButton("❌ Non salvare", callback_data="non_salvare")
            ],
            [InlineKeyboardButton("🔄 Nuovo calcolo", callback_data="nuovo")]
        ]

        await update.message.reply_text(
            messaggio,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "❌ Valore non valido. Inserisci un numero positivo, es: *3* o *2.5*",
            parse_mode="Markdown"
        )
        return TEMPO

# --- EXPORT CSV ---
async def gestisci_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        filename = esporta_csv()
        chat_id = update.callback_query.message.chat_id
        with open(filename, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename="kelim_export.csv",
                caption="📤 *Export KELIM Score*",
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.callback_query.message.reply_text(
            "❌ Nessun dato da esportare ancora."
        )

# --- ANNULLA ---
async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Calcolo annullato.",
        reply_markup=menu_keyboard()
    )
    return ConversationHandler.END

# --- MAIN ---
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("calcola", lambda u, c: u.message.reply_text(
                "Inserisci l'*ID paziente*:", parse_mode="Markdown"
            )),
            CallbackQueryHandler(bottone_menu, pattern="^calcola$"),
            CallbackQueryHandler(bottone_menu, pattern="^nuovo$"),
        ],
        states={
            ID_PAZIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_id)],
            PRE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_pre)],
            POST:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_post)],
            TEMPO:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevo_tempo)],
        },
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", gestisci_export))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(bottone_menu))

    print("✅ Bot KELIM avviato...")
    app.run_polling()
