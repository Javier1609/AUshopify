from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_PATH = "configuraciones.db"

# Crear tablas si no existen
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuraciones (
        shop_domain TEXT PRIMARY KEY,
        activa INTEGER DEFAULT 1
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_domain TEXT,
        pedido_id TEXT,
        telefono TEXT,
        mensaje TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()

@app.get("/configurar", response_class=HTMLResponse)
async def mostrar_formulario(request: Request, shop: str = Query(None)):
    if not shop:
        return HTMLResponse("❌ Falta el parámetro ?shop=mitienda.myshopify.com", status_code=400)
    return templates.TemplateResponse("configurar.html", {"request": request, "shop": shop})

@app.post("/configurar", response_class=HTMLResponse)
async def guardar_configuracion(
    request: Request,
    shop: str = Form(...)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO configuraciones (shop_domain, activa)
        VALUES (?, 1)
    """, (shop,))
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
    cursor.execute("SELECT activa FROM configuraciones WHERE shop_domain = ?", (shop,))
    resultado = cursor.fetchone()

    cursor.execute("""
        SELECT pedido_id, telefono, mensaje, estado, fecha
        FROM mensajes
        WHERE shop_domain = ?
        ORDER BY fecha DESC
    """, (shop,))
    mensajes = cursor.fetchall()
    conn.close()

    if not resultado:
        return HTMLResponse(f"❌ No hay configuración guardada para {shop}", status_code=404)

    activa = resultado[0]
    return templates.TemplateResponse("panel.html", {
        "request": request,
        "shop": shop,
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
    cursor.execute("SELECT activa FROM configuraciones WHERE shop_domain = ?", (shop_domain,))
    resultado = cursor.fetchone()

    if not resultado or resultado[0] == 0:
        return {"error": "Tienda inactiva o no registrada"}

    telefono_raw = pedido.get("shipping_address", {}).get("phone", "")
    telefono = ''.join(filter(str.isdigit, telefono_raw))  # Solo números
    nombre = pedido.get("shipping_address", {}).get("name")
    direccion = pedido.get("shipping_address", {}).get("address1")
    productos = "\n".join([f"• {item['title']} x{item['quantity']}" for item in pedido.get("line_items", [])])
    pedido_id = str(pedido.get("id"))

    if not telefono:
        return {"error": "El pedido no tiene teléfono"}

    mensaje = f"""🛍️ ¡Hola {nombre}!

Gracias por tu pedido #{pedido_id} en nuestra tienda ❤️

📦 Productos:
{productos}

📍 Dirección de entrega:
{direccion}

Te avisaremos cuando tu pedido esté en camino. ¡Gracias por confiar en nosotros! 📬"""

    # Enviar con Baileys en Replit
    url = "https://94eba1fc-8243-4ba5-aec6-4ac0c286ce4f-00-hmxo37a6xidr.spock.replit.dev/send"
    payload = {
        "to": telefono,
        "message": mensaje
    }

    estado_envio = "pendiente"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            estado_envio = "enviado" if response.status_code == 200 else "fallido"
        except Exception as e:
            print("❌ Error enviando WhatsApp:", e)
            estado_envio = "fallido"

    # Guardar en historial
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mensajes (shop_domain, pedido_id, telefono, mensaje, estado)
        VALUES (?, ?, ?, ?, ?)
    """, (shop_domain, pedido_id, telefono, mensaje, estado_envio))
    conn.commit()
    conn.close()

    return {"status": estado_envio}
