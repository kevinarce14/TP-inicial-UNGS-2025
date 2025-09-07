from flask import Flask, jsonify, render_template, request
import sqlite3
import sys
import os
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from src.logica.administrador_database import DatabaseManager
db_manager = DatabaseManager()

app = Flask(__name__, template_folder="templates", static_folder="static")

#DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "asistencia_empleados.db")
DB_RUTA = 'database/asistencia_empleados.db'

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

# Ruta para detectar rostro con OpenCV
@app.route('/api/detectar_rostro', methods=['POST'])
def detectar_rostro():
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    if not nombre or not apellido:
        return jsonify({'success': False, 'message': 'Nombre y apellido son requeridos'}), 400

    # Obtener la imagen desde el formulario
    if 'frame' not in request.files:
        return jsonify({'success': False, 'message': 'No se proporcionó un frame'}), 400
    frame_file = request.files['frame']
    
    # Convertir el archivo a imagen
    img = Image.open(frame_file)
    img = np.array(img)  # Convertir a formato numpy para OpenCV
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # Convertir de RGB a BGR

    # Cargar el clasificador de rostros de OpenCV
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        return jsonify({'success': False, 'message': 'Error al cargar el clasificador de rostros'}), 500

    # Convertir a escala de grises para detección
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(50, 50))
    
    print(f"Rostros detectados por OpenCV: {len(faces)}")  # Depuración
    if len(faces) > 0:
        # Obtener el último ID_Empleado y asignar el siguiente
        last_id = query_db("SELECT MAX(ID_Empleado) FROM empleados", one=True)
        new_id = (last_id[0] or 0) + 1 if last_id else 1
        # Rostro detectado, guardar la imagen
        foto_path = os.path.join('imagenes_empleados', f'{nombre}_{apellido}{new_id}.png')
        os.makedirs('imagenes_empleados', exist_ok=True)
        cv2.imwrite(foto_path, img)
        print(f"Foto guardada en: {foto_path}")
        return jsonify({'success': True, 'foto_path': foto_path})
    else:
        return jsonify({'success': False, 'message': 'No se detectó un rostro'})

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

# Otras rutas (como /api/empleados, /api/asistencias, etc.)
# Asegúrate de incluir las rutas existentes para que el resto del frontend funcione

# Ruta para borrar foto
@app.route('/api/borrar_foto', methods=['POST'])
def borrar_foto():
    foto_path = request.json['foto_path']
    if os.path.exists(foto_path):
        os.remove(foto_path)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Foto no encontrada'})

if __name__ == "__main__":
    app.run(debug=True)


