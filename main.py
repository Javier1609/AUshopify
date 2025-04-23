from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_PATH = "configuraciones.db"

# CREAR BASE DE DATOS: configuración y mensajes
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuraciones (
        shop_domain TEXT PRIMARY KEY,
        instance_id TEXT,
        token TEXT,
        activa INTEGER DEFAULT 1
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_domain TEXT,
        telefono TEXT,
        mensaje TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/configurar", response_class=HTMLResponse)
async def mostrar_formulario(request: Request, shop: str = Query(None)):
    if not shop:
        return HTMLResponse("❌ Debes acceder con ?shop=mitienda.myshopify.com", status_code=400)
    return templates.TemplateResponse("configurar.html", {"request": request, "shop": shop})


@app.post("/configurar", response_class=HTMLResponse)
async def guardar_configuracion(
    request: Request,
    shop: str = Form(...),
    instance_id: str = Form(...),
    token: str = Form(...)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO configuraciones (shop_domain, instance_id, token, activa)
        VALUES (?, ?, ?, 1)
    """, (shop, instance_id, token))
    conn.commit()
    conn.close()
    return templates.TemplateResponse("configurar.html", {
        "request": request,
        "shop": shop,
        "mensaje": "✅ Configuración guardada correctamente"
    })


@app.get("/panel", response_class=HTMLResponse)
async def ver_panel(request: Request, shop: str = Query(None)):
    if not shop:
        return HTMLResponse("❌ Falta el parámetro ?shop=...", status_code=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT instance_id, token, activa FROM configuraciones WHERE shop_domain = ?", (shop,))
    resultado = cursor.fetchone()

    cursor.execute("SELECT telefono, mensaje, fecha FROM mensajes WHERE shop_domain = ? ORDER BY fecha DESC", (shop,))
    mensajes = cursor.fetchall()
    conn.close()

    if not resultado:
        return HTMLResponse(f"❌ No hay configuración guardada para {shop}", status_code=404)

    instance_id, token, activa = resultado
    return templates.TemplateResponse("panel.html", {
        "request": request,
        "shop": shop,
        "instance_id": instance_id,
        "token": token,
        "activa": activa,
        "mensajes": mensajes
    })


@app.get("/activar")
async def activar_shop(shop: str = Query(...), estado: int = Query(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE configuraciones SET activa = ? WHERE shop_domain = ?", (estado, shop))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/panel?shop={shop}", status_code=303)


@app.post("/webhook")
async def recibir_pedido(pedido: dict):
    shop_domain = pedido.get("source_name")
    if not shop_domain:
        return {"error": "No se detectó el dominio de la tienda"}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT instance_id, token, activa FROM configuraciones WHERE shop_domain = ?", (shop_domain,))
    resultado = cursor.fetchone()

    if not resultado:
        return {"error": f"No hay configuración guardada para {shop_domain}"}

    instance_id, token, activa = resultado

    if activa == 0:
        return {"error": "Tienda inactiva. WhatsApp no enviado."}

    telefono = pedido.get("shipping_address", {}).get("phone")
    nombre = pedido.get("shipping_address", {}).get("name")
    direccion = pedido.get("shipping_address", {}).get("address1")
    productos = "\n".join([f"• {item['title']} x{item['quantity']}" for item in pedido.get("line_items", [])])

    if not telefono:
        return {"error": "El pedido no tiene teléfono"}

    mensaje = f"""🛍️ ¡Hola {nombre}!

Gracias por tu pedido #{pedido.get("id")} en nuestra tienda ❤️

📦 Productos:
{productos}

📍 Dirección de entrega:
{direccion}

Te avisaremos cuando tu pedido esté en camino. ¡Gracias por confiar en nosotros! 📬"""

    url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    payload = {
        "token": token,
        "to": telefono,
        "body": mensaje
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=payload)

            # GUARDAR MENSAJE EN HISTORIAL
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mensajes (shop_domain, telefono, mensaje)
                VALUES (?, ?, ?)
            """, (shop_domain, telefono, mensaje))
            conn.commit()
            conn.close()

            print("✅ WhatsApp enviado a:", telefono)
            return {"status": "success", "whatsapp_response": response.json()}
        except Exception as e:
            print("❌ Error enviando WhatsApp:", str(e))
            return {"error": str(e)}
