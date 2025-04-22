from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_PATH = "configuraciones.db"

# Crear la tabla si no existe
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuraciones (
        shop_domain TEXT PRIMARY KEY,
        instance_id TEXT,
        token TEXT
    )
''')
conn.commit()
conn.close()


# Ruta GET para mostrar el formulario
@app.get("/configurar", response_class=HTMLResponse)
async def mostrar_formulario(request: Request, shop: str = Query(None)):
    if not shop:
        return HTMLResponse(content="❌ Error: Debes acceder con ?shop=mitienda.myshopify.com", status_code=400)
    return templates.TemplateResponse("configurar.html", {"request": request, "shop": shop})


# Ruta POST para guardar la configuración de cada tienda
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
        INSERT OR REPLACE INTO configuraciones (shop_domain, instance_id, token)
        VALUES (?, ?, ?)
    """, (shop, instance_id, token))
    conn.commit()
    conn.close()

    return templates.TemplateResponse("configurar.html", {
        "request": request,
        "shop": shop,
        "mensaje": "✅ Configuración guardada correctamente"
    })


# Webhook para recibir pedidos y enviar WhatsApp usando config de esa tienda
@app.post("/webhook")
async def recibir_pedido(pedido: dict):
    shop_domain = pedido.get("source_name")
    if not shop_domain:
        return {"error": "No se detectó el dominio de la tienda"}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT instance_id, token FROM configuraciones WHERE shop_domain = ?", (shop_domain,))
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        print(f"❌ No hay configuración para la tienda {shop_domain}")
        return {"error": f"No hay configuración guardada para {shop_domain}"}

    instance_id, token = resultado

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
            print("✅ WhatsApp enviado a:", telefono)
            return {"status": "success", "whatsapp_response": response.json()}
        except Exception as e:
            print("❌ Error enviando WhatsApp:", str(e))
            return {"error": str(e)}
        
@app.get("/panel", response_class=HTMLResponse)
async def ver_panel(request: Request, shop: str = Query(None)):
    if not shop:
        return HTMLResponse("❌ Falta el parámetro ?shop=...", status_code=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT instance_id, token FROM configuraciones WHERE shop_domain = ?", (shop,))
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return HTMLResponse(f"❌ No hay configuración guardada para {shop}", status_code=404)

    instance_id, token = resultado
    return templates.TemplateResponse("panel.html", {
        "request": request,
        "shop": shop,
        "instance_id": instance_id,
        "token": token
    })

