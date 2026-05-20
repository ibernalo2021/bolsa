# Bot de Alertas Bursatiles

Este proyecto analiza una lista de activos con `yfinance` y `pandas-ta`, y envia alertas a Telegram cuando detecta condiciones tecnicas o noticias relevantes.

## Modos disponibles

El script principal es [`script_bolsa.py`](./script_bolsa.py) y ahora se ejecuta por modos:

- `startup`: envia el mensaje de arranque
- `market_scan`: escaneo horario durante mercado abierto
- `preclose`: escaneo especial de pre-cierre
- `swing_report`: reporte tecnico de 7 dias
- `news_scan`: escaneo de noticias fuera de horario

## Variables de entorno

Puedes usar un archivo `.env` local o secretos de GitHub Actions.

Variables requeridas:

```env
TELEGRAM_BOT_1_TOKEN=tu_token
TELEGRAM_BOT_1_CHAT_ID=tu_chat_id
TELEGRAM_BOT_1_NAME=Ivan
```

Variables opcionales para un segundo bot:

```env
TELEGRAM_BOT_2_TOKEN=
TELEGRAM_BOT_2_CHAT_ID=
TELEGRAM_BOT_2_NAME=Bot Secundario
```

## Ejecucion local

Instala dependencias:

```powershell
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Ejemplos de ejecucion:

```powershell
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" script_bolsa.py startup
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" script_bolsa.py market_scan
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" script_bolsa.py preclose
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" script_bolsa.py swing_report
& "C:\Users\ICBS\AppData\Local\Programs\Python\Python312\python.exe" script_bolsa.py news_scan
```

## Despliegue en GitHub Actions

El workflow ya esta incluido en:

[`/.github/workflows/bot-jobs.yml`](./.github/workflows/bot-jobs.yml)

### 1. Subir el proyecto a GitHub

Sube este repositorio a GitHub. El archivo `.env` esta ignorado por [`.gitignore`](./.gitignore), asi que tus credenciales locales no deben subirse.

### 2. Crear los secretos

En GitHub:

`Settings > Secrets and variables > Actions`

Crea estos secretos:

- `TELEGRAM_BOT_1_TOKEN`
- `TELEGRAM_BOT_1_CHAT_ID`
- `TELEGRAM_BOT_1_NAME`
- `TELEGRAM_BOT_2_TOKEN` opcional
- `TELEGRAM_BOT_2_CHAT_ID` opcional
- `TELEGRAM_BOT_2_NAME` opcional

### 3. Probar manualmente

En GitHub:

`Actions > Bot Jobs > Run workflow`

Prueba primero alguno de estos modos:

- `startup`
- `market_scan`

Si el bot envia mensajes correctamente, ya puedes confiar en la programacion automatica.

## Horarios configurados en GitHub Actions

El workflow ejecuta:

- `market_scan`: cada hora entre `9:00 AM` y `3:00 PM` de `America/New_York`
- `preclose`: `3:45 PM` de `America/New_York`
- `swing_report`: `4:05 PM` de `America/New_York`
- `news_scan`: `12:00 AM`, `8:00 AM` y `8:00 PM` de `America/New_York`

## Notas importantes

- GitHub Actions no deja el proceso vivo; ejecuta cada job y termina. Este proyecto fue adaptado especificamente para ese modelo.
- Si Telegram devuelve `chat not found`, el problema suele ser el `CHAT_ID`.
- Si la API de Telegram devuelve `404`, el problema suele ser el `TOKEN`.
- Si usas un repo privado, vigila el consumo de minutos de GitHub Actions.
