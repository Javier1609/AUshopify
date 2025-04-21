# 📦 Notificador Automático de Pedidos por WhatsApp para Shopify

Este proyecto permite **automatizar el envío de mensajes de WhatsApp** a los clientes de una tienda Shopify **cada vez que hacen un pedido**, utilizando:

- ✅ Shopify (webhooks)
- ✅ FastAPI (backend)
- ✅ UltraMsg (API de WhatsApp)
- ✅ SQLite (registro de pedidos enviados)
- ✅ Render.com (para alojarlo en la nube, sin depender de tu PC)

---

## 🚀 ¿Qué hace esta aplicación?

Cada vez que un cliente hace un pedido en tu tienda:

1. Shopify envía un **webhook** a esta aplicación.
2. El servidor recibe los datos del pedido: nombre, teléfono, productos, dirección...
3. Se genera un **mensaje de WhatsApp personalizado**.
4. Se envía automáticamente usando **tu instancia activa de UltraMsg**.
5. El pedido se guarda en una base de datos para **evitar envíos duplicados**.

---

## ⚙️ Requisitos

- Python 3.9+
- Una cuenta gratuita en [UltraMsg](https://app.ultramsg.com)
- Una tienda Shopify
- Una cuenta de GitHub (si lo vas a desplegar en Render)
- Render.com para alojarlo 24/7 (gratis)

---

## 🛠️ Cómo usarlo localmente

1. Clona este repositorio
2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   venv\Scripts\activate
