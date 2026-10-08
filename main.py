import cv2
import customtkinter as ctk
from PIL import Image, ImageTk
import pyzbar.pyzbar as pyzbar
import datetime
import sqlite3
import qrcode
import os
import urllib.request
import time

# ==========================================
# SECCIÓN 0: CONFIGURACIÓN DE DIRECTORIOS Y MODELOS
# ==========================================
# Crear carpeta local para auditoría de seguridad y capturas de acceso
if not os.path.exists("capturas_seguridad"):
    os.makedirs("capturas_seguridad")

# Descargar y asegurar el clasificador XML para la detección de rostros (Visión Computacional)
xml_face_path = 'haarcascade_frontalface_default.xml'
if not os.path.exists(xml_face_path):
    url_xml = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
    try:
        urllib.request.urlretrieve(url_xml, xml_face_path)
    except Exception:
        pass


class KioscoAccesoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración general de la ventana principal (Estilo Kiosco Táctil)
        self.title("Sistema de Control de Acceso - La Conve")
        self.geometry("1024x768")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variables de control de estado y tiempos de espera (Cooldown)
        self.ultimo_qr = None
        self.tiempo_ultimo_escaneo = 0
        self.cooldown_segundos = 4

        # Inicialización de la Base de Datos Local SQLite
        self.init_db()

        # Configuración del hardware de video (Cámara web con DirectShow para Windows)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        # Carga del modelo de detección de rostros en movimiento
        self.face_cascade = cv2.CascadeClassifier(xml_face_path)

        # Configuración del sistema de pestañas (Pantalla única con módulo Admin oculto)
        self.tabview = ctk.CTkTabview(self, width=1000, height=740)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_escaner = self.tabview.add("Escaner (Touch Screen)")
        self.tab_admin = self.tabview.add("Admin / Generar QR")

        # Construcción de la interfaz gráfica
        self.setup_escaner_tab()
        self.setup_admin_tab()

        # Iniciar ciclo de procesamiento en tiempo real del video
        self.actualizar_video()

    # ==========================================
    # SECCIÓN 1: GESTIÓN DE BASE DE DATOS (SQLite)
    # ==========================================
    def init_db(self):
        self.conn = sqlite3.connect('boletos_conve.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS boletos
                         (id TEXT PRIMARY KEY, titular TEXT, fecha TEXT, tipo TEXT, personas INTEGER, estado TEXT)''')
        self.conn.commit()

    # ==========================================
    # SECCIÓN 2: INTERFAZ GRÁFICA - PESTAÑA ESCÁNER
    # ==========================================
    def setup_escaner_tab(self):
        # Panel superior de contadores en tiempo real
        self.frame_contadores = ctk.CTkFrame(self.tab_escaner)
        self.frame_contadores.pack(pady=10, fill="x")

        self.lbl_entradas = ctk.CTkLabel(self.frame_contadores, text="Entradas: 0", font=("Arial", 24, "bold"))
        self.lbl_entradas.pack(side="left", expand=True)

        self.lbl_rechazos = ctk.CTkLabel(self.frame_contadores, text="Rechazos: 0", font=("Arial", 24, "bold"))
        self.lbl_rechazos.pack(side="left", expand=True)

        # Contenedor del feed de video de la cámara
        self.lbl_video = ctk.CTkLabel(self.tab_escaner, text="")
        self.lbl_video.pack(pady=10)

        # Pantalla central de mensajes y alertas estilo Kiosco
        self.lbl_mensaje = ctk.CTkLabel(self.tab_escaner, text="Muestre su codigo QR a la camara", 
                                        font=("Arial", 28, "bold"), fg_color="#333333", 
                                        corner_radius=10, height=100)
        self.lbl_mensaje.pack(pady=20, fill="x", padx=50)

        self.actualizar_contadores()

    # ==========================================
    # SECCIÓN 3: INTERFAZ GRÁFICA - PESTAÑA ADMIN
    # ==========================================
    def setup_admin_tab(self):
        titulo = ctk.CTkLabel(self.tab_admin, text="Registro de Nuevos Boletos y QRs", font=("Arial", 24, "bold"))
        titulo.pack(pady=20)

        self.ent_id = ctk.CTkEntry(self.tab_admin, placeholder_text="ID del Boleto (ej. TKT-001)", width=300)
        self.ent_id.pack(pady=10)

        self.ent_titular = ctk.CTkEntry(self.tab_admin, placeholder_text="Nombre del Titular", width=300)
        self.ent_titular.pack(pady=10)

        self.ent_fecha = ctk.CTkEntry(self.tab_admin, placeholder_text="Fecha (YYYY-MM-DD)", width=300)
        self.ent_fecha.pack(pady=10)
        self.ent_fecha.insert(0, datetime.date.today().strftime("%Y-%m-%d")) 

        self.combo_tipo = ctk.CTkComboBox(self.tab_admin, values=["General", "VIP"], width=300)
        self.combo_tipo.pack(pady=10)

        self.ent_personas = ctk.CTkEntry(self.tab_admin, placeholder_text="Cantidad de personas", width=300)
        self.ent_personas.pack(pady=10)

        btn_generar = ctk.CTkButton(self.tab_admin, text="Generar QR y Guardar en DB", command=self.generar_qr)
        btn_generar.pack(pady=20)

        self.lbl_admin_msg = ctk.CTkLabel(self.tab_admin, text="")
        self.lbl_admin_msg.pack()

    # ==========================================
    # SECCIÓN 4: LOGICA DE REGISTRO Y GENERACIÓN QR
    # ==========================================
    def generar_qr(self):
        b_id = self.ent_id.get()
        titular = self.ent_titular.get()
        fecha = self.ent_fecha.get()
        tipo = self.combo_tipo.get()
        personas = self.ent_personas.get()

        if not all([b_id, titular, fecha, personas]):
            self.lbl_admin_msg.configure(text="Llene todos los campos requeridos", text_color="red")
            return

        try:
            # Insertar registro en la base de datos simulada
            self.c.execute("INSERT INTO boletos VALUES (?, ?, ?, ?, ?, 'SIN USAR')", 
                           (b_id, titular, fecha, tipo, int(personas)))
            self.conn.commit()
            
            # Generar archivo de imagen QR físico para pruebas
            img_qr = qrcode.make(b_id)
            img_qr.save(f"{b_id}.png")
            
            self.lbl_admin_msg.configure(text=f"Boleto {b_id} registrado con exito.", text_color="green")
            self.actualizar_contadores()
        except sqlite3.IntegrityError:
            self.lbl_admin_msg.configure(text="Error: El ID del boleto ya se encuentra registrado.", text_color="red")

    def actualizar_contadores(self):
        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='INGRESADO'")
        entradas = self.c.fetchone()[0]
        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='RECHAZADO'")
        rechazos = self.c.fetchone()[0]
        
        self.lbl_entradas.configure(text=f"Entradas: {entradas}")
        self.lbl_rechazos.configure(text=f"Rechazos: {rechazos}")

    def mostrar_mensaje_pantalla(self, texto, color):
        self.lbl_mensaje.configure(text=texto, fg_color=color)

    # ==========================================
    # SECCIÓN 5: PROCESAMIENTO DE VIDEO Y VISIÓN COMPUTACIONAL
    # ==========================================
    def actualizar_video(self):
        ret, frame = self.cap.read()
        if ret:
            # Voltear la imagen horizontalmente para un efecto espejo natural
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Algoritmo de detección de rostros en movimiento (Fase 2)
            if not self.face_cascade.empty():
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Control de tiempo de espera (Cooldown) entre lecturas de códigos QR consecutivos
            if time.time() - self.tiempo_ultimo_escaneo > self.cooldown_segundos:
                self.mostrar_mensaje_pantalla("Muestre su codigo QR a la camara", "#333333")
                
                # Decodificación y lectura de códigos QR mediante pyzbar
                codigos_qr = pyzbar.decode(frame)
                for qr in codigos_qr:
                    qr_data = qr.data.decode('utf-8')
                    self.procesar_acceso(qr_data, frame)
                    self.tiempo_ultimo_escaneo = time.time()
                    break 

            # Renderizado del flujo de video en la interfaz de CustomTkinter
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img_tk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(640, 480))
            self.lbl_video.configure(image=img_tk)
            self.lbl_video.image = img_tk

        self.after(10, self.actualizar_video)

    # ==========================================
    # SECCIÓN 6: REGLAS DE NEGOCIO Y VALIDACIÓN DE ACCESOS
    # ==========================================
    def procesar_acceso(self, qr_id, frame_actual):
        self.c.execute("SELECT * FROM boletos WHERE id=?", (qr_id,))
        boleto = self.c.fetchone()
        
        # Auditoría: Capturar y guardar fotografía del intento de acceso en la carpeta local
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"capturas_seguridad/{qr_id}_{timestamp}.jpg", frame_actual)

        # Validación: Existencia del boleto en la base de datos
        if not boleto:
            self.mostrar_mensaje_pantalla("Acceso denegado: QR no encontrado en el sistema.", "#8B0000")
            return

        b_id, titular, fecha, tipo, personas, estado = boleto
        fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

        # Punto 1: Validación estricta de fechas del evento
        if fecha != fecha_hoy:
            self.mostrar_mensaje_pantalla(f"Acceso denegado: El boleto pertenece a la fecha {fecha}.\nHoy es {fecha_hoy}.", "#8B0000")
            self.c.execute("UPDATE boletos SET estado='RECHAZADO' WHERE id=?", (b_id,))
            self.conn.commit()
            self.actualizar_contadores()
            return

        # Validación: Control de boleto previamente utilizado (Evitar reutilización)
        if estado == 'INGRESADO':
            self.mostrar_mensaje_pantalla("Acceso denegado: Este boleto ya fue registrado previamente.", "#8B0000")
            return

        # Punto 2: Manejo de excepciones y redirección para accesos VIP
        if tipo == "VIP":
            self.mostrar_mensaje_pantalla("Boleto VIP detectado.\nRedirigir a zona preferencial para entrega de beneficios.", "#B8860B")
            return

        # Punto 0: Validación de acceso general y simulación de entrega de brazaletes físicos
        self.c.execute("UPDATE boletos SET estado='INGRESADO' WHERE id=?", (b_id,))
        self.conn.commit()
        self.actualizar_contadores()
        
        mensaje_exito = f"Bienvenido {titular}.\nDispensando {personas} brazalete(s) fisico(s)..."
        self.mostrar_mensaje_pantalla(mensaje_exito, "#006400")

if __name__ == "__main__":
    app = KioscoAccesoApp()
    app.mainloop()