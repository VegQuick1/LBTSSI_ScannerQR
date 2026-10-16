## Requisitos Previos

Antes de ejecutar el proyecto, asegúrate de tener instalado en tu equipo:
1. **Python** (Versión 3.10 o superior recomendada). *Nota: Asegúrate de marcar la casilla "Add Python to PATH" durante su instalación.*
2. **Visual Studio Code** (o cualquier IDE de tu preferencia).

---

## Instalación y Configuración

Una vez que descargues o clones este repositorio en tu computadora, abre la carpeta del proyecto en tu terminal o en Visual Studio Code.

### 1. Instalar las dependencias necesarias
El sistema requiere librerías específicas para el manejo de la interfaz gráfica, la cámara, la base de datos y la decodificación de códigos QR.
Ejecuta el siguiente comando en la terminal:


pip install opencv-python pyzbar customtkinter pillow qrcode



*Abre la carpeta del proyecto en Visual Studio Code.
*Abre una terminal integrada en la ruta del proyecto.
*Ejecuta el script principal con el siguiente comando:

python main.py

-------------------------------------------------------------------------------------------------------------------------------------------


Guía de Uso del Sistema
Pestaña 1: Admin / Generar QR (Panel de Pruebas)
Para poder probar el escáner sin necesidad de boletos reales, puedes generar tus propios códigos de prueba:

Entra a la pestaña Admin / Generar QR.

Rellena los campos solicitados:

ID del Boleto: Un identificador único (ejemplo: TKT-001).

Nombre del Titular: Nombre de la persona.

Fecha: Formato YYYY-MM-DD (puedes dejar la fecha actual para que sea un acceso válido).

Tipo: Selecciona entre General o VIP.

Cantidad de personas: Número de personas incluidas en el boleto (simula la entrega de brazaletes).

Haz clic en Generar QR y Guardar en DB. Esto creará automáticamente una imagen PNG con el código QR en la carpeta del proyecto y guardará el registro en la base de datos local (boletos_conve.db).






Pestaña 2: Escáner (Touch Screen)
Cambia a la pestaña principal Escaner.

Abre la imagen del código QR que generaste (puedes abrirla en la pantalla de tu celular o en otra ventana de tu PC).

Colócala frente a la cámara web. En el preciso instante en que el sistema lea el código QR:

Se tomará y guardará automáticamente una fotografía de auditoría del fotograma actual. Esta captura incluye tanto el código QR escaneado como el rostro de la persona frente a la cámara, almacenándose en la carpeta local capturas_seguridad/ para mayor seguridad del evento.

El sistema validará la fecha y el tipo de boleto.

Mostrará el mensaje de acceso correspondiente (éxito con simulación de brazaletes, rechazo por fecha, o redirección a zona VIP).

Actualizará en tiempo real los contadores de Entradas y Rechazos.





Visualización de la Base de Datos (.db)
El sistema utiliza una base de datos local basada en SQLite (boletos_conve.db). Si deseas visualizar el contenido de las tablas directamente en Visual Studio Code:

Ve a la sección de Extensiones en VS Code (Ctrl + Shift + X).

Busca e instala la extensión SQLite Viewer.

Haz doble clic sobre el archivo boletos_conve.db en el explorador de archivos para ver y consultar los registros en tiempo real.



### 1. Instalar las dependencias necesarias
El proyecto incluye un archivo `requirements.txt` con todas las librerías necesarias configuradas. Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python -m pip install -r requirements.txt