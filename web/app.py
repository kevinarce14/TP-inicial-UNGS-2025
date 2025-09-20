import face_recognition
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg2
import cv2
import numpy as np
import os
from io import BytesIO
from PIL import Image
import subprocess
import threading
import sys
from src.logica.administrador_database import DatabaseManager

import json
from datetime import date, datetime

# Configuración de conexión a Neon
#DB_CONFIG = {
#    'host': "ep-wispy-breeze-acjxjbvm-pooler.sa-east-1.aws.neon.tech",
#    'port': 5432,
#    'dbname': "neondb",
#    'user': "neondb_owner",
#    'password': "npg_gRD2wkVuvYH4",
#    'sslmode': "require"
#}

DB_CONFIG = {
    'host': os.environ.get("DB_HOST", "ep-wispy-breeze-acjxjbvm-pooler.sa-east-1.aws.neon.tech"),
    'port': int(os.environ.get("DB_PORT", 5432)),
    'dbname': os.environ.get("DB_NAME", "neondb"),
    'user': os.environ.get("DB_USER", "neondb_owner"),
    'password': os.environ.get("DB_PASSWORD", "npg_gRD2wkVuvYH4"),
    'sslmode': os.environ.get("DB_SSLMODE", "require")
}

app = FastAPI(title="Asistencia API")

db_manager = DatabaseManager()

# Templates y static - Solo si existen los directorios
templates = None
if os.path.exists("web/templates"):
    templates = Jinja2Templates(directory="web/templates")

if os.path.exists("web/static"):
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

# -----------------------
#   Funciones DB
# -----------------------
def query_db(query, args=(), one=False):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query, args)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        result = []
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                # Convertir Decimal a float para serialización JSON
                if hasattr(value, 'isoformat'):  # datetime, date, time objects
                    row_dict[colnames[i]] = value.isoformat()
                elif hasattr(value, 'to_eng_string'):  # Decimal objects
                    row_dict[colnames[i]] = float(value)
                else:
                    row_dict[colnames[i]] = value
            result.append(row_dict)
        return (result[0] if result else None) if one else result
    except Exception as e:
        print(f"Error en query_db: {e}")
        return [] if not one else None
    finally:
        if conn:
            conn.close()


# -----------------------
#   Rutas
# -----------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("<h1>API de Asistencia</h1><p>Directorios de templates no encontrados</p>")

@app.get("/api/empleados")
async def empleados():
    try:
        rows = query_db("""
            SELECT id_empleado, nombre, apellido, departamento, turno
            FROM empleados
            ORDER BY id_empleado
        """)
        return JSONResponse(content=rows)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get("/api/asistencias")
async def asistencias():
    try:
        rows = query_db("""
            SELECT 
                id_asistencia,
                fecha,
                id_empleado,
                turno,
                hora_ingreso,
                hora_egreso,
                estado_asistencia,
                minutos_tarde,
                observacion
            FROM asistencias
            ORDER BY fecha DESC, id_asistencia DESC
        """)
        return JSONResponse(content=rows)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get("/api/denegaciones")
async def denegaciones():
    try:
        rows = query_db("""
            SELECT 
                id_denegacion,
                fecha,
                hora,
                id_empleado,
                motivo,
                modo_operacion
            FROM denegaciones
            ORDER BY fecha DESC, hora DESC
        """)
        return JSONResponse(content=rows)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get("/api/produccion")
async def produccion():
    try:
        rows = query_db("""
            SELECT 
                id_produccion,
                fecha,
                turno,
                id_empleado,
                producto,
                produccion_real as production_real,
                produccion_buena as production_buena,
                produccion_defectuosa as production_defectuosa,
                tiempo_planificado,
                tiempo_paradas,
                tiempo_operativo,
                oee,
                disponibilidad,
                rendimiento,
                calidad,
                observaciones
            FROM produccion
            ORDER BY fecha DESC, id_produccion DESC
        """)
        return JSONResponse(content=rows)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.post("/api/detectar_rostro")
async def detectar_rostro(nombre: str = Form(...), apellido: str = Form(...), frame: UploadFile = None):
    try:
        if not frame:
            return JSONResponse(status_code=400, content={'success': False, 'message': 'No se proporcionó un frame'})

        print("🔄 Procesando imagen para detección facial...")
        
        # Leer y procesar la imagen
        img_bytes = await frame.read()
        img = Image.open(BytesIO(img_bytes))
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Usar face_recognition (el mismo método que tu sistema principal)
        print("🔍 Detectando rostros con face_recognition...")
        
        # Redimensionar para acelerar (igual que en tu sistema)
        FRAME_SCALE = 0.25
        small_frame = cv2.resize(img, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE)
        
        # Detectar ubicaciones de rostros
        face_locations = face_recognition.face_locations(small_frame, model='hog')
        
        print(f"📊 Rostros detectados: {len(face_locations)}")

        if len(face_locations) == 0:
            print("❌ No se detectó ningún rostro")
            return JSONResponse(content={
                'success': False, 
                'message': 'No se detectó ningún rostro. Asegúrese de que la cara esté visible y bien iluminada.'
            })
        
        if len(face_locations) > 1:
            print("❌ Se detectó más de un rostro")
            return JSONResponse(content={
                'success': False, 
                'message': 'Se detectó más de un rostro. Por favor, capture solo una persona.'
            })

        # Obtener el siguiente ID disponible consultando la base de datos
        print("🔢 Obteniendo próximo ID de empleado...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id_empleado), 0) FROM empleados")
        max_id = cur.fetchone()[0]
        new_id = max_id + 1
        cur.close()
        conn.close()

        # Guardar la imagen
        os.makedirs('imagenes_empleados', exist_ok=True)
        foto_path = os.path.join('imagenes_empleados', f'{nombre}_{apellido}_{new_id}.png')
        cv2.imwrite(foto_path, img)

        print(f"✅ Rostro detectado correctamente. Imagen guardada en: {foto_path}")

        return JSONResponse(content={
            'success': True,
            'foto_path': foto_path,
            'id_empleado': new_id,
            'faces_count': len(face_locations),
            'message': 'Rostro detectado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error en detectar_rostro: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={
                'success': False, 
                'message': f'Error del servidor: {str(e)}'
            }
        )

@app.post("/api/agregar_empleado")
async def agregar_empleado(
    nombre: str = Form(...),
    apellido: str = Form(...),
    departamento: str = Form(...),
    turno: str = Form(...),
    foto_path: str = Form(...)
):
    try:
        print(f"🎯 === LLAMANDO AGREGAR_EMPLEADO ===")
        print(f"📋 Datos recibidos:")
        print(f"   Nombre: {nombre}")
        print(f"   Apellido: {apellido}")
        print(f"   Departamento: {departamento}")
        print(f"   Turno: {turno}")
        print(f"   Foto path: {foto_path}")
        
        # Verificar que el archivo existe
        if not os.path.exists(foto_path):
            print(f"❌ ERROR: El archivo {foto_path} no existe")
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": f"El archivo {foto_path} no existe"}
            )
        print("✅ Archivo de foto existe")

        # Usar el método del DatabaseManager
        print("🔄 Llamando a db_manager.agregar_empleado()...")
        resultado = db_manager.agregar_empleado(nombre, apellido, departamento, turno, foto_path)
        
        if resultado:
            print("✅ Empleado agregado exitosamente mediante DatabaseManager")
            
            # Verificar que realmente se guardó en la BD
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM empleados WHERE nombre = %s AND apellido = %s", 
                       (nombre, apellido))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            print(f"✅ Verificación BD: {count} empleados con nombre '{nombre} {apellido}'")
            
            return JSONResponse(
                content={
                    "success": True, 
                    "message": "Empleado agregado correctamente"
                }
            )
        else:
            print("❌ Error al agregar empleado mediante DatabaseManager")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "message": "Error al agregar empleado. Verifique los datos e intente nuevamente."
                }
            )
            
    except Exception as e:
        print(f"❌ Error inesperado en agregar_empleado: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={
                "success": False, 
                "message": f"Error inesperado: {str(e)}"
            }
        )

@app.post("/api/ejecutar_totem")
async def ejecutar_totem(modo: str = Form(default="entry")):
    try:
        def ejecutar_en_segundo_plano():
            try:
                comando = [sys.executable, 'main.py', '--mode', modo]
                subprocess.run(comando, capture_output=True, text=True, timeout=30)
            except Exception as e:
                print("Error ejecutando tótem:", e)

        threading.Thread(target=ejecutar_en_segundo_plano).start()
        return JSONResponse(content={"success": True, "message": f"Tótem de {modo} iniciado correctamente"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

##if __name__ == "__main__":
##    import uvicorn
##    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))