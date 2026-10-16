import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "boletos_conve.db")
XML_FACE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
DIR_CAPTURAS = os.path.join(BASE_DIR, "capturas_seguridad")

# Fase 3: Conexión del software con dispositivos externos (0 = laptop, 1+ = arcos USB)
CAMERA_INDEX = 0

MOVIMIENTO_UMBRAL_PX = 8.0
FACE_SCALE_FACTOR = 1.1
FACE_MIN_NEIGHBORS = 5

COOLDOWN_QR_SEGUNDOS = 4

# Fase 3: Configuración de variables para ajustar las métricas del aforo en tiempo real
AFORO_MAXIMO = 3