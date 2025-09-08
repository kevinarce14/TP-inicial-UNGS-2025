from flask import Flask, jsonify, render_template, request
import sqlite3
import sys
import os
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from src.logica.administrador_database import DatabaseManager
import subprocess
import threading

app = Flask(__name__, template_folder="templates", static_folder="static")

# Ruta de la base de datos
DB_RUTA = 'database/asistencia_empleados.db'
db_manager = DatabaseManager()

def query_db(query, args=(), one=False):
    con = sqlite3.connect(DB_RUTA)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    con.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/empleados")
def empleados():
    rows = query_db("""
        SELECT ID_Empleado, Nombre, Apellido, Departamento, Turno
        FROM empleados
    """)
    return jsonify([dict(row) for row in rows])

@app.route("/api/asistencias")
def asistencias():
    rows = query_db("""
        SELECT ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso,
               Estado_Asistencia, Minutos_Tarde, Observacion
        FROM asistencias
    """)
    return jsonify([dict(row) for row in rows])

@app.route("/api/denegaciones")
def denegaciones():
    rows = query_db("""
        SELECT id_denegacion, fecha, hora, id_empleado, motivo, modo_operacion
        FROM denegaciones
    """)
    return jsonify([dict(row) for row in rows])

@app.route("/api/produccion")
def produccion():
    rows = query_db("""
        SELECT ID_Produccion, Fecha, Turno, Producto, Produccion_Real,
               Produccion_Buena, Produccion_Defectuosa, OEE,
               Disponibilidad, Rendimiento, Calidad
        FROM produccion
    """)
    return jsonify([dict(row) for row in rows])

# Ruta para detectar rostro con OpenCV (mejorada)
@app.route('/api/detectar_rostro', methods=['POST'])
def detectar_rostro():
    print("Solicitud recibida en /api/detectar_rostro")
    try:
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        if not nombre or not apellido:
            print("Faltan nombre o apellido")
            return jsonify({'success': False, 'message': 'Nombre y apellido son requeridos'}), 400

        # Obtener la imagen desde el formulario
        if 'frame' not in request.files:
            print("No se recibió el archivo 'frame'")
            return jsonify({'success': False, 'message': 'No se proporcionó un frame'}), 400
        frame_file = request.files['frame']
        
        # Convertir el archivo a imagen
        img = Image.open(frame_file)
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Cargar el clasificador de rostros de OpenCV
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            print("Clasificador de rostros no cargado")
            return jsonify({'success': False, 'message': 'Error al cargar el clasificador de rostros'}), 500

        # Convertir a escala de grises para detección
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Mejorar la imagen para una mejor detección
        gray = cv2.equalizeHist(gray)
        
        # Detectar rostros con parámetros optimizados
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        print(f"Rostros detectados por OpenCV: {len(faces)}")

        if len(faces) > 0:
            # Obtener el último ID_Empleado y asignar el siguiente
            last_id = query_db("SELECT MAX(ID_Empleado) FROM empleados", one=True)
            new_id = (last_id[0] or 0) + 1 if last_id else 1
            
            # Rostro detectado, guardar la imagen
            os.makedirs('imagenes_empleados', exist_ok=True)
            foto_path = os.path.join('imagenes_empleados', f'{nombre}_{apellido}_{new_id}.png')
            cv2.imwrite(foto_path, img)
            
            print(f"Foto guardada en: {foto_path}")
            return jsonify({
                'success': True, 
                'foto_path': foto_path, 
                'id': new_id,
                'faces_count': len(faces)
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'No se detectó un rostro. Asegúrese de tener buena iluminación y estar frente a la cámara.'
            })
    except Exception as e:
        print(f"Error inesperado: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Ruta para agregar empleado
@app.route('/api/agregar_empleado', methods=['POST'])
def api_agregar_empleado():
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    departamento = request.form['departamento']
    turno = request.form['turno']
    foto_path = request.form['foto_path']
    
    # Llamar a la función de DatabaseManager
    success = db_manager.agregar_empleado(nombre, apellido, departamento, turno, foto_path)
    return jsonify({'success': success})

# Ruta para borrar foto
@app.route('/api/borrar_foto', methods=['POST'])
def borrar_foto():
    foto_path = request.json['foto_path']
    if os.path.exists(foto_path):
        os.remove(foto_path)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Foto no encontrada'})
    
@app.route('/api/ejecutar_totem', methods=['POST'])
def ejecutar_totem():
    try:
        data = request.json
        modo = data.get('modo', 'entry')
        
        # Ejecutar el proceso en segundo plano
        def ejecutar_en_segundo_plano():
            try:
                comando = ['python', 'main.py', '--mode', modo]
                resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)
                print(f"Resultado del tótem ({modo}):", resultado.stdout)
                if resultado.stderr:
                    print("Errores:", resultado.stderr)
            except subprocess.TimeoutExpired:
                print(f"El tótem {modo} tardó demasiado tiempo")
            except Exception as e:
                print(f"Error ejecutando tótem: {e}")
        
        # Ejecutar en un hilo separado para no bloquear Flask
        hilo = threading.Thread(target=ejecutar_en_segundo_plano)
        hilo.start()
        
        return jsonify({'success': True, 'message': f'Tótem de {modo} iniciado correctamente'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == "__main__":
    app.run(debug=True)