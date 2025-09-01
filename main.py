import threading
import cv2
import face_recognition
import os
import time
import sqlite3
import numpy as np
from datetime import datetime, date, time as dt_time, timedelta
from collections import deque

# ------------------------------
# CONFIGURACIÓN
# ------------------------------
TOLERANCE = 0.6
FRAME_THICKNESS = 3
FONT_THICKNESS = 2
MODEL = 'hog'  # 'hog' en CPU, 'cnn' con GPU CUDA
DB_PATH = 'asistencia_empleados.db'

# Configuración de mensajes en pantalla
MESSAGE_DURATION = 5  # segundos que se muestra cada mensaje
MAX_MESSAGES = 5      # máximo número de mensajes en pantalla

# Horarios de los turnos
TURNOS = {
    'Mañana': {'inicio': dt_time(7, 30), 'fin': dt_time(15, 30)},
    'Tarde': {'inicio': dt_time(15, 30), 'fin': dt_time(23, 30)},
    'Noche': {'inicio': dt_time(23, 30), 'fin': dt_time(7, 30)}
}

# ------------------------------
# VERIFICACIÓN INICIAL
# ------------------------------
def verificar_tablas():
    """Verifica si las tablas existen, si no, las crea"""
    if not os.path.exists(DB_PATH):
        print("La base de datos no existe. Creándola...")
        try:
            from create_database import create_database
            create_database()
        except ImportError:
            print("ERROR: No se pudo importar create_database")
    else:
        # Verificar si la tabla empleados existe
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM empleados")
            conn.close()
        except sqlite3.OperationalError:
            print("Las tablas no existen. Creándolas...")
            conn.close()
            try:
                from create_database import create_database
                create_database()
            except ImportError:
                print("ERROR: No se pudo importar create_database")

print("Verificando base de datos...")
verificar_tablas()

# ------------------------------
# FUNCIONES DE BASE DE DATOS
# ------------------------------
def load_known_faces_from_db():
    """Carga los rostros conocidos desde la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT ID_Empleado, Nombre, Apellido, Embedding FROM empleados")
    rows = cursor.fetchall()
    
    known_faces = []
    known_names = []
    employee_ids = []
    
    for row in rows:
        employee_id, nombre, apellido, embedding_blob = row
        # Convertir el BLOB a numpy array (CORRECCIÓN: usar float32)
        embedding = np.frombuffer(embedding_blob, dtype=np.float32)
        known_faces.append(embedding)
        full_name = f"{nombre} {apellido}"
        known_names.append(full_name)
        employee_ids.append(employee_id)
    
    conn.close()
    return known_faces, known_names, employee_ids

print("Cargando imágenes conocidas desde la base de datos...")
known_faces, known_names, employee_ids = load_known_faces_from_db()

print("Listo! Iniciando cámara...")

# ------------------------------
# VARIABLES COMPARTIDAS ENTRE HILOS
# ------------------------------
frame_lock = threading.Lock()
message_lock = threading.Lock()
current_frame = None
current_results = []

# Para reutilizar encodings previos
last_matches = []  # [(id_empleado, nombre, (top,right,bottom,left)), ...]

# Cola de mensajes para mostrar en pantalla
screen_messages = deque(maxlen=MAX_MESSAGES)

class ScreenMessage:
    def __init__(self, text, message_type='info'):
        self.text = text
        self.timestamp = time.time()
        self.type = message_type  # 'success', 'error', 'warning', 'info'
        
    def is_expired(self):
        return time.time() - self.timestamp > MESSAGE_DURATION

def add_screen_message(text, message_type='info'):
    """Agregar mensaje a la cola de mensajes en pantalla"""
    with message_lock:
        screen_messages.append(ScreenMessage(text, message_type))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

def get_color_by_type(message_type):
    """Obtener color según el tipo de mensaje"""
    colors = {
        'success': (0, 150, 0),    # Verde
        'error': (0, 0, 255),      # Rojo
        'warning': (0, 165, 255),  # Naranja
        'info': (255, 255, 255)    # Blanco
    }
    return colors.get(message_type, (255, 255, 255))

def same_face(loc1, loc2, threshold=50):
    """Compara si dos caras están cerca en píxeles"""
    return abs(loc1[0] - loc2[0]) < threshold and abs(loc1[1] - loc2[1]) < threshold

def determinar_turno_actual():
    """Determina el turno actual basado en la hora"""
    ahora = datetime.now().time()
    hora_actual = ahora.hour + ahora.minute/60
    
    # Turno Mañana: 7:30 - 15:30
    if 7.5 <= hora_actual < 15.5:
        return 'Mañana'
    # Turno Tarde: 15:30 - 23:30
    elif 15.5 <= hora_actual < 23.5:
        return 'Tarde'
    # Turno Noche: 23:30 - 7:30 (del día siguiente)
    else:
        return 'Noche'

def calcular_minutos_tarde(hora_ingreso, turno):
    """Calcula los minutos de tardanza según el turno"""
    ahora = datetime.now()
    hora_ingreso_dt = datetime.combine(ahora.date(), hora_ingreso)
    
    if turno == 'Mañana':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Mañana']['inicio'])
    elif turno == 'Tarde':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Tarde']['inicio'])
    else:  # Noche
        # Para turno noche, si es antes de medianoche usa hoy, sino ayer
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

def registrar_asistencia(employee_id, nombre_completo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener información del empleado
    cursor.execute("SELECT Turno FROM empleados WHERE ID_Empleado = ?", (employee_id,))
    resultado = cursor.fetchone()
    turno_empleado = resultado[0] if resultado else "Mañana"
    
    # Obtener fecha y hora actual (convertidos a string)
    ahora = datetime.now()
    fecha_actual = ahora.date().isoformat()       # YYYY-MM-DD
    hora_actual = ahora.strftime("%H:%M:%S")      # HH:MM:SS
    turno_actual = determinar_turno_actual()
    
    # Verificar si ya existe un registro de ingreso para hoy
    cursor.execute('''
    SELECT ID_Asistencia, Hora_Ingreso, Hora_Egreso 
    FROM asistencias 
    WHERE ID_Empleado = ? AND Fecha = ?
    ''', (employee_id, fecha_actual))
    
    registro = cursor.fetchone()
    
    if registro:
        # Si ya existe un registro pero no tiene hora de egreso
        id_asistencia, hora_ingreso, hora_egreso = registro
        if hora_egreso is None:
            # Registrar egreso
            cursor.execute('''
            UPDATE asistencias 
            SET Hora_Egreso = ?, Estado_Asistencia = FALSE
            WHERE ID_Asistencia = ?
            ''', (ahora.strftime("%H:%M:%S"), id_asistencia))
            add_screen_message(f"Ingreso registrado para {nombre_completo} a las {hora_actual}", 'success')
        else:
            add_screen_message(f"{nombre_completo} ya fue verificado hoy", 'success')
    else:
        # Verificar si el empleado está en el turno correcto
        if turno_empleado != turno_actual:
            add_screen_message(f"Acceso denegado: {nombre_completo} no pertenece al turno {turno_actual}", 'error')
            conn.close()
            return False
        
        # Calcular minutos de tardanza (usamos datetime.time aquí solo para cálculo)
        minutos_tarde = calcular_minutos_tarde(ahora.time(), turno_empleado)
        
        # Verificar si la tardanza es mayor a 120 minutos
        if minutos_tarde > 120:
            add_screen_message(f"Acceso denegado: {nombre_completo} llegó {minutos_tarde} minutos tarde", 'error')
            conn.close()
            return False
        
        # Determinar observación
        observacion = determinar_observacion(minutos_tarde)
        
        # Registrar nuevo ingreso
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, ?, TRUE, ?, ?)
        ''', (fecha_actual, employee_id, turno_empleado, hora_actual, minutos_tarde, observacion))
        
        if observacion == 'Puntual':
            add_screen_message(f"Ingreso registrado para {nombre_completo} a las {hora_actual}", 'success')
        else:
            add_screen_message(f"Ingreso registrado para {nombre_completo} a las {hora_actual}. {observacion}", 'warning')
    
    conn.commit()
    conn.close()
    return True

def draw_messages_on_frame(frame):
    """Dibujar mensajes en el frame"""
    with message_lock:
        # Limpiar mensajes expirados
        while screen_messages and screen_messages[0].is_expired():
            screen_messages.popleft()
        
        # Dibujar mensajes actuales
        y_offset = 30
        for message in screen_messages:
            color = get_color_by_type(message.type)
            
            # Fondo semi-transparente para mejor legibilidad
            text_size = cv2.getTextSize(message.text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(frame, (10, y_offset - 25), (text_size[0] + 20, y_offset + 5), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, y_offset - 25), (text_size[0] + 20, y_offset + 5), color, 2)
            
            # Texto del mensaje
            cv2.putText(frame, message.text, (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            y_offset += 45

# ------------------------------
# HILO DE CAPTURA
# ------------------------------
def capture_thread():
    global current_frame
    try:
        video = cv2.VideoCapture(0)
        if not video.isOpened():
            add_screen_message("Error: No se pudo abrir la cámara", 'error')
            return
            
        video.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
        video.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)
        
        while True:
            ret, frame = video.read()
            if not ret:
                add_screen_message("Error: No se pudo leer el frame de la cámara", 'error')
                break
            with frame_lock:
                current_frame = frame.copy()
    except Exception as e:
        add_screen_message(f"Error en hilo de captura: {e}", 'error')
    finally:
        if 'video' in locals():
            video.release()

# ------------------------------
# HILO DE RECONOCIMIENTO
# ------------------------------
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
                if same_face(face_location, last_loc):
                    match_id = last_id
                    match_name = last_name
                    break

            # Si no estaba, comparar contra base de datos
            if match_id is None:
                results = face_recognition.compare_faces(known_faces, face_encoding, TOLERANCE)
                if True in results:
                    match_index = results.index(True)
                    match_id = employee_ids[match_index]
                    match_name = known_names[match_index]
                    
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

# ------------------------------
# INICIO DE HILOS
# ------------------------------
threading.Thread(target=capture_thread, daemon=True).start()
threading.Thread(target=recognition_thread, daemon=True).start()

# ------------------------------
# BUCLE PRINCIPAL DE VISUALIZACIÓN
# ------------------------------
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
            cv2.rectangle(frame, (left, top), (right, bottom), color, FRAME_THICKNESS)
            if name:
                # Fondo para el nombre
                text_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.7, FONT_THICKNESS)[0]
                cv2.rectangle(frame, (left, top-35), (left + text_size[0] + 10, top), color, -1)
                cv2.putText(frame, name, (left + 5, top-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), FONT_THICKNESS)

        # Dibujar mensajes en pantalla
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
    add_screen_message(f"Error en el bucle principal: {e}", 'error')
    print(f"Error en el bucle principal: {e}")

finally:
    # Este bloque se ejecuta siempre, incluso si hay error
    try:
        cv2.destroyAllWindows()
    except:
        pass  # Ignorar errores al cerrar