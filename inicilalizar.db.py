import sqlite3

# Ruta de la base de datos
DB_PATH = "configuraciones.db"

# Conexión y creación de tablas
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Tabla de configuración de tiendas (activas o inactivas)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuraciones (
        shop_domain TEXT PRIMARY KEY,
        instance_id TEXT,
        token TEXT,
        activa INTEGER DEFAULT 1
    )
''')

# Historial de mensajes enviados
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

print("✅ Base de datos configurada correctamente.")
