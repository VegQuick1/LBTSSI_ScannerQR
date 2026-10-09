import cv2
import customtkinter as ctk
from PIL import Image, ImageTk
import datetime
import sqlite3
import qrcode
import os
import time
from vision_engine import VisionEngine

if not os.path.exists("capturas_seguridad"):
    os.makedirs("capturas_seguridad")

class KioscoAccesoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Control de Acceso - La Conve")
        self.geometry("1024x768")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.ultimo_qr = None
        self.tiempo_ultimo_escaneo = 0
        self.cooldown_segundos = 4

        self.init_db()

        # Motor de vision computacional (Fase 2)
        self.vision = VisionEngine()

        # Camara
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)

        # Pestañas
        self.tabview = ctk.CTkTabview(self, width=1000, height=740)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_escaner = self.tabview.add("Escaner (Touch Screen)")
        self.tab_admin = self.tabview.add("Admin / Generar QR")

        self.setup_escaner_tab()
        self.setup_admin_tab()

        self.actualizar_video()

    def init_db(self):
        self.conn = sqlite3.connect('boletos_conve.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS boletos
                         (id TEXT PRIMARY KEY, titular TEXT, fecha TEXT, tipo TEXT, personas INTEGER, estado TEXT)''')
        self.conn.commit()

    def setup_escaner_tab(self):
        self.frame_contadores = ctk.CTkFrame(self.tab_escaner)
        self.frame_contadores.pack(pady=10, fill="x")

        self.lbl_entradas = ctk.CTkLabel(self.frame_contadores, text="Entradas: 0", font=("Arial", 22, "bold"))
        self.lbl_entradas.pack(side="left", expand=True)

        self.lbl_rechazos = ctk.CTkLabel(self.frame_contadores, text="Rechazos: 0", font=("Arial", 22, "bold"))
        self.lbl_rechazos.pack(side="left", expand=True)

        self.lbl_video = ctk.CTkLabel(self.tab_escaner, text="")
        self.lbl_video.pack(pady=10)

        self.lbl_mensaje = ctk.CTkLabel(self.tab_escaner, text="Muestre su codigo QR a la camara", 
                                        font=("Arial", 24, "bold"), fg_color="#333333", 
                                        corner_radius=10, height=80)
        self.lbl_mensaje.pack(pady=15, fill="x", padx=40)

        self.actualizar_contadores()

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

    def generar_qr(self):
        b_id = self.ent_id.get().strip()
        titular = self.ent_titular.get().strip()
        fecha = self.ent_fecha.get().strip()
        tipo = self.combo_tipo.get()
        personas = self.ent_personas.get().strip()

        if not all([b_id, titular, fecha, personas]):
            self.lbl_admin_msg.configure(text="Llene todos los campos requeridos", text_color="red")
            return

        try:
            self.c.execute("INSERT INTO boletos VALUES (?, ?, ?, ?, ?, 'SIN USAR')", 
                           (b_id, titular, fecha, tipo, int(personas)))
            self.conn.commit()
            
            img_qr = qrcode.make(b_id)
            img_qr.save(f"{b_id}.png")
            
            self.lbl_admin_msg.configure(text=f"Boleto {b_id} registrado con exito.", text_color="green")
            self.actualizar_contadores()
        except sqlite3.IntegrityError:
            self.lbl_admin_msg.configure(text="Error: El ID ya se encuentra registrado.", text_color="red")

    def actualizar_contadores(self):
        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='INGRESADO'")
        entradas = self.c.fetchone()[0]
        self.c.execute("SELECT COUNT(*) FROM boletos WHERE estado='RECHAZADO'")
        rechazos = self.c.fetchone()[0]
        
        self.lbl_entradas.configure(text=f"Entradas: {entradas}")
        self.lbl_rechazos.configure(text=f"Rechazos: {rechazos}")

    def mostrar_mensaje_pantalla(self, texto, color):
        self.lbl_mensaje.configure(text=texto, fg_color=color)

    def actualizar_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)

            # Pipeline Fase 2: personas, rostros en movimiento y gafetes
            frame_anotado, personas, rostros, gafetes = self.vision.procesar_frame(frame)

            # Logica de validacion y cooldown
            ahora = time.time()
            if ahora - self.tiempo_ultimo_escaneo > self.cooldown_segundos:
                self.mostrar_mensaje_pantalla("Muestre su codigo QR a la camara", "#333333")
                if gafetes:
                    codigo = gafetes[0]["data"]
                    self.procesar_acceso(codigo, frame)
                    self.tiempo_ultimo_escaneo = ahora

            # Renderizar en Tkinter
            img_pil = Image.fromarray(cv2.cvtColor(frame_anotado, cv2.COLOR_BGR2RGB))
            img_tk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(640, 480))
            self.lbl_video.configure(image=img_tk)
            self.lbl_video.image = img_tk

        self.after(15, self.actualizar_video)

    def procesar_acceso(self, qr_id, frame_actual):
        self.c.execute("SELECT * FROM boletos WHERE id=?", (qr_id,))
        boleto = self.c.fetchone()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"capturas_seguridad/{qr_id}_{timestamp}.jpg", frame_actual)

        if not boleto:
            self.mostrar_mensaje_pantalla("Acceso denegado: QR no registrado.", "#8B0000")
            return

        b_id, titular, fecha, tipo, personas, estado = boleto
        fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

        if fecha != fecha_hoy:
            self.mostrar_mensaje_pantalla(f"Acceso denegado: Boleto para {fecha}.\nHoy es {fecha_hoy}.", "#8B0000")
            self.c.execute("UPDATE boletos SET estado='RECHAZADO' WHERE id=?", (b_id,))
            self.conn.commit()
            self.actualizar_contadores()
            return

        if estado == 'INGRESADO':
            self.mostrar_mensaje_pantalla("Acceso denegado: Boleto ya utilizado.", "#8B0000")
            return

        if tipo == "VIP":
            self.mostrar_mensaje_pantalla(f"Pase VIP: {titular}.\nAcceso concedido a zona preferencial.", "#B8860B")
            self.c.execute("UPDATE boletos SET estado='INGRESADO' WHERE id=?", (b_id,))
            self.conn.commit()
            self.actualizar_contadores()
            return

        self.c.execute("UPDATE boletos SET estado='INGRESADO' WHERE id=?", (b_id,))
        self.conn.commit()
        self.actualizar_contadores()
        self.mostrar_mensaje_pantalla(f"Bienvenido {titular}.\nDispensando {personas} brazalete(s)...", "#006400")

    def destroy(self):
        if self.cap.isOpened():
            self.cap.release()
        self.conn.close()
        super().destroy()

if __name__ == "__main__":
    app = KioscoAccesoApp()
    app.mainloop()