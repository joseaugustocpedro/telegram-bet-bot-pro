import os
import logging
import threading
from decimal import Decimal

from flask import Flask

import psycopg2
import psycopg2.extras

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)


# ============================================================
# CONFIG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

INITIAL_BANKROLL = float(
    os.environ.get("INITIAL_BANKROLL", "1000")
)

CURRENCY = os.environ.get("CURRENCY", "R$")


# ============================================================
# FLASK
# ============================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return {
        "status": "online",
        "bot": "telegram-bet-bot-pro"
    }, 200


def run_flask():

    port = int(os.environ.get("PORT", 10000))

    web_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )


# ============================================================
# POSTGRESQL
# ============================================================

def get_conn():

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def criar_banco():

    with get_conn() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id BIGSERIAL PRIMARY KEY,

                chat_id BIGINT NOT NULL,

                sport TEXT NOT NULL,

                market TEXT NOT NULL,

                event TEXT NOT NULL,

                tipster TEXT,

                odds NUMERIC(10,2) NOT NULL,

                stake NUMERIC(14,2) NOT NULL,

                status TEXT NOT NULL,

                profit NUMERIC(14,2) NOT NULL,

                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """)

    logger.info("Banco pronto")


# ============================================================
# HELPERS
# ============================================================

def numero(valor):

    if valor is None:
        return 0.0

    if isinstance(valor, Decimal):
        return float(valor)

    return float(valor)


def calcular_lucro(odd, stake, status):

    status = status.upper()

    if status == "GREEN":
        return round((odd - 1) * stake, 2)

    if status == "RED":
        return round(-stake, 2)

    if status == "VOID":
        return 0

    if status == "HALF_GREEN":
        return round(((odd - 1) * stake) / 2, 2)

    if status == "HALF_RED":
        return round(-stake / 2, 2)

    return 0


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = f"""
🤖 BOT PROFISSIONAL DE GESTÃO DE BANCA

Comandos:

/add
/resumo
/analise
/help

━━━━━━━━━━━━━━━━━━

EXEMPLO:

/add Futebol | Match Odds | Arsenal vs Chelsea | 2.10 | 50 | GREEN | Tipster João
"""

    await update.message.reply_text(texto)


# ============================================================
# HELP
# ============================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
📚 COMANDOS

/start
/help

/add esporte | mercado | evento | odd | stake | status | tipster opcional

/resumo

/analise esporte
/analise mercado
/analise tipster
"""

    await update.message.reply_text(texto)


# ============================================================
# ADD
# ============================================================

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        chat_id = update.effective_chat.id

        mensagem = update.message.text.replace(
            "/add",
            "",
            1
        ).strip()

        partes = [p.strip() for p in mensagem.split("|")]

        if len(partes) not in [6, 7]:

            await update.message.reply_text(
                "Formato inválido."
            )

            return

        sport = partes[0]
        market = partes[1]
        event = partes[2]

        odds = float(
            partes[3].replace(",", ".")
        )

        stake = float(
            partes[4].replace(",", ".")
        )

        status = partes[5].upper()

        tipster = None

        if len(partes) == 7:
            tipster = partes[6]

        profit = calcular_lucro(
            odds,
            stake,
            status
        )

        with get_conn() as conn:

            with conn.cursor() as cursor:

                cursor.execute("""
                INSERT INTO bets (
                    chat_id,
                    sport,
                    market,
                    event,
                    tipster,
                    odds,
                    stake,
                    status,
                    profit
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                RETURNING id;
                """, (
                    chat_id,
                    sport,
                    market,
                    event,
                    tipster,
                    odds,
                    stake,
                    status,
                    profit
                ))

                bet_id = cursor.fetchone()["id"]

        await update.message.reply_text(
            f"""
✅ BET REGISTRADA

🆔 ID: {bet_id}

🏆 {sport}

🎯 {market}

📌 {event}

👤 {tipster or 'Sem tipster'}

📊 Odd: {odds:.2f}

💵 Stake: {CURRENCY} {stake:.2f}

📈 Resultado: {CURRENCY} {profit:.2f}
"""
        )

    except Exception as erro:

        logger.exception(erro)

        await update.message.reply_text(
            f"Erro:\n{erro}"
        )


# ============================================================
# RESUMO
# ============================================================

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    with get_conn() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
            SELECT

                COUNT(*) AS total,

                COALESCE(SUM(stake),0) AS apostado,

                COALESCE(SUM(profit),0) AS lucro,

                COALESCE(AVG(odds),0) AS odd_media,

                COUNT(*) FILTER (
                    WHERE status='GREEN'
                ) AS greens,

                COUNT(*) FILTER (
                    WHERE status='RED'
                ) AS reds

            FROM bets

            WHERE chat_id=%s;
            """, (chat_id,))

            dados = cursor.fetchone()

    total = int(dados["total"])

    apostado = numero(
        dados["apostado"]
    )

    lucro = numero(
        dados["lucro"]
    )

    odd_media = numero(
        dados["odd_media"]
    )

    greens = int(
        dados["greens"]
    )

    reds = int(
        dados["reds"]
    )

    roi = (
        lucro / apostado * 100
        if apostado > 0 else 0
    )

    banca_atual = (
        INITIAL_BANKROLL + lucro
    )

    winrate = (
        greens / (greens + reds) * 100
        if (greens + reds) > 0 else 0
    )

    texto = f"""
📊 DASHBOARD

🏦 Banca Atual:
{CURRENCY} {banca_atual:.2f}

💰 Lucro:
{CURRENCY} {lucro:.2f}

🎯 Apostado:
{CURRENCY} {apostado:.2f}

📈 ROI:
{roi:.2f}%

✅ Win Rate:
{winrate:.2f}%

📌 Odd Média:
{odd_media:.2f}

━━━━━━━━━━━━━━

🧾 Bets:
{total}

🟢 Greens:
{greens}

🔴 Reds:
{reds}
"""

    await update.message.reply_text(texto)


# ============================================================
# ANALISE
# ============================================================

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not context.args:

        await update.message.reply_text(
            "Use:\n"
            "/analise esporte\n"
            "/analise mercado\n"
            "/analise tipster"
        )

        return

    tipo = context.args[0].lower()

    campos = {
        "esporte": "sport",
        "mercado": "market",
        "tipster": "tipster"
    }

    if tipo not in campos:

        await update.message.reply_text(
            "Filtro inválido."
        )

        return

    campo = campos[tipo]

    with get_conn() as conn:

        with conn.cursor() as cursor:

            cursor.execute(f"""
            SELECT

                {campo} AS categoria,

                COUNT(*) AS total,

                COALESCE(
                    SUM(stake),0
                ) AS apostado,

                COALESCE(
                    SUM(profit),0
                ) AS lucro

            FROM bets

            WHERE chat_id=%s

            GROUP BY {campo}

            ORDER BY lucro DESC;
            """, (chat_id,))

            linhas = cursor.fetchall()

    if not linhas:

        await update.message.reply_text(
            "Sem dados."
        )

        return

    resposta = f"📊 ANÁLISE POR {tipo.upper()}\n\n"

    for linha in linhas:

        categoria = (
            linha["categoria"]
            or "Sem informação"
        )

        apostado = numero(
            linha["apostado"]
        )

        lucro = numero(
            linha["lucro"]
        )

        roi = (
            lucro / apostado * 100
            if apostado > 0 else 0
        )

        resposta += (
            f"📌 {categoria}\n"
            f"💰 Lucro: {CURRENCY} {lucro:.2f}\n"
            f"📈 ROI: {roi:.2f}%\n"
            f"━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(resposta)


# ============================================================
# MAIN
# ============================================================

def main():

    criar_banco()

    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    flask_thread.start()

    app = ApplicationBuilder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("add", add)
    )

    app.add_handler(
        CommandHandler("resumo", resumo)
    )

    app.add_handler(
        CommandHandler("analise", analise)
    )

    logger.info("BOT ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
