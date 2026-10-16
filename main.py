import cv2
import customtkinter as ctk
from PIL import Image, ImageTk
import datetime
import sqlite3
import qrcode
import os
import time
from vision_engine import VisionEngine
import config  # Importación de variables para la Fase 3

# Crear carpetas necesarias al iniciar
if not os.path.exists(config.DIR_CAPTURAS):
    os.makedirs(config.DIR_CAPTURAS)

# Carpeta para organizar los QR de prueba generados
if not os.path.exists("qrs_generados"):
    os.makedirs("qrs_generados")

class KioscoAccesoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LA CONVE - Control de Acceso")
        self.geometry("1024x768")
        # Diseño basado en los carteles: Fondo casi negro
        self.configure(fg_color="#0A0A0A") 
        ctk.set_appearance_mode("dark")

        self.ultimo_qr = None
        self.tiempo_ultimo_escaneo = 0
        self.cooldown_segundos = config.COOLDOWN_QR_SEGUNDOS
        
        # Ventana de administración oculta por defecto
        self.admin_window = None

        self.init_db()

        # Motor de vision computacional (Fase 2)
        self.vision = VisionEngine()

        # Camara (Fase 3: Conexión con dispositivos externos)
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(config.CAMERA_INDEX)

        self.setup_escaner_ui()
        
        # Atajo de teclado secreto para abrir el admin (Ctrl + A)
        self.bind('<Control-a>', self.abrir_admin)

        self.actualizar_video()

    def init_db(self):
        self.conn = sqlite3.connect(config.DB_PATH)
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS boletos
                         (id TEXT PRIMARY KEY, titular TEXT, fecha TEXT, tipo TEXT, personas INTEGER, estado TEXT)''')
        self.conn.commit()

    def setup_escaner_ui(self):
        # HEADER LOGO (Inspirado en la tipografía blanca y bloques rojos)
        self.lbl_header = ctk.CTkLabel(self, text="LA CONVE", font=("Arial Black", 55, "bold"), text_color="#FFFFFF")
        self.lbl_header.pack(pady=(30, 0))
        
        self.lbl_sub = ctk.CTkLabel(self, text="  MONTERREY  ", font=("Arial Black", 28), 
                                    text_color="#0A0A0A", fg_color="#FFFFFF", corner_radius=5)
        self.lbl_sub.pack(pady=(0, 5))

        self.lbl_fecha = ctk.CTkLabel(self, text=" CONTROL DE ACCESO ", font=("Arial Black", 20), 
                                    text_color="#FFFFFF", fg_color="#E32626", corner_radius=5)
        self.lbl_fecha.pack(pady=(0, 20), ipadx=10, ipady=3)

        # Contenedor del Video
        self.lbl_video = ctk.CTkLabel(self, text="")
        self.lbl_video.pack(pady=10)

        # Mensaje de estado (Inspirado en la caja amarilla de los expositores)
        self.lbl_mensaje = ctk.CTkLabel(self, text="MUESTRE SU CÓDIGO QR", 
                                        font=("Arial Black", 26), text_color="#0A0A0A", fg_color="#FFD100", 
                                        corner_radius=10, height=80)
        self.lbl_mensaje.pack(pady=20, fill="x", padx=100)

    def abrir_admin(self, event=None):
        # Evitar abrir múltiples ventanas si ya está abierta
        if self.admin_window is None or not self.admin_window.winfo_exists():
            self.admin_window = ctk.CTkToplevel(self)
            self.admin_window.title("Panel de Administración - La Conve")
            self.admin_window.geometry("450x650")
            # Diseño basado en el cartel rojo oscuro tipo grunge
            self.admin_window.configure(fg_color="#660505")
            self.admin_window.transient(self) # Mantener por encima de la ventana principal

            titulo = ctk.CTkLabel(self.admin_window, text="PANEL INTERNO", font=("Arial Black", 24), text_color="#FFFFFF")
            titulo.pack(pady=(20, 10))

            # Métrica de Aforo y contadores (Ocultos del público)
            frame_metricas = ctk.CTkFrame(self.admin_window, fg_color="#1A1A1A", corner_radius=10)
            frame_metricas.pack(pady=10, padx=20, fill="x", ipadx=10, ipady=10)
            
            self.lbl_aforo = ctk.CTkLabel(frame_metricas, text="Aforo Actual: Calculando...", font=("Arial Black", 20), text_color="#00FF00")
            self.lbl_aforo.pack(pady=5)

            self.lbl_entradas = ctk.CTkLabel(frame_metricas, text="Entradas validadas: 0", font=("Arial", 16, "bold"), text_color="#FFFFFF")
            self.lbl_entradas.pack(pady=2)

            self.lbl_rechazos = ctk.CTkLabel(frame_metricas, text="Rechazos: 0", font=("Arial", 16, "bold"), text_color="#E32626")
            self.lbl_rechazos.pack(pady=2)

            # Formulario de simulación
            frame_form = ctk.CTkFrame(self.admin_window, fg_color="#1A1A1A", corner_radius=10)
            frame_form.pack(pady=10, padx=20, fill="x", ipadx=10, ipady=10)

            ctk.CTkLabel(frame_form, text="GENERAR BOLETOS DE PRUEBA", font=("Arial Black", 14), text_color="#FFD100").pack(pady=5)

            self.ent_id = ctk.CTkEntry(frame_form, placeholder_text="ID del Boleto", width=300)
            self.ent_id.pack(pady=5)

            self.ent_titular = ctk.CTkEntry(frame_form, placeholder_text="Nombre del Titular", width=300)
            self.ent_titular.pack(pady=5)

            self.ent_fecha = ctk.CTkEntry(frame_form, placeholder_text="Fecha (YYYY-MM-DD)", width=300)
            self.ent_fecha.pack(pady=5)
            self.ent_fecha.insert(0, datetime.date.today().strftime("%Y-%m-%d")) 

            self.combo_tipo = ctk.CTkComboBox(frame_form, values=["General", "VIP"], width=300)
            self.combo_tipo.pack(pady=5)

            self.ent_personas = ctk.CTkEntry(frame_form, placeholder_text="Cantidad de personas", width=300)
            self.ent_personas.pack(pady=5)

            btn_generar = ctk.CTkButton(frame_form, text="Guardar y Crear QR", font=("Arial Black", 14), 
                                        fg_color="#E32626", hover_color="#8B0000", command=self.generar_qr)
            btn_generar.pack(pady=15)

            self.lbl_admin_msg = ctk.CTkLabel(frame_form, text="")
            self.lbl_admin_msg.pack()

            self.actualizar_contadores()
        else:
            self.admin_window.focus()

    def generar_qr(self):
        b_id = self.ent_id.get().strip()
        titular = self.ent_titular.get().strip()
        fecha = self.ent_fecha.get().strip()
        tipo = self.combo_tipo.get()
        personas = self.ent_personas.get().strip()

        if not all([b_id, titular, fecha, personas]):
            self.lbl_admin_msg.configure(text="Llene todos los campos requeridos", text_color="#FFD100")
            return

        try:
            self.c.execute("INSERT INTO boletos VALUES (?, ?, ?, ?, ?, 'SIN USAR')", 
                           (b_id, titular, fecha, tipo, int(personas)))
            self.conn.commit()
            
            img_qr = qrcode.make(b_id)
            # Guardar el QR en la nueva carpeta "qrs_generados"
            ruta_qr = os.path.join("qrs_generados", f"{b_id}.png")
            img_qr.save(ruta_qr)
            
            self.lbl_admin_msg.configure(text=f"Boleto {b_id} registrado con éxito.", text_color="#00FF00")
            self.actualizar_contadores()
        except sqlite3.IntegrityError:
            self.lbl_admin_msg.configure(text="Error: El ID ya se encuentra registrado.", text_color="#E32626")

    def actualizar_contadores(self):
        # Actualizar base de datos
        self.c.execute("SELECT SUM(personas) FROM boletos WHERE estado='INGRESADO'")
        resultado = self.c.fetchone()[0]
        aforo_actual = resultado if resultado else 0

        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='INGRESADO'")
        entradas = self.c.fetchone()[0]
        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='RECHAZADO'")
        rechazos = self.c.fetchone()[0]
        
        # Solo actualizar los textos si la ventana de admin está abierta
        if self.admin_window and self.admin_window.winfo_exists():
            self.lbl_entradas.configure(text=f"Entradas validadas: {entradas}")
            self.lbl_rechazos.configure(text=f"Rechazos: {rechazos}")

            self.lbl_aforo.configure(text=f"Aforo Actual: {aforo_actual} / {config.AFORO_MAXIMO}")
            if aforo_actual >= config.AFORO_MAXIMO:
                self.lbl_aforo.configure(text_color="#E32626") # Rojo
            elif aforo_actual >= config.AFORO_MAXIMO * 0.8:
                self.lbl_aforo.configure(text_color="#FFD100") # Amarillo
            else:
                self.lbl_aforo.configure(text_color="#00FF00") # Verde

    def mostrar_mensaje_pantalla(self, texto, bg_color, txt_color="#FFFFFF"):
        self.lbl_mensaje.configure(text=texto, fg_color=bg_color, text_color=txt_color)

    def actualizar_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)

            # Pipeline Fase 2
            frame_anotado, personas, rostros, gafetes = self.vision.procesar_frame(frame)

            # Logica de validacion
            ahora = time.time()
            if ahora - self.tiempo_ultimo_escaneo > self.cooldown_segundos:
                # Regresar al estado amarillo por defecto
                self.mostrar_mensaje_pantalla("MUESTRE SU CÓDIGO QR", "#FFD100", "#0A0A0A")
                if gafetes:
                    codigo = gafetes[0]["data"]
                    self.procesar_acceso(codigo, frame)
                    self.tiempo_ultimo_escaneo = ahora

            img_pil = Image.fromarray(cv2.cvtColor(frame_anotado, cv2.COLOR_BGR2RGB))
            img_tk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(640, 480))
            self.lbl_video.configure(image=img_tk)
            self.lbl_video.image = img_tk

        self.after(15, self.actualizar_video)

    def procesar_acceso(self, qr_id, frame_actual):
        self.c.execute("SELECT * FROM boletos WHERE id=?", (qr_id,))
        boleto = self.c.fetchone()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_captura = os.path.join(config.DIR_CAPTURAS, f"{qr_id}_{timestamp}.jpg")
        cv2.imwrite(ruta_captura, frame_actual)

        if not boleto:
            self.mostrar_mensaje_pantalla("ACCESO DENEGADO\nQR no registrado.", "#E32626")
            return

        b_id, titular, fecha, tipo, personas, estado = boleto
        fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

        # Fase 3: Regla de negocio para límite de aforo
        self.c.execute("SELECT SUM(personas) FROM boletos WHERE estado='INGRESADO'")
        resultado = self.c.fetchone()[0]
        aforo_actual = resultado if resultado else 0
        
        if aforo_actual + personas > config.AFORO_MAXIMO:
            self.mostrar_mensaje_pantalla(f"AFORO MÁXIMO ALCANZADO\nIntento de ingreso: {personas} persona(s)", "#E32626")
            return

        if fecha != fecha_hoy:
            self.mostrar_mensaje_pantalla(f"ACCESO DENEGADO\nBoleto para {fecha}. Hoy es {fecha_hoy}.", "#E32626")
            self.c.execute("UPDATE boletos SET estado='RECHAZADO' WHERE id=?", (b_id,))
            self.conn.commit()
            self.actualizar_contadores()
            return

        if estado == 'INGRESADO':
            self.mostrar_mensaje_pantalla("ACCESO DENEGADO\nBoleto ya utilizado.", "#E32626")
            return

        if tipo == "VIP":
            self.mostrar_mensaje_pantalla(f"PASE VIP: {titular}\nAcceso a zona preferencial.", "#B8860B")
            self.c.execute("UPDATE boletos SET estado='INGRESADO' WHERE id=?", (b_id,))
            self.conn.commit()
            self.actualizar_contadores()
            return

        self.c.execute("UPDATE boletos SET estado='INGRESADO' WHERE id=?", (b_id,))
        self.conn.commit()
        self.actualizar_contadores()
        self.mostrar_mensaje_pantalla(f"BIENVENIDO {titular}\nDispensando {personas} brazalete(s)...", "#006400")

    def destroy(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'conn'):
            self.conn.close()
        super().destroy()

if __name__ == "__main__":
    app = KioscoAccesoApp()
    app.mainloop()