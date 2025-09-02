import threading
import cv2
import face_recognition
import os
import time
import sqlite3
import numpy as np
from datetime import datetime, date, time as dt_time, timedelta
from collections import deque


# CONFIGURACIÓN
TOLERANCIA = 0.6
GROSOR_MARCO_CARA = 3
GROSOR_FUENTE_MARCO = 2
MODEL = 'hog'
DB_RUTA = 'database/asistencia_empleados.db'

DURACION_MENSAJE = 5 
MAX_CANT_MENSAJES = 5 

TURNOS = {
    'Mañana': {'inicio': dt_time(7, 30), 'fin': dt_time(15, 30)},
    'Tarde': {'inicio': dt_time(15, 30), 'fin': dt_time(23, 30)},
    'Noche': {'inicio': dt_time(23, 30), 'fin': dt_time(7, 30)}
}

# VERIFICACIÓN INICIAL
def verificar_tablas():
    if not os.path.exists(DB_RUTA):
        print("La base de datos no existe. Creándola...")
        try:
            from src.gestor_database.create_database import create_database
            create_database()
        except ImportError:
            print("ERROR: No se pudo importar create_database")
    else:
        conexion = sqlite3.connect(DB_RUTA)
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM empleados")
            conexion.close()
        except sqlite3.OperationalError:
            print("Las tablas no existen. Creándolas...")
            conexion.close()
            try:
                from src.gestor_database.create_database import create_database
                create_database()
            except ImportError:
                print("ERROR: No se pudo importar create_database")

print("Verificando base de datos...")
verificar_tablas()

# FUNCIONES DE BASE DE DATOS
def cargando_embeddings_db():
    conexion = sqlite3.connect(DB_RUTA)
    cursor = conexion.cursor()
    
    cursor.execute("SELECT ID_Empleado, Nombre, Apellido, Embedding FROM empleados")
    filas = cursor.fetchall()
    
    empleados_caras = []
    empleados_nombres = []
    empleados_ids = []
    
    for fila in filas:
        empleado_id, nombre, apellido, embedding_blob = fila
        embedding = np.frombuffer(embedding_blob, dtype=np.float32)
        empleados_caras.append(embedding)
        nombre_completo = (nombre + " " + apellido)
        empleados_nombres.append(nombre_completo)
        empleados_ids.append(empleado_id)
    
    conexion.close()
    return empleados_caras, empleados_nombres, empleados_ids

print("Cargando imágenes conocidas desde la base de datos...")
empleados_caras, empleados_nombres, empleados_ids = cargando_embeddings_db()

print("Listo! Iniciando cámara...")

#---------------------------------------------------------------------------------------------------------------
# VARIABLES COMPARTIDAS ENTRE HILOS
frame_lock = threading.Lock()
lock_mensajes = threading.Lock()
current_frame = None
current_results = []

# Para reutilizar encodings previos
last_matches = []  # [(id_empleado, nombre, (top,right,bottom,left)), ...]

mensajes_pantalla = deque(maxlen=MAX_CANT_MENSAJES)

class ScreenMessage:
    def __init__(self, mensaje, mensaje_tipo='info'):
        self.text = mensaje
        self.timestamp = time.time()
        self.tipo = mensaje_tipo
        
    def is_expired(self):
        return time.time() - self.timestamp > DURACION_MENSAJE

def agregar_mensaje_pantalla(mensaje, mensaje_tipo='info'):
    with lock_mensajes:
        mensajes_pantalla.append(ScreenMessage(mensaje, mensaje_tipo))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {mensaje}")

def get_color_por_tipo(mensaje_tipo):
    colores = {
        'success': (0, 150, 0),
        'error': (0, 0, 255),
        'warning': (0, 165, 255),
        'info': (255, 255, 255)
    }
    return colores.get(mensaje_tipo, (255, 255, 255))

def misma_cara(loc1, loc2, threshold=50):
    return abs(loc1[0] - loc2[0]) < threshold and abs(loc1[1] - loc2[1]) < threshold

def determinar_turno_actual():
    ahora = datetime.now().time()
    hora_actual = ahora.hour + ahora.minute/60
    
    if 7.5 <= hora_actual < 15.5:
        return 'Mañana'
    elif 15.5 <= hora_actual < 23.5:
        return 'Tarde'
    else:
        return 'Noche'

def calcular_minutos_tarde(hora_ingreso, turno):
    ahora = datetime.now()
    hora_ingreso_dt = datetime.combine(ahora.date(), hora_ingreso)
    
    if turno == 'Mañana':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Mañana']['inicio'])
    elif turno == 'Tarde':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Tarde']['inicio'])
    else:
        if ahora.hour < 12:
            hora_esperada = datetime.combine(ahora.date() - timedelta(days=1), TURNOS['Noche']['inicio'])
        else:
            hora_esperada = datetime.combine(ahora.date(), TURNOS['Noche']['inicio'])
    
    diferencia = hora_ingreso_dt - hora_esperada
    minutos_tarde = max(0, int(diferencia.total_seconds() / 60))
    return minutos_tarde

def determinar_observacion(minutos_tarde):
    """Determina la observación basada en los minutos de tardanza"""
    if minutos_tarde <= 10:
        return 'Puntual'
    elif minutos_tarde <= 30:
        return 'Medio Tarde'
    else:
        return 'Muy Tarde'

def registrar_asistencia(empleado_id, nombre_completo):
    conexion = sqlite3.connect(DB_RUTA)
    cursor = conexion.cursor()
    
    cursor.execute("SELECT Turno FROM empleados WHERE ID_Empleado = ?", (empleado_id,))
    resultado = cursor.fetchone()
    turno_empleado = resultado[0]
    
    ahora = datetime.now()
    fecha_actual = ahora.date().isoformat()
    hora_actual = ahora.strftime("%H:%M:%S")
    turno_actual = determinar_turno_actual()
    
    # Verificaa si ya existe un registro de ingreso para hoy
    cursor.execute('''
    SELECT ID_Asistencia, Hora_Ingreso, Hora_Egreso 
    FROM asistencias 
    WHERE ID_Empleado = ? AND Fecha = ?
    ''', (empleado_id, fecha_actual))
    
    registro = cursor.fetchone()
    
    if registro:
        agregar_mensaje_pantalla(f"{nombre_completo} ya fue verificado hoy", 'success')
    else:
        if turno_empleado != turno_actual:
            agregar_mensaje_pantalla(f"Acceso denegado: {nombre_completo} no pertenece al turno {turno_actual}", 'error')
            conexion.close()
            return False
        
        minutos_tarde = calcular_minutos_tarde(ahora.time(), turno_empleado)
        
        if minutos_tarde > 120:
            agregar_mensaje_pantalla(f"Acceso denegado: {nombre_completo} llegó {minutos_tarde} minutos tarde", 'error')
            conexion.close()
            return False
        
        observacion = determinar_observacion(minutos_tarde)
        
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, ?, TRUE, ?, ?)
        ''', (fecha_actual, empleado_id, turno_empleado, hora_actual, minutos_tarde, observacion))
        
        if observacion == 'Puntual':
            agregar_mensaje_pantalla(f"Ingreso registrado para {nombre_completo} a las {hora_actual}", 'success')
        else:
            agregar_mensaje_pantalla(f"Ingreso registrado para {nombre_completo} a las {hora_actual}. {observacion}", 'warning')
    
    conexion.commit()
    conexion.close()
    return True

def draw_messages_on_frame(frame):
    """Dibujar mensajes en el frame"""
    with lock_mensajes:
        # Limpiar mensajes expirados
        while mensajes_pantalla and mensajes_pantalla[0].is_expired():
            mensajes_pantalla.popleft()
        
        # Dibujar mensajes actuales
        y_offset = 30
        for message in mensajes_pantalla:
            color = get_color_por_tipo(message.tipo)
            
            text_size = cv2.getTextSize(message.text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(frame, (10, y_offset - 25), (text_size[0] + 20, y_offset + 5), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, y_offset - 25), (text_size[0] + 20, y_offset + 5), color, 2)
            
            # Texto del mensaje
            cv2.putText(frame, message.text, (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            y_offset += 45

# HILO DE CAPTURA
def capture_thread():
    global current_frame
    try:
        video = cv2.VideoCapture(0)
        if not video.isOpened():
            agregar_mensaje_pantalla("Error: No se pudo abrir la cámara", 'error')
            return
            
        video.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
        video.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)
        
        while True:
            ret, frame = video.read()
            if not ret:
                agregar_mensaje_pantalla("Error: No se pudo leer el frame de la cámara", 'error')
                break
            with frame_lock:
                current_frame = frame.copy()
    except Exception as e:
        agregar_mensaje_pantalla(f"Error en hilo de captura: {e}", 'error')
    finally:
        if 'video' in locals():
            video.release()

# HILO DE RECONOCIMIENTO
def recognition_thread():
    global current_frame, current_results, last_matches
    # Para evitar registrar múltiples veces la misma asistencia
    ultimo_registro = {}
    
    while True:
        time.sleep(0.05)  # evita uso 100% CPU

        with frame_lock:
            if current_frame is None:
                continue
            frame = current_frame.copy()

        # Redimensionar para acelerar
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Detectar ubicaciones
        face_locations = face_recognition.face_locations(small_frame, model=MODEL)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        # Escalar ubicaciones al tamaño original
        face_locations = [(t*4, r*4, b*4, l*4) for (t, r, b, l) in face_locations]

        current_matches = []

        for face_encoding, face_location in zip(face_encodings, face_locations):
            match_id = None
            match_name = None

            # Reutilizar coincidencia anterior si la cara está cerca
            for last_id, last_name, last_loc in last_matches:
                if misma_cara(face_location, last_loc):
                    match_id = last_id
                    match_name = last_name
                    break

            # Si no estaba, comparar contra base de datos
            if match_id is None:
                results = face_recognition.compare_faces(empleados_caras, face_encoding, TOLERANCIA)
                if True in results:
                    match_index = results.index(True)
                    match_id = empleados_ids[match_index]
                    match_name = empleados_nombres[match_index]
                    
                    # Registrar asistencia (solo una vez cada 30 segundos por persona)
                    ahora = time.time()
                    if match_id not in ultimo_registro or ahora - ultimo_registro[match_id] > 30:
                        registrar_asistencia(match_id, match_name)
                        ultimo_registro[match_id] = ahora

            current_matches.append((match_id, match_name, face_location))

        # Actualizar variables compartidas
        with frame_lock:
            current_results = current_matches
            last_matches = current_matches.copy()

# INICIO DE HILOS
threading.Thread(target=capture_thread, daemon=True).start()
threading.Thread(target=recognition_thread, daemon=True).start()

# BUCLE PRINCIPAL DE VISUALIZACIÓN

try:
    while True:
        with frame_lock:
            if current_frame is None:
                time.sleep(0.1)
                continue
            frame = current_frame.copy()
            results = current_results.copy()

        # Dibujar resultados de reconocimiento facial
        for emp_id, name, (top, right, bottom, left) in results:
            color = (0, 255, 0) if emp_id else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, GROSOR_MARCO_CARA)
            if name:
                # Fondo para el nombre
                text_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.7, GROSOR_FUENTE_MARCO)[0]
                cv2.rectangle(frame, (left, top-35), (left + text_size[0] + 10, top), color, -1)
                cv2.putText(frame, name, (left + 5, top-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), GROSOR_FUENTE_MARCO)

        draw_messages_on_frame(frame)

        # Mostrar hora actual en esquina superior derecha
        hora_actual = datetime.now().strftime("%H:%M:%S")
        turno_actual = determinar_turno_actual()
        info_text = f"{hora_actual} - Turno: {turno_actual}"
        text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        frame_width = frame.shape[1]
        
        cv2.rectangle(frame, (frame_width - text_size[0] - 15, 5), 
                     (frame_width - 5, 35), (0, 0, 0), -1)
        cv2.putText(frame, info_text, (frame_width - text_size[0] - 10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Sistema de Control de Asistencia", frame)
        
        # Salir con 'q' o si la ventana se cierra
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
            
        # Verificar si la ventana todavía existe
        if cv2.getWindowProperty("Sistema de Control de Asistencia", cv2.WND_PROP_VISIBLE) < 1:
            break

except Exception as e:
    agregar_mensaje_pantalla(f"Error en el bucle principal: {e}", 'error')
    print(f"Error en el bucle principal: {e}")

finally:
    # Este bloque se ejecuta siempre, incluso si hay error
    try:
        cv2.destroyAllWindows()
    except:
        pass  # Ignorar errores al cerrar