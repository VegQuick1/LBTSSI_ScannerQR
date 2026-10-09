import cv2
import numpy as np
import pyzbar.pyzbar as pyzbar
import math
import os
import urllib.request

class VisionEngine:
    #Alaroña con el nombre largo del xml
    def __init__(self, face_xml_path='haarcascade_frontalface_default.xml', movimiento_umbral=8.0):
        self.movimiento_umbral = movimiento_umbral
        self.centroides_previos = [] #Posiciones del anterior fotograma

        #Validación de que el modelo está aún si se elimina por accidente
        if not os.path.exists(face_xml_path):
            url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
            try:
                urllib.request.urlretrieve(url, face_xml_path)
            except Exception:
                pass

        self.face_cascade = cv2.CascadeClassifier(face_xml_path)

        #Detector preentrenado de siluetas de personas
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detectar_personas(self, frame):
        h, w = frame.shape[:2]
        small_frame = cv2.resize(frame, (320, int(h * (320 / w))))

        cajas, _ = self.hog.detectMultiScale(
            small_frame, 
            winStride=(8, 8), 
            padding=(4, 4), 
            scale=1.05
        )

        escala_x = w / 320.0
        escala_y = h / small_frame.shape[0]

        personas = []
        for (x, y, bw, bh) in cajas:
            rx = int(x * escala_x)
            ry = int(y * escala_y)
            rw = int(bw * escala_x)
            rh = int(bh * escala_y)
            personas.append((rx, ry, rw, rh))
        return personas

    def detectar_rostros_en_movimiento(self, frame, gray):
        rostros_detectados = []
        if self.face_cascade.empty():
            return rostros_detectados

        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(60, 60)
        )

        nuevos_centroides = []
        for (x, y, w, h) in faces:
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            nuevos_centroides.append((cx, cy))

            #Cálculo del desplazamiento 
            desplazamiento = 0.0
            if self.centroides_previos:
                distancias = [math.hypot(cx - pcx, cy - pcy) for (pcx, pcy) in self.centroides_previos]
                desplazamiento = min(distancias) if distancias else 0.0

            en_movimiento = desplazamiento >= self.movimiento_umbral
            rostros_detectados.append({
                "bbox": (x, y, w, h),
                "centroide": (cx, cy),
                "desplazamiento": desplazamiento,
                "en_movimiento": en_movimiento
            })

        self.centroides_previos = nuevos_centroides
        return rostros_detectados

    def leer_patrones_gafete(self, frame):
        gafetes = []
        codigos = pyzbar.decode(frame)
        for obj in codigos:
            data = obj.data.decode('utf-8')
            puntos = obj.polygon
            if len(puntos) == 4:
                pts = [(p.x, p.y) for p in puntos]
            else:
                x, y, w, h = obj.rect
                pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            gafetes.append({"data": data, "pts": pts})
        return gafetes

    def procesar_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        personas = self.detectar_personas(frame)
        rostros = self.detectar_rostros_en_movimiento(frame, gray)
        gafetes = self.leer_patrones_gafete(frame)

        for (x, y, w, h) in personas:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 120, 0), 2)
            cv2.putText(frame, "Persona Detectada", (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 120, 0), 2)

        for r in rostros:
            x, y, w, h = r["bbox"]
            color = (0, 255, 0) if r["en_movimiento"] else (0, 215, 255)
            tag = "Rostro en Movimiento" if r["en_movimiento"] else "Rostro Estatico"
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{tag} ({r['desplazamiento']:.1f}px)", (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for g in gafetes:
            pts = np.array(g["pts"], np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (255, 0, 255), 3)
            p0 = g["pts"][0]
            cv2.putText(frame, f"Gafete: {g['data']}", (p0[0], max(20, p0[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

        return frame, personas, rostros, gafetes