from fastapi import FastAPI, Request
import httpx
import sqlite3
import os
import re

app = FastAPI()

ULTRAMSG_API_URL = "https://api.ultramsg.com/instance115371/messages/chat"
TOKEN = "ghaw82a43rs531dl"
TO_PHONE_PREFIX = "34"

# 🗃️ Inicializar la base de datos
DB_PATH = "notificados.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 📩 Función para revisar si un pedido ya fue enviado
def pedido_ya_enviado(order_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pedidos WHERE id = ?", (order_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

# ✅ Guardar pedido como enviado
def guardar_pedido(order_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pedidos (id) VALUES (?)", (order_id,))
    conn.commit()
    conn.close()

@app.post("/webhook")
async def receive_order(request: Request):
    data = await request.json()
    print("📦 Pedido recibido:\n", data)

    try:
        customer = data.get("customer", {})
        shipping_address = data.get("shipping_address", {})
        phone = customer.get("phone")
        name = customer.get("first_name", "cliente")
        order_id = data.get("id", None)
        line_items = data.get("line_items", [])

        if not order_id:
            return {"status": "error", "message": "ID de pedido no encontrado"}

        if pedido_ya_enviado(order_id):
            print(f"⚠️ Pedido {order_id} ya fue notificado. Ignorando.")
            return {"status": "duplicate", "order_id": order_id}

        if not phone:
            print("⚠️ Pedido sin número de teléfono.")
            return {"status": "ignored", "reason": "no phone"}

        # Limpieza de número
        raw_phone = re.sub(r"\D", "", phone)
        final_phone = raw_phone if raw_phone.startswith(TO_PHONE_PREFIX) else TO_PHONE_PREFIX + raw_phone[-9:]

        # Dirección y productos
        address = f"{shipping_address.get('address1', '')}, {shipping_address.get('city', '')}, {shipping_address.get('zip', '')}, {shipping_address.get('country', '')}"
        products = "\n".join([f"• {item['title']} x{item['quantity']}" for item in line_items])

        # Mensaje de WhatsApp
        message = (
            f"🛒 ¡Hola {name}!\n"
            f"Gracias por tu pedido #{order_id} en nuestra tienda ❤️\n\n"
            f"📦 Productos:\n{products or 'sin productos'}\n\n"
            f"🏠 Dirección de entrega:\n{address or 'sin dirección'}\n\n"
            "Te avisaremos cuando tu pedido esté en camino. ¡Gracias por confiar en nosotros! 🚚"
        )

        payload = {
            "token": TOKEN,
            "to": final_phone,
            "body": message
        }

        print(f"📤 Enviando WhatsApp a {final_phone}")
        print(f"📨 Mensaje:\n{message}")

        async with httpx.AsyncClient() as client:
            response = await client.post(ULTRAMSG_API_URL, data=payload)
            print("✅ Respuesta UltraMsg:", response.status_code, response.text)

        guardar_pedido(order_id)
        return {"status": "ok", "order_id": order_id}

    except Exception as e:
        print("❌ Error:", e)
        return {"status": "error", "message": str(e)}
