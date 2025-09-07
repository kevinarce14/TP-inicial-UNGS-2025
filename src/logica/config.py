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


DENEGACION_COOLDOWN = 5  


# CONFIGURACIÓN DE PRODUCCIÓN
TASA_IDEAL_PRODUCCION = 100  # unidades por hora (base para cálculo de rendimiento)
PRODUCTOS_DISPONIBLES = [
    'Producto A',
    'Producto B', 
    'Producto C',
    'Producto D'
]

# LÍMITES OEE (Overall Equipment Effectiveness)
OEE_EXCELENTE = 85      # >= 85% se considera excelente
OEE_BUENO = 70          # >= 70% se considera bueno  
OEE_REGULAR = 50        # >= 50% se considera regular
                        # < 50% se considera deficiente

# CONFIGURACIÓN DE REPORTES
DIAS_REPORTE_DEFAULT = 30       # Días por defecto para reportes
MAX_REGISTROS_CONSULTA = 1000   # Máximo registros por consulta
FORMATO_FECHA_REPORTE = '%Y-%m-%d'
FORMATO_HORA_REPORTE = '%H:%M:%S'

# COLORES PARA INDICADORES OEE (RGB)
COLOR_OEE_EXCELENTE = (0, 255, 0)      # Verde
COLOR_OEE_BUENO = (255, 255, 0)        # Amarillo  
COLOR_OEE_REGULAR = (255, 165, 0)      # Naranja
COLOR_OEE_DEFICIENTE = (255, 0, 0)     # Rojo

# CONFIGURACIÓN DE VALIDACIONES PRODUCCIÓN
MIN_TIEMPO_PLANIFICADO = 60     # Mínimo 1 hora planificada
MAX_TIEMPO_PLANIFICADO = 960    # Máximo 16 horas planificadas
MAX_PRODUCCION_POR_REGISTRO = 10000  # Máximo unidades por registro