
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
TOLERANCIA = 0.6
GROSOR_MARCO = 3
GROSOR_FUENTE = 2
MODELO = 'hog'  # 'hog' en CPU, 'cnn' con GPU CUDA
RUTA_BD = 'asistencia_empleados.db'

# Configuración de mensajes en pantalla
DURACION_MENSAJE = 5  # segundos que se muestra cada mensaje
MAXIMO_MENSAJES = 5   # máximo número de mensajes en pantalla

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
    if not os.path.exists(RUTA_BD):
        print("La base de datos no existe. Creándola...")
        try:
            from create_database import create_database
            create_database()
        except ImportError:
            print("ERROR: No se pudo importar create_database")
    else:
        # Verificar si la tabla empleados existe
        conexion = sqlite3.connect(RUTA_BD)
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM empleados")
            conexion.close()
        except sqlite3.OperationalError:
            print("Las tablas no existen. Creándolas...")
            conexion.close()
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
def cargar_caras_conocidas_desde_bd():
    """Carga los rostros conocidos desde la base de datos"""
    conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()
    
    cursor.execute("SELECT ID_Empleado, Nombre, Apellido, Embedding FROM empleados")
    filas = cursor.fetchall()
    
    caras_conocidas = []
    nombres_conocidos = []
    ids_empleados = []
    
    for fila in filas:
        id_empleado, nombre, apellido, embedding_blob = fila
        # Convertir el BLOB a numpy array (CORRECCIÓN: usar float32)
        embedding = np.frombuffer(embedding_blob, dtype=np.float32)
        caras_conocidas.append(embedding)
        nombre_completo = f"{nombre} {apellido}"
        nombres_conocidos.append(nombre_completo)
        ids_empleados.append(id_empleado)
    
    conexion.close()
    return caras_conocidas, nombres_conocidos, ids_empleados

print("Cargando imágenes conocidas desde la base de datos...")
caras_conocidas, nombres_conocidos, ids_empleados = cargar_caras_conocidas_desde_bd()

print("Listo! Iniciando cámara...")

# ------------------------------
# VARIABLES COMPARTIDAS ENTRE HILOS
# ------------------------------
bloqueo_frame = threading.Lock()
bloqueo_mensaje = threading.Lock()
frame_actual = None
resultados_actuales = []

# Para reutilizar encodings previos
ultimas_coincidencias = []  # [(id_empleado, nombre, (top,right,bottom,left)), ...]

# Cola de mensajes para mostrar en pantalla
mensajes_pantalla = deque(maxlen=MAXIMO_MENSAJES)

class MensajePantalla:
    def __init__(self, texto, tipo_mensaje='info'):
        self.texto = texto
        self.marca_tiempo = time.time()
        self.tipo = tipo_mensaje  # 'success', 'error', 'warning', 'info'
        
    def esta_expirado(self):
        return time.time() - self.marca_tiempo > DURACION_MENSAJE

def agregar_mensaje_pantalla(texto, tipo_mensaje='info'):
    """Agregar mensaje a la cola de mensajes en pantalla"""
    with bloqueo_mensaje:
        mensajes_pantalla.append(MensajePantalla(texto, tipo_mensaje))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {texto}")

def obtener_color_por_tipo(tipo_mensaje):
    """Obtener color según el tipo de mensaje"""
    colores = {
        'success': (0, 150, 0),    # Verde
        'error': (0, 0, 255),      # Rojo
        'warning': (0, 165, 255),  # Naranja
        'info': (255, 255, 255)    # Blanco
    }
    return colores.get(tipo_mensaje, (255, 255, 255))

def misma_cara(ubicacion1, ubicacion2, umbral=50):
    """Compara si dos caras están cerca en píxeles"""
    return abs(ubicacion1[0] - ubicacion2[0]) < umbral and abs(ubicacion1[1] - ubicacion2[1]) < umbral

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

def registrar_asistencia(id_empleado, nombre_completo):
    conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()
    
    # Obtener información del empleado
    cursor.execute("SELECT Turno FROM empleados WHERE ID_Empleado = ?", (id_empleado,))
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
    ''', (id_empleado, fecha_actual))
    
    registro = cursor.fetchone()
    
    if registro:
        # Si ya existe un registro pero no tiene hora de egreso
        id_asistencia, hora_ingreso, hora_egreso = registro
        if hora_egreso is None:
            agregar_mensaje_pantalla(f"{nombre_completo} ya fue verificado hoy", 'success')
    else:
        # Verificar si el empleado está en el turno correcto
        if turno_empleado != turno_actual:
            agregar_mensaje_pantalla(f"Acceso denegado: {nombre_completo} no pertenece al turno {turno_actual}", 'error')
            conexion.close()
            return False
        
        # Calcular minutos de tardanza (usamos datetime.time aquí solo para cálculo)
        minutos_tarde = calcular_minutos_tarde(ahora.time(), turno_empleado)
        
        # Verificar si la tardanza es mayor a 120 minutos
        if minutos_tarde > 120:
            agregar_mensaje_pantalla(f"Acceso denegado: {nombre_completo} llegó {minutos_tarde} minutos tarde", 'error')
            conexion.close()
            return False
        
        # Determinar observación
        observacion = determinar_observacion(minutos_tarde)
        
        # Registrar nuevo ingreso
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, ?, TRUE, ?, ?)
        ''', (fecha_actual, id_empleado, turno_empleado, hora_actual, minutos_tarde, observacion))
        
        if observacion == 'Puntual':
            agregar_mensaje_pantalla(f"Ingreso registrado para {nombre_completo} a las {hora_actual}", 'success')
        else:
            agregar_mensaje_pantalla(f"Ingreso registrado para {nombre_completo} a las {hora_actual}. {observacion}", 'warning')
    
    conexion.commit()
    conexion.close()
    return True

def dibujar_mensajes_en_frame(frame):
    """Dibujar mensajes en el frame"""
    with bloqueo_mensaje:
        # Limpiar mensajes expirados
        while mensajes_pantalla and mensajes_pantalla[0].esta_expirado():
            mensajes_pantalla.popleft()
        
        # Dibujar mensajes actuales
        desplazamiento_y = 30
        for mensaje in mensajes_pantalla:
            color = obtener_color_por_tipo(mensaje.tipo)
            
            # Fondo semi-transparente para mejor legibilidad
            tamano_texto = cv2.getTextSize(mensaje.texto, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(frame, (10, desplazamiento_y - 25), (tamano_texto[0] + 20, desplazamiento_y + 5), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, desplazamiento_y - 25), (tamano_texto[0] + 20, desplazamiento_y + 5), color, 2)
            
            # Texto del mensaje
            cv2.putText(frame, mensaje.texto, (15, desplazamiento_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            desplazamiento_y += 45

# ------------------------------
# HILO DE CAPTURA
# ------------------------------
def hilo_captura():
    global frame_actual
    try:
        video = cv2.VideoCapture(1)
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
            with bloqueo_frame:
                frame_actual = frame.copy()
    except Exception as e:
        agregar_mensaje_pantalla(f"Error en hilo de captura: {e}", 'error')
    finally:
        if 'video' in locals():
            video.release()

# ------------------------------
# HILO DE RECONOCIMIENTO
# ------------------------------
def hilo_reconocimiento():
    global frame_actual, resultados_actuales, ultimas_coincidencias
    # Para evitar registrar múltiples veces la misma asistencia
    ultimo_registro = {}
    
    while True:
        time.sleep(0.05)  # evita uso 100% CPU

        with bloqueo_frame:
            if frame_actual is None:
                continue
            frame = frame_actual.copy()

        # Redimensionar para acelerar
        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Detectar ubicaciones
        ubicaciones_caras = face_recognition.face_locations(frame_pequeno, model=MODELO)
        encodings_caras = face_recognition.face_encodings(frame_pequeno, ubicaciones_caras)

        # Escalar ubicaciones al tamaño original
        ubicaciones_caras = [(t*4, r*4, b*4, l*4) for (t, r, b, l) in ubicaciones_caras]

        coincidencias_actuales = []

        for encoding_cara, ubicacion_cara in zip(encodings_caras, ubicaciones_caras):
            id_coincidencia = None
            nombre_coincidencia = None

            # Reutilizar coincidencia anterior si la cara está cerca
            for ultimo_id, ultimo_nombre, ultima_ubicacion in ultimas_coincidencias:
                if misma_cara(ubicacion_cara, ultima_ubicacion):
                    id_coincidencia = ultimo_id
                    nombre_coincidencia = ultimo_nombre
                    break

            # Si no estaba, comparar contra base de datos
            if id_coincidencia is None:
                resultados = face_recognition.compare_faces(caras_conocidas, encoding_cara, TOLERANCIA)
                if True in resultados:
                    indice_coincidencia = resultados.index(True)
                    id_coincidencia = ids_empleados[indice_coincidencia]
                    nombre_coincidencia = nombres_conocidos[indice_coincidencia]
                    
                    # Registrar asistencia (solo una vez cada 30 segundos por persona)
                    ahora = time.time()
                    if id_coincidencia not in ultimo_registro or ahora - ultimo_registro[id_coincidencia] > 30:
                        registrar_asistencia(id_coincidencia, nombre_coincidencia)
                        ultimo_registro[id_coincidencia] = ahora

            coincidencias_actuales.append((id_coincidencia, nombre_coincidencia, ubicacion_cara))

        # Actualizar variables compartidas
        with bloqueo_frame:
            resultados_actuales = coincidencias_actuales
            ultimas_coincidencias = coincidencias_actuales.copy()

# ------------------------------
# INICIO DE HILOS
# ------------------------------
threading.Thread(target=hilo_captura, daemon=True).start()
threading.Thread(target=hilo_reconocimiento, daemon=True).start()

# ------------------------------
# BUCLE PRINCIPAL DE VISUALIZACIÓN
# ------------------------------
try:
    while True:
        with bloqueo_frame:
            if frame_actual is None:
                time.sleep(0.1)
                continue
            frame = frame_actual.copy()
            resultados = resultados_actuales.copy()

        # Dibujar resultados de reconocimiento facial
        for id_empleado, nombre, (arriba, derecha, abajo, izquierda) in resultados:
            color = (0, 255, 0) if id_empleado else (0, 0, 255)
            cv2.rectangle(frame, (izquierda, arriba), (derecha, abajo), color, GROSOR_MARCO)
            if nombre:
                # Fondo para el nombre
                tamano_texto = cv2.getTextSize(nombre, cv2.FONT_HERSHEY_SIMPLEX, 0.7, GROSOR_FUENTE)[0]
                cv2.rectangle(frame, (izquierda, arriba-35), (izquierda + tamano_texto[0] + 10, arriba), color, -1)
                cv2.putText(frame, nombre, (izquierda + 5, arriba-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), GROSOR_FUENTE)

        # Dibujar mensajes en pantalla
        dibujar_mensajes_en_frame(frame)

        # Mostrar hora actual en esquina superior derecha
        hora_actual = datetime.now().strftime("%H:%M:%S")
        turno_actual = determinar_turno_actual()
        texto_info = f"{hora_actual} - Turno: {turno_actual}"
        tamano_texto = cv2.getTextSize(texto_info, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        ancho_frame = frame.shape[1]
        
        cv2.rectangle(frame, (ancho_frame - tamano_texto[0] - 15, 5), 
                     (ancho_frame - 5, 35), (0, 0, 0), -1)
        cv2.putText(frame, texto_info, (ancho_frame - tamano_texto[0] - 10, 25),
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