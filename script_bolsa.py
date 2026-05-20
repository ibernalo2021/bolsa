import contextlib
import datetime
import os
import sys
import threading
import time

import pandas_ta as ta
import pytz
import requests
import yfinance as yf


def cargar_dotenv(ruta=".env"):
    if not os.path.exists(ruta):
        return

    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue

            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")

            if clave and clave not in os.environ:
                os.environ[clave] = valor


def cargar_bots_desde_entorno():
    bots = []
    faltantes_bot_1 = []

    for indice in range(1, 6):
        bot = {
            "token": os.getenv(f"TELEGRAM_BOT_{indice}_TOKEN"),
            "chat_id": os.getenv(f"TELEGRAM_BOT_{indice}_CHAT_ID"),
            "nombre": os.getenv(f"TELEGRAM_BOT_{indice}_NAME", f"Bot {indice}"),
        }

        if indice == 1:
            if not bot["token"]:
                faltantes_bot_1.append("TELEGRAM_BOT_1_TOKEN")
            if not bot["chat_id"]:
                faltantes_bot_1.append("TELEGRAM_BOT_1_CHAT_ID")

        if bot["token"] and bot["chat_id"]:
            bots.append(bot)
        elif bot["token"] or bot["chat_id"]:
            print(
                f"Aviso: el Bot {indice} fue ignorado porque su configuracion esta incompleta. "
                f"Debes definir TELEGRAM_BOT_{indice}_TOKEN y TELEGRAM_BOT_{indice}_CHAT_ID para activarlo."
            )

    if faltantes_bot_1:
        raise RuntimeError(
            "Faltan variables de entorno requeridas para el bot principal: "
            + ", ".join(faltantes_bot_1)
        )

    return bots


def entorno_activo(nombre):
    return os.getenv(nombre, "").strip().lower() in {"1", "true", "yes", "si", "on"}


cargar_dotenv()
BOTS = cargar_bots_desde_entorno()
NY_TZ = pytz.timezone("America/New_York")


SECTORES = {
    "METALES & REFUGIO": ["GLD", "SLV", "GOLD", "NEM", "FCX", "AU", "AGI", "PAAS", "GFI", "WPM", "FNV", "KGC"],
    "URANIO & ENERGIA": ["CCJ", "UEC", "NFE", "XOM", "CVX", "BOIL", "UNG", "SRUUF", "DNN", "SHEL", "BP", "TTE", "COP", "SLB", "PBR", "EOG", "OXY", "VLO", "MPC", "D", "URNM", "URA"],
    "BIG TECH & IA": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL", "ADBE", "CRM", "NFLX", "CSCO", "ACN", "IBM", "INTU", "SAP", "NOW", "PLTR", "UBER", "SNOW", "PANW", "NET", "TEAM", "WDAY"],
    "SEMICONDUCTORES": ["TSM", "AMD", "ASML", "QCOM", "TXN", "MU", "INTC", "ADI", "LRCX", "AMAT", "KLAC", "MCHP", "NXPI", "MRVL", "STX", "WDC", "ARM", "NVTS", "GFS"],
    "FINANZAS & CRIPTO": ["JPM", "BAC", "WFC", "C", "GS", "MS", "V", "MA", "AXP", "PYPL", "BLK", "BX", "SCHW", "BRK-B", "NU", "COIN", "HOOD", "SOFI", "MSTR", "MARA", "RIOT", "IBIT"],
    "SALUD & BIO": ["LLY", "NVO", "UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "DHR", "ABT", "AMGN", "ISRG", "VRTX", "BMY", "GILD", "ZTS", "MDT", "SYK", "ELV", "CI", "HCA", "BSX"],
    "CONSUMO & RETAIL": ["WMT", "COST", "HD", "LOW", "TGT", "KO", "PEP", "NKE", "EL", "PM", "MO", "PG", "CL", "SBUX", "MDLZ", "TJX", "DG", "DLTR", "LULU", "CROX", "VSCO", "EBAY"],
    "INDUSTRIA & AERO": ["CAT", "DE", "HON", "GE", "MMM", "UNP", "UPS", "FDX", "BA", "LMT", "RTX", "NOC", "GD", "ETN", "EMR", "WM", "RSG", "TT", "CARR", "ASTS", "SPCE"],
    "COMUNICACION & MEDIA": ["DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "WBD", "SPOT", "LYV", "ROKU", "TME", "BIDU", "BABA", "JD", "PDD", "SE"],
    "REAL ESTATE & RIESGO": ["NEE", "DUK", "AMT", "PLD", "CCI", "EQIX", "PLUG", "QS", "RIVN", "LCID", "DNA", "OPEN", "UPST", "AFRM", "PATH", "DKNG", "QUBT", "QBTS", "LUMN", "CACC"],
    "VARIOS": ["BRBR", "SHLS", "RBLX", "OUST", "USAR", "ONDS", "BL"],
}

ACCIONES_A_VIGILAR = [ticker for sublist in SECTORES.values() for ticker in sublist]
PALABRAS_CLAVE_NOTICIAS = [
    "EARNINGS",
    "SEC",
    "LAWSUIT",
    "CRASH",
    "HALT",
    "BUYOUT",
    "ACQUISITION",
    "ALERT",
    "FRAUD",
    "BANKRUPTCY",
]


def ahora_ny():
    return datetime.datetime.now(NY_TZ)


def enviar_mensaje(texto):
    hilos = []

    def _disparar_y_validar(bot_info, msg):
        try:
            url = f"https://api.telegram.org/bot{bot_info['token']}/sendMessage"
            payload = {"chat_id": bot_info["chat_id"], "text": msg, "parse_mode": "Markdown"}
            response = requests.post(url, data=payload, timeout=12)
            if response.status_code == 200:
                print(f"[EXITO] Mensaje enviado a: {bot_info['nombre']}")
            else:
                print(f"[FALLO] {bot_info['nombre']} error {response.status_code}: {response.text}")
        except Exception as error:
            print(f"[ERROR DE RED] Conexion fallida con {bot_info['nombre']}: {error}")

    for bot in BOTS:
        hilo = threading.Thread(target=_disparar_y_validar, args=(bot, texto))
        hilo.start()
        hilos.append(hilo)

    for hilo in hilos:
        hilo.join()


def obtener_noticias_ticker(ticker):
    try:
        asset = yf.Ticker(ticker)
        news = asset.news
        if not news:
            return "No se encontraron titulares de prensa recientes para este activo."

        texto_noticias = ""
        for i, item in enumerate(news[:3], start=1):
            titulo = item.get("title", "Sin titulo")
            link = item.get("link", "#")
            texto_noticias += f"{i}. [{titulo}]({link})\n"
        return texto_noticias
    except Exception:
        return "Error temporal al conectar con el servidor de noticias."


def analizar_mercado_quirurgico(es_cierre=False):
    tipo = "ALERTA DE PRE-CIERRE (MOC)" if es_cierre else "ESCANEO HORARIO AUTOMATICO"
    ahora_str = ahora_ny().strftime("%H:%M")
    print(f"\n{tipo} activado a las {ahora_str} (NY)...")
    alertas_enviadas = 0

    for ticker in ACCIONES_A_VIGILAR:
        try:
            with open(os.devnull, "w") as archivo_nulo, contextlib.redirect_stderr(archivo_nulo):
                hist = yf.Ticker(ticker).history(period="2d", interval="15m")
            if len(hist) < 10:
                continue

            p_actual = hist["Close"].iloc[-1]
            p_anterior = hist["Close"].iloc[-2]
            p_apertura = hist["Open"].iloc[0]
            vol_actual = hist["Volume"].iloc[-1]
            vol_prom = hist["Volume"].tail(10).mean()

            variacion_diaria = ((p_actual - p_apertura) / p_apertura) * 100
            rsi = ta.rsi(hist["Close"], length=14).iloc[-1]

            if variacion_diaria < -6.0:
                if p_actual > p_anterior:
                    noticias = obtener_noticias_ticker(ticker)
                    enviar_mensaje(
                        f"COMPRA CONFIRMADA: {ticker}\n"
                        f"--------------------\n"
                        f"GIRO INTRADIA: El precio freno su caida y empieza a subir.\n"
                        f"Caida del dia: {variacion_diaria:.2f}%\n"
                        f"Precio entrada: ${p_actual:.2f}\n"
                        f"Volumen ultimo: {'ALTO (Absorcion)' if vol_actual > vol_prom else 'Normal'}\n"
                        f"Stop loss sugerido: ${p_actual * 0.97:.2f} (Riesgo maximo 3%)\n\n"
                        f"Contexto de la caida (noticias):\n{noticias}"
                    )
                    alertas_enviadas += 1
                else:
                    print(f"[ESPERA] {ticker} en caida libre ({variacion_diaria:.2f}%), esperando estabilizacion en vela de 15m...")
            elif rsi < 28 and p_actual > p_anterior:
                noticias = obtener_noticias_ticker(ticker)
                enviar_mensaje(
                    f"ORDEN: REBOTE RSI {ticker}\n"
                    f"--------------------\n"
                    f"RSI actual: {rsi:.2f} (Sobreventa critica en 15m).\n"
                    f"Precio: ${p_actual:.2f}\n"
                    f"Accion: iniciando giro. Evalua entrada en Quantfury con stop loss ajustado.\n\n"
                    f"Ultimos titulares:\n{noticias}"
                )
                alertas_enviadas += 1
            elif rsi > 75:
                enviar_mensaje(
                    f"ORDEN: RETIRAR BENEFICIOS EN {ticker}\n"
                    f"--------------------\n"
                    f"RSI extendido: {rsi:.2f} (Agotamiento alcista).\n"
                    f"Precio: ${p_actual:.2f}\n"
                    f"Accion: protege tu capital. Cierra o reduce la posicion."
                )
                alertas_enviadas += 1
        except Exception:
            continue
        time.sleep(0.05)

    return alertas_enviadas


def generar_reporte_proximos_7_dias():
    print("\nAnalizando estructuras macro para proyeccion semanal de 7 dias...")
    oportunidades = []

    for ticker in ACCIONES_A_VIGILAR:
        try:
            with open(os.devnull, "w") as archivo_nulo, contextlib.redirect_stderr(archivo_nulo):
                hist = yf.Ticker(ticker).history(period="3m", interval="1d")
            if len(hist) < 30:
                continue

            rsi = ta.rsi(hist["Close"], length=14).iloc[-1]
            ema_20 = ta.ema(hist["Close"], length=20).iloc[-1]
            ema_20_anterior = ta.ema(hist["Close"], length=20).iloc[-2]
            p_actual = hist["Close"].iloc[-1]

            if rsi < 35 or (p_actual > ema_20 and hist["Close"].iloc[-2] <= ema_20_anterior):
                potencial = "Fuerte rebote en soporte" if rsi < 35 else "Ruptura de tendencia swing"
                oportunidades.append((ticker, p_actual, rsi, potencial))
        except Exception:
            continue
        time.sleep(0.05)

    if oportunidades:
        reporte = "PROYECCION SWING: PROXIMOS 7 DIAS\n"
        reporte += "--------------------\n"
        reporte += "Analisis de estructura diaria post-cierre de mercado:\n\n"
        for op in oportunidades[:7]:
            reporte += f"{op[0]} | Precio cierre: ${op[1]:.2f}\n"
            reporte += f"RSI diario: {op[2]:.2f} | Patron: {op[3]}\n"
            reporte += "Objetivo tecnico: estimado +4.5% a +8% semanal.\n\n"
        enviar_mensaje(reporte)
        return 1

    enviar_mensaje("REPORTE SWING: el mercado cerro sin patrones limpios de consolidacion para la semana.")
    return 1


def escanear_noticias_fuera_de_horario():
    print(f"\nEscaneando noticias de impacto fuera de horario laboral ({ahora_ny().strftime('%H:%M')} NY)...")
    alertas_enviadas = 0

    for ticker in ACCIONES_A_VIGILAR:
        try:
            with open(os.devnull, "w") as archivo_nulo, contextlib.redirect_stderr(archivo_nulo):
                asset = yf.Ticker(ticker)
                news = asset.news

            if not news:
                continue

            ultima_noticia = news[0]
            titulo = ultima_noticia.get("title", "").upper()
            link = ultima_noticia.get("link", "#")

            if any(palabra in titulo for palabra in PALABRAS_CLAVE_NOTICIAS):
                enviar_mensaje(
                    f"RADAR 24/7: NOTICIA CRITICA FUERA DE HORARIO ({ticker})\n"
                    f"--------------------\n"
                    f"Titular: [{ultima_noticia.get('title')}]({link})\n"
                    f"Recomendacion: revisa su pre-market antes de operar manualmente."
                )
                alertas_enviadas += 1
        except Exception:
            continue
        time.sleep(0.05)

    return alertas_enviadas


def enviar_mensaje_inicio():
    enviar_mensaje(
        "CENTRO DE CONTROL ACTIVADO\n"
        "- Monitoreo tecnico en mercado abierto (por hora)\n"
        "- Alerta de pre-cierre institucional (3:45 PM)\n"
        "- Reporte tecnico proyeccion 7 dias (4:05 PM)\n"
        "- Rastreador de noticias de impacto 24/7 (fuera de horario)"
    )


def enviar_resumen_sin_alertas(modo):
    enviar_mensaje(
        f"BOT JOB OK: `{modo}` ejecutado a las {ahora_ny().strftime('%H:%M')} NY sin alertas ni noticias criticas."
    )


def ejecutar_job(modo):
    mensajes_enviados = 0

    if modo == "startup":
        enviar_mensaje_inicio()
        mensajes_enviados = 1
    elif modo == "market_scan":
        mensajes_enviados = analizar_mercado_quirurgico(es_cierre=False)
    elif modo == "preclose":
        mensajes_enviados = analizar_mercado_quirurgico(es_cierre=True)
    elif modo == "swing_report":
        mensajes_enviados = generar_reporte_proximos_7_dias()
    elif modo == "news_scan":
        mensajes_enviados = escanear_noticias_fuera_de_horario()
    else:
        raise ValueError(
            "Modo no valido. Usa uno de: startup, market_scan, preclose, swing_report, news_scan."
        )

    if mensajes_enviados == 0 and entorno_activo("BOT_NOTIFY_EMPTY_RUNS"):
        enviar_resumen_sin_alertas(modo)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(
            "Uso: python script_bolsa.py <startup|market_scan|preclose|swing_report|news_scan>"
        )

    ejecutar_job(sys.argv[1].strip().lower())


if __name__ == "__main__":
    main()
