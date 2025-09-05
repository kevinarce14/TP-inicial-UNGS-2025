from datetime import time as dt_time

# CONFIGURACIÓN DE RECONOCIMIENTO FACIAL
TOLERANCIA = 0.6
GROSOR_MARCO_CARA = 3
GROSOR_FUENTE_MARCO = 2
MODEL = 'hog'

# CONFIGURACIÓN DE BASE DE DATOS
DB_RUTA = 'database/asistencia_empleados.db'

# CONFIGURACIÓN DE MENSAJES EN PANTALLA
DURACION_MENSAJE = 7 
MAX_CANT_MENSAJES = 5 

# CONFIGURACIÓN DE TURNOS
TURNOS = {
    'Manana': {'inicio': dt_time(7, 30), 'fin': dt_time(15, 30)},
    'Tarde': {'inicio': dt_time(15, 30), 'fin': dt_time(23, 30)},
    'Noche': {'inicio': dt_time(23, 30), 'fin': dt_time(7, 30)}
}

# CONFIGURACIÓN DE CÁMARA
CAMERA_WIDTH = 1024
CAMERA_HEIGHT = 768
FRAME_SCALE = 0.25  # Para acelerar el procesamiento

# DEPARTAMENTOS Y TURNOS VÁLIDOS
DEPARTAMENTOS_VALIDOS = ['Administración', 'Ventas', 'Producción', 'Recursos Humanos']
TURNOS_VALIDOS = ['Manana', 'Tarde', 'Noche']

# LÍMITES DE TARDANZA
MAX_MINUTOS_TARDE = 120  # Máximo permitido para acceso
LIMITE_PUNTUAL = 10      # Hasta 10 min = puntual
LIMITE_MEDIO_TARDE = 30  # 11-30 min = medio tarde

# THREADING
RECOGNITION_SLEEP = 0.05  # Segundos entre procesamiento de frames
REGISTRO_COOLDOWN = 5     # Segundos antes de permitir nuevo procesamiento del mismo empleado


DENEGACION_COOLDOWN = 300  # 5 minutos entre denegaciones del mismo tipo para el mismo empleado