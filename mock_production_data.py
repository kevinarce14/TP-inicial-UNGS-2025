import sqlite3
import random
from datetime import datetime, timedelta
import numpy as np
import os

# Configuración de la base de datos
DB_PATH = 'database/asistencia_empleados.db'

# Productos lácteos
PRODUCTOS_LACTEOS = [
    'Leche Entera',
    'Queso Fresco', 
    'Manteca',
    'Dulce de Leche',
    'Queso Untable',
    'Flan',
    'Yogur'
]

# Nombres y apellidos para generar empleados
NOMBRES = ['Juan', 'Maria', 'Carlos', 'Laura', 'Pedro', 'Ana', 'Luis', 'Elena', 
           'Miguel', 'Sofia', 'Javier', 'Carmen', 'David', 'Isabel', 'Francisco',
           'Rosa', 'Jose', 'Teresa', 'Antonio', 'Patricia', 'Manuel', 'Lucia',
           'Daniel', 'Eva', 'Alejandro', 'Marta', 'Rafael', 'Cristina', 'Pablo', 'Paula']

APELLIDOS = ['Garcia', 'Rodriguez', 'Gonzalez', 'Fernandez', 'Lopez', 'Martinez',
            'Sanchez', 'Perez', 'Gomez', 'Martin', 'Jimenez', 'Ruiz', 'Hernandez',
            'Diaz', 'Moreno', 'Alvarez', 'Romero', 'Alonso', 'Gutierrez', 'Navarro',
            'Torres', 'Dominguez', 'Vazquez', 'Ramos', 'Gil', 'Ramirez', 'Serrano',
            'Blanco', 'Molina', 'Morales', 'Ortega', 'Delgado', 'Castro', 'Ortiz',
            'Rubio', 'Marin', 'Sanz', 'Nunez', 'Iglesias', 'Medina', 'Garrido']

DEPARTAMENTOS = ['Administración', 'Ventas', 'Producción', 'Recursos Humanos']
TURNOS = ['Manana', 'Tarde', 'Noche']

# Horarios de turnos
HORARIOS_TURNOS = {
    'Manana': {'entrada': '07:30:00', 'salida': '15:30:00'},
    'Tarde': {'entrada': '15:30:00', 'salida': '23:30:00'},
    'Noche': {'entrada': '23:30:00', 'salida': '07:30:00'}
}

# Probabilidades de inasistencia por turno (más realistas)
PROBABILIDAD_INASISTENCIA = {
    'Manana': 0.15,  # 15% de inasistencia en turno mañana
    'Tarde': 0.08,   # 8% de inasistencia en turno tarde  
    'Noche': 0.20    # 20% de inasistencia en turno noche
}

def conectar_db():
    """Conecta a la base de datos"""
    return sqlite3.connect(DB_PATH)

def verificar_tabla_produccion():
    """Verifica si la tabla de producción existe"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produccion'")
        resultado = cursor.fetchone()
        conexion.close()
        return resultado is not None
    except:
        conexion.close()
        return False

def verificar_tabla_asistencias():
    """Verifica si la tabla de asistencias existe"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asistencias'")
        resultado = cursor.fetchone()
        conexion.close()
        return resultado is not None
    except:
        conexion.close()
        return False

def obtener_estructura_tabla_produccion():
    """Obtiene la estructura de la tabla de producción"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(produccion)")
        estructura = cursor.fetchall()
        conexion.close()
        return [col[1] for col in estructura]  # Devuelve solo los nombres de las columnas
    except:
        conexion.close()
        return []

def crear_tabla_produccion_simple():
    """Crea una versión simplificada de la tabla de producción"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Primero eliminar la tabla si existe
    cursor.execute('DROP TABLE IF EXISTS produccion')
    
    # Crear tabla simplificada SIN ID_Empleado
    cursor.execute('''
    CREATE TABLE produccion (
        ID_Produccion INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha DATE NOT NULL,
        Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
        Producto TEXT NOT NULL,
        Produccion_Real INTEGER NOT NULL CHECK(Produccion_Real >= 0),
        Produccion_Buena INTEGER NOT NULL CHECK(Produccion_Buena >= 0),
        Produccion_Defectuosa INTEGER NOT NULL CHECK(Produccion_Defectuosa >= 0),
        Tiempo_Planificado INTEGER NOT NULL CHECK(Tiempo_Planificado > 0),
        Tiempo_Paradas INTEGER NOT NULL DEFAULT 0 CHECK(Tiempo_Paradas >= 0),
        Observaciones TEXT,
        Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Updated_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK (Produccion_Buena + Produccion_Defectuosa = Produccion_Real),
        CHECK (Tiempo_Paradas <= Tiempo_Planificado)
    )
    ''')
    
    # Crear índices
    cursor.execute('CREATE INDEX idx_produccion_fecha ON produccion(Fecha)')
    cursor.execute('CREATE INDEX idx_produccion_turno ON produccion(Turno)')
    cursor.execute('CREATE INDEX idx_produccion_producto ON produccion(Producto)')
    
    conexion.commit()
    conexion.close()
    print("Tabla de producción simplificada creada (sin ID_Empleado)")

def modificar_constraint_asistencias():
    """Modifica la constraint de la tabla asistencias para permitir 'Ausente'"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        # Primero hacer backup de la tabla
        cursor.execute('''
        CREATE TABLE asistencias_backup AS 
        SELECT * FROM asistencias
        ''')
        
        # Eliminar la tabla original
        cursor.execute('DROP TABLE asistencias')
        
        # Crear nueva tabla con constraint modificada
        cursor.execute('''
        CREATE TABLE asistencias (
            ID_Asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha DATE NOT NULL,
            ID_Empleado INTEGER NOT NULL,
            Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
            Hora_Ingreso TIME,
            Hora_Egreso TIME,
            Estado_Asistencia BOOLEAN,
            Minutos_Tarde INTEGER,
            Observacion TEXT CHECK(Observacion IN ('Puntual', 'Medio Tarde', 'Muy Tarde', 'Ausente')),
            FOREIGN KEY (ID_Empleado) REFERENCES empleados(ID_Empleado)
        )
        ''')
        
        # Restaurar datos del backup
        cursor.execute('''
        INSERT INTO asistencias 
        SELECT * FROM asistencias_backup
        ''')
        
        # Eliminar backup
        cursor.execute('DROP TABLE asistencias_backup')
        
        # Recrear índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_fecha ON asistencias(Fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_empleado ON asistencias(ID_Empleado)')
        
        conexion.commit()
        conexion.close()
        print("Constraint de tabla asistencias modificada exitosamente")
        return True
        
    except Exception as e:
        print(f"Error al modificar constraint: {e}")
        # En caso de error, restaurar tabla original
        try:
            cursor.execute('DROP TABLE IF EXISTS asistencias')
            cursor.execute('ALTER TABLE asistencias_backup RENAME TO asistencias')
            conexion.commit()
        except:
            pass
        conexion.close()
        return False

def obtener_empleados_existentes():
    """Obtiene la lista de empleados existentes en la base de datos"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT ID_Empleado, Nombre, Apellido, Turno FROM empleados")
        empleados = cursor.fetchall()
        conexion.close()
        
        return [{
            'id': emp[0],
            'nombre': emp[1],
            'apellido': emp[2],
            'nombre_completo': f"{emp[1]} {emp[2]}",
            'turno': emp[3]
        } for emp in empleados]
    except sqlite3.OperationalError:
        conexion.close()
        return []

def crear_empleados_si_faltan():
    """Crea empleados si no hay suficientes (mínimo 20)"""
    empleados_existentes = obtener_empleados_existentes()
    
    if len(empleados_existentes) >= 20:
        print(f"Ya existen {len(empleados_existentes)} empleados en la base de datos")
        return empleados_existentes
    
    print(f"Creando {20 - len(empleados_existentes)} empleados nuevos...")
    
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Crear empleados faltantes
    for i in range(20 - len(empleados_existentes)):
        nombre = random.choice(NOMBRES)
        apellido = random.choice(APELLIDOS)
        departamento = random.choice(DEPARTAMENTOS)
        turno = random.choice(TURNOS)
        
        # Crear un embedding dummy (array de ceros)
        embedding = np.zeros(128, dtype=np.float32)
        embedding_blob = embedding.tobytes()
        
        cursor.execute('''
        INSERT INTO empleados (Nombre, Apellido, Departamento, Turno, Foto_Path, Embedding)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, departamento, turno, f"{nombre.lower()}_{apellido.lower()}.png", embedding_blob))
    
    conexion.commit()
    conexion.close()
    
    print("Empleados creados exitosamente")
    return obtener_empleados_existentes()

def calcular_oee_manual(produccion_real, produccion_buena, tiempo_planificado, tiempo_paradas):
    """Calcula manualmente el OEE y sus componentes"""
    if tiempo_planificado <= 0 or produccion_real <= 0:
        return {
            'oee': 0,
            'disponibilidad': 0,
            'rendimiento': 0,
            'calidad': 0,
            'tiempo_operativo': 0
        }
    
    # Tiempo operativo en minutos
    tiempo_operativo = tiempo_planificado - tiempo_paradas
    
    if tiempo_operativo <= 0:
        return {
            'oee': 0,
            'disponibilidad': 0,
            'rendimiento': 0, 
            'calidad': 0,
            'tiempo_operativo': 0
        }
    
    # Cálculos de componentes OEE
    disponibilidad = (tiempo_operativo / tiempo_planificado) * 100
    
    # Tasa ideal de producción: 100 unidades/hora
    TASA_IDEAL = 100
    tiempo_operativo_horas = tiempo_operativo / 60.0
    produccion_teorica = tiempo_operativo_horas * TASA_IDEAL
    rendimiento = (produccion_real / produccion_teorica) * 100 if produccion_teorica > 0 else 0
    
    calidad = (produccion_buena / produccion_real) * 100
    
    # OEE total
    oee = (disponibilidad / 100) * (rendimiento / 100) * (calidad / 100) * 100
    
    return {
        'oee': round(oee, 2),
        'disponibilidad': round(disponibilidad, 2),
        'rendimiento': round(rendimiento, 2),
        'calidad': round(calidad, 2),
        'tiempo_operativo': tiempo_operativo
    }

def generar_datos_turno_manana():
    """Genera datos para turno mañana: bajo rendimiento por ausencias"""
    # Alta tasa de paradas (ausencias)
    tiempo_planificado = 480  # 8 horas
    tiempo_paradas = random.randint(120, 180)  # 2-3 horas de paradas
    
    # Baja producción
    produccion_real = random.randint(300, 500)
    defectuosa = random.randint(40, 80)  # Mayor defectuosa
    produccion_buena = produccion_real - defectuosa
    
    return {
        'tiempo_planificado': tiempo_planificado,
        'tiempo_paradas': tiempo_paradas,
        'produccion_real': produccion_real,
        'produccion_buena': produccion_buena,
        'produccion_defectuosa': defectuosa
    }

def generar_datos_turno_tarde():
    """Genera datos para turno tarde: buen rendimiento"""
    # Pocas paradas
    tiempo_planificado = 480  # 8 horas
    tiempo_paradas = random.randint(30, 60)  # 0.5-1 hora de paradas
    
    # Buena producción con alta calidad
    produccion_real = random.randint(600, 800)
    defectuosa = random.randint(10, 30)  # Poca defectuosa
    produccion_buena = produccion_real - defectuosa
    
    return {
        'tiempo_planificado': tiempo_planificado,
        'tiempo_paradas': tiempo_paradas,
        'produccion_real': produccion_real,
        'produccion_buena': produccion_buena,
        'produccion_defectuosa': defectuosa
    }

def generar_datos_turno_noche():
    """Genera datos para turno noche: bajo rendimiento por llegadas tarde"""
    # Paradas moderadas (llegadas tarde)
    tiempo_planificado = 480  # 8 horas
    tiempo_paradas = random.randint(60, 120)  # 1-2 horas de paradas
    
    # Producción moderada con calidad variable
    produccion_real = random.randint(400, 600)
    defectuosa = random.randint(30, 60)  # Defectuosa moderada
    produccion_buena = produccion_real - defectuosa
    
    return {
        'tiempo_planificado': tiempo_planificado,
        'tiempo_paradas': tiempo_paradas,
        'produccion_real': produccion_real,
        'produccion_buena': produccion_buena,
        'produccion_defectuosa': defectuosa
    }

def insertar_registro_produccion(fecha, turno, producto, datos_produccion):
    """Inserta un registro de producción en la base de datos (SIN ID_Empleado)"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Primero verificar la estructura de la tabla
    columnas = obtener_estructura_tabla_produccion()
    
    if 'ID_Empleado' in columnas:
        # Si la tabla tiene ID_Empleado, usar la versión con empleado
        cursor.execute('''
        INSERT INTO produccion (
            Fecha, Turno, ID_Empleado, Producto,
            Produccion_Real, Produccion_Buena, Produccion_Defectuosa,
            Tiempo_Planificado, Tiempo_Paradas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fecha, turno, random.randint(1, 20), producto,  # Empleado aleatorio
            datos_produccion['produccion_real'],
            datos_produccion['produccion_buena'],
            datos_produccion['produccion_defectuosa'],
            datos_produccion['tiempo_planificado'],
            datos_produccion['tiempo_paradas']
        ))
    else:
        # Si la tabla NO tiene ID_Empleado, usar la versión sin empleado
        cursor.execute('''
        INSERT INTO produccion (
            Fecha, Turno, Producto,
            Produccion_Real, Produccion_Buena, Produccion_Defectuosa,
            Tiempo_Planificado, Tiempo_Paradas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fecha, turno, producto,
            datos_produccion['produccion_real'],
            datos_produccion['produccion_buena'],
            datos_produccion['produccion_defectuosa'],
            datos_produccion['tiempo_planificado'],
            datos_produccion['tiempo_paradas']
        ))
    
    conexion.commit()
    conexion.close()

def insertar_registro_asistencia(fecha, id_empleado, turno, minutos_tarde=None):
    """Inserta un registro de asistencia en la base de datos con hora de egreso"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Obtener horarios del turno
    hora_entrada = HORARIOS_TURNOS[turno]['entrada']
    hora_salida = HORARIOS_TURNOS[turno]['salida']
    
    # Simular llegadas tarde según el turno
    if minutos_tarde is None:
        if turno == 'Manana':
            minutos_tarde = random.randint(15, 45)  # Mañana: más tardanzas
        elif turno == 'Tarde':
            minutos_tarde = random.randint(5, 20)   # Tarde: pocas tardanzas
        else:  # Noche
            minutos_tarde = random.randint(10, 30)  # Noche: tardanzas moderadas
    
    # Calcular hora de entrada real (con tardanza)
    if minutos_tarde > 0:
        hora_entrada_real = sumar_minutos_a_hora(hora_entrada, minutos_tarde)
    else:
        hora_entrada_real = hora_entrada
    
    # Determinar observación basada en minutos de tardanza
    if minutos_tarde <= 10:
        observacion = 'Puntual'
    elif minutos_tarde <= 30:
        observacion = 'Medio Tarde'
    else:
        observacion = 'Muy Tarde'
    
    # Verificar si ya existe un registro para este empleado en esta fecha
    cursor.execute('''
    SELECT ID_Asistencia FROM asistencias 
    WHERE Fecha = ? AND ID_Empleado = ?
    ''', (fecha, id_empleado))
    
    existe_registro = cursor.fetchone()
    
    if existe_registro:
        # Actualizar registro existente con hora de egreso
        cursor.execute('''
        UPDATE asistencias 
        SET Hora_Ingreso = ?, Hora_Egreso = ?, Minutos_Tarde = ?, Observacion = ?, Estado_Asistencia = TRUE
        WHERE Fecha = ? AND ID_Empleado = ?
        ''', (hora_entrada_real, hora_salida, minutos_tarde, observacion, fecha, id_empleado))
    else:
        # Insertar nuevo registro con hora de egreso
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, ?, ?, TRUE, ?, ?)
        ''', (fecha, id_empleado, turno, hora_entrada_real, hora_salida, minutos_tarde, observacion))
    
    conexion.commit()
    conexion.close()

def insertar_inasistencia(fecha, id_empleado, turno):
    """Inserta un registro de inasistencia en la base de datos"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Verificar si ya existe un registro para este empleado en esta fecha
    cursor.execute('''
    SELECT ID_Asistencia FROM asistencias 
    WHERE Fecha = ? AND ID_Empleado = ?
    ''', (fecha, id_empleado))
    
    existe_registro = cursor.fetchone()
    
    if existe_registro:
        # Actualizar registro existente como inasistencia
        cursor.execute('''
        UPDATE asistencias 
        SET Hora_Ingreso = NULL, Hora_Egreso = NULL, Minutos_Tarde = NULL, 
            Observacion = 'Muy Tarde', Estado_Asistencia = FALSE
        WHERE Fecha = ? AND ID_Empleado = ?
        ''', (fecha, id_empleado))
    else:
        # Insertar nuevo registro de inasistencia
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, NULL, NULL, FALSE, NULL, 'Muy Tarde')
        ''', (fecha, id_empleado, turno))
    
    conexion.commit()
    conexion.close()

def sumar_minutos_a_hora(hora_str, minutos):
    """Suma minutos a una hora en formato HH:MM:SS"""
    from datetime import datetime, timedelta
    
    hora = datetime.strptime(hora_str, '%H:%M:%S')
    nueva_hora = hora + timedelta(minutes=minutos)
    return nueva_hora.strftime('%H:%M:%S')

def generar_datos_30_dias(empleados):
    """Genera datos de producción and asistencia para los últimos 30 días"""
    fecha_fin = datetime.now().date()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    print(f"Generando datos desde {fecha_inicio} hasta {fecha_fin}...")
    
    total_registros_produccion = 0
    total_registros_asistencia = 0
    total_inasistencias = 0
    
    for i in range(30):
        fecha_actual = fecha_inicio + timedelta(days=i)
        fecha_str = fecha_actual.isoformat()
        
        # No generar datos para fines de semana (sábado=5, domingo=6)
        if fecha_actual.weekday() >= 5:
            continue
        
        # Para cada empleado, generar asistencia o inasistencia
        for empleado in empleados:
            turno = empleado['turno']
            probabilidad_ausencia = PROBABILIDAD_INASISTENCIA[turno]
            
            if random.random() < probabilidad_ausencia:
                # Inasistencia
                insertar_inasistencia(fecha_str, empleado['id'], turno)
                total_inasistencias += 1
            else:
                # Asistencia normal
                insertar_registro_asistencia(fecha_str, empleado['id'], turno)
                total_registros_asistencia += 1
        
        # Generar 3-6 registros de producción por día
        if fecha_actual.weekday() in [0, 4]:  # Lunes y viernes
            registros_dia = random.randint(4, 6)
        else:
            registros_dia = random.randint(3, 5)
        
        for _ in range(registros_dia):
            # Seleccionar turno aleatorio
            turno = random.choice(TURNOS)
            producto = random.choice(PRODUCTOS_LACTEOS)
            
            # Generar datos según el turno
            if turno == 'Manana':
                datos = generar_datos_turno_manana()
            elif turno == 'Tarde':
                datos = generar_datos_turno_tarde()
            else:  # Noche
                datos = generar_datos_turno_noche()
            
            # Insertar registro de producción
            insertar_registro_produccion(
                fecha_str,
                turno,
                producto,
                datos
            )
            
            total_registros_produccion += 1
    
    print(f"Datos generados exitosamente!")
    print(f"  - {total_registros_asistencia} registros de asistencia creados")
    print(f"  - {total_inasistencias} inasistencias registradas")
    print(f"  - {total_registros_produccion} registros de producción creados")

def calcular_oee_desde_datos(produccion_real, produccion_buena, tiempo_planificado, tiempo_paradas):
    """Calcula OEE a partir de los datos (para estadísticas)"""
    if tiempo_planificado <= 0 or produccion_real <= 0:
        return 0
    
    tiempo_operativo = tiempo_planificado - tiempo_paradas
    if tiempo_operativo <= 0:
        return 0
    
    disponibilidad = (tiempo_operativo / tiempo_planificado) * 100
    TASA_IDEAL = 100
    tiempo_operativo_horas = tiempo_operativo / 60.0
    produccion_teorica = tiempo_operativo_horas * TASA_IDEAL
    rendimiento = (produccion_real / produccion_teorica) * 100 if produccion_teorica > 0 else 0
    calidad = (produccion_buena / produccion_real) * 100
    
    oee = (disponibilidad / 100) * (rendimiento / 100) * (calidad / 100) * 100
    return round(oee, 2)

def mostrar_estadisticas():
    """Muestra estadísticas de los datos generados"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # Estadísticas de producción
    print("\n=== ESTADÍSTICAS DE PRODUCCIÓN ===")
    
    # Obtener todos los registros de producción para calcular estadísticas
    cursor.execute('''
    SELECT Produccion_Real, Produccion_Buena, Produccion_Defectuosa, 
           Tiempo_Planificado, Tiempo_Paradas, Turno 
    FROM produccion
    ''')
    
    registros = cursor.fetchall()
    
    # Calcular estadísticas por turno
    estadisticas_turno = {
        'Manana': {'total': 0, 'oee_sum': 0, 'prod_total': 0, 'buena_total': 0, 'def_total': 0},
        'Tarde': {'total': 0, 'oee_sum': 0, 'prod_total': 0, 'buena_total': 0, 'def_total': 0},
        'Noche': {'total': 0, 'oee_sum': 0, 'prod_total': 0, 'buena_total': 0, 'def_total': 0}
    }
    
    for prod_real, prod_buena, prod_def, tiempo_plan, tiempo_par, turno in registros:
        oee = calcular_oee_desde_datos(prod_real, prod_buena, tiempo_plan, tiempo_par)
        
        if turno in estadisticas_turno:
            estadisticas_turno[turno]['total'] += 1
            estadisticas_turno[turno]['oee_sum'] += oee
            estadisticas_turno[turno]['prod_total'] += prod_real
            estadisticas_turno[turno]['buena_total'] += prod_buena
            estadisticas_turno[turno]['def_total'] += prod_def
    
    for turno, stats in estadisticas_turno.items():
        if stats['total'] > 0:
            oee_promedio = stats['oee_sum'] / stats['total']
            print(f"\nTurno: {turno}")
            print(f"  Registros: {stats['total']}")
            print(f"  OEE Promedio: {oee_promedio:.2f}%")
            print(f"  Producción Total: {stats['prod_total']} unidades")
            print(f"  Buenas: {stats['buena_total']} unidades")
            print(f"  Defectuosas: {stats['def_total']} unidades")
    
    # OEE general de producción
    oee_total = sum(stats['oee_sum'] for stats in estadisticas_turno.values())
    total_registros = sum(stats['total'] for stats in estadisticas_turno.values())
    oee_general = oee_total / total_registros if total_registros > 0 else 0
    print(f"\nOEE General Producción: {oee_general:.2f}%")
    
    # Estadísticas de asistencia
    print("\n=== ESTADÍSTICAS DE ASISTENCIA ===")
    
    cursor.execute('''
    SELECT Turno, 
           COUNT(*) as Total_Registros,
           SUM(CASE WHEN Estado_Asistencia = TRUE THEN 1 ELSE 0 END) as Asistencias,
           SUM(CASE WHEN Estado_Asistencia = FALSE THEN 1 ELSE 0 END) as Inasistencias,
           AVG(CASE WHEN Estado_Asistencia = TRUE THEN Minutos_Tarde ELSE NULL END) as Tardanza_Promedio,
           SUM(CASE WHEN Minutos_Tarde <= 10 AND Estado_Asistencia = TRUE THEN 1 ELSE 0 END) as Puntuales,
           SUM(CASE WHEN Minutos_Tarde > 10 AND Minutos_Tarde <= 30 AND Estado_Asistencia = TRUE THEN 1 ELSE 0 END) as Medio_Tarde,
           SUM(CASE WHEN Minutos_Tarde > 30 AND Estado_Asistencia = TRUE THEN 1 ELSE 0 END) as Muy_Tarde
    FROM asistencias 
    GROUP BY Turno
    ''')
    
    stats_asistencia = cursor.fetchall()
    
    for turno, total, asistencias, inasistencias, tardanza_prom, puntuales, medio_tarde, muy_tarde in stats_asistencia:
        if asistencias > 0:
            print(f"\nTurno: {turno}")
            print(f"  Total registros: {total}")
            print(f"  Asistencias: {asistencias} ({asistencias/total*100:.1f}%)")
            print(f"  Inasistencias: {inasistencias} ({inasistencias/total*100:.1f}%)")
            print(f"  Tardanza promedio: {tardanza_prom:.1f} minutos")
            print(f"  Puntuales: {puntuales} ({puntuales/asistencias*100:.1f}% de asistencias)")
            print(f"  Medio tarde: {medio_tarde} ({medio_tarde/asistencias*100:.1f}% de asistencias)")
            print(f"  Muy tarde: {muy_tarde} ({muy_tarde/asistencias*100:.1f}% de asistencias)")
    
    # Mostrar algunos registros de ejemplo
    cursor.execute('''
    SELECT a.Fecha, e.Nombre, e.Apellido, a.Turno, a.Hora_Ingreso, a.Hora_Egreso, 
           a.Minutos_Tarde, a.Estado_Asistencia, a.Observacion
    FROM asistencias a
    JOIN empleados e ON a.ID_Empleado = e.ID_Empleado
    ORDER BY a.Fecha DESC, a.Estado_Asistencia DESC
    LIMIT 10
    ''')
    
    ejemplos = cursor.fetchall()
    print("\n=== EJEMPLOS DE REGISTROS DE ASISTENCIA ===")
    for fecha, nombre, apellido, turno, ingreso, egreso, tardanza, estado, observacion in ejemplos:
        if estado:  # Asistencia
            print(f"{fecha}: {nombre} {apellido} ({turno}) - Entrada: {ingreso}, Salida: {egreso}, Tardanza: {tardanza} min - {observacion}")
        else:  # Inasistencia
            print(f"{fecha}: {nombre} {apellido} ({turno}) - AUSENTE - {observacion}")
    
    conexion.close()

def limpiar_datos_existentes():
    """Elimina todos los datos existentes de producción y asistencia"""
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM produccion')
    cursor.execute('DELETE FROM asistencias')
    conexion.commit()
    conexion.close()
    print("Datos existentes de producción y asistencia eliminados.")

def main():
    """Función principal"""
    print("=== GENERADOR DE DATOS DE PRODUCCIÓN Y ASISTENCIA PARA LÁCTEOS ===")
    
    # Verificar si la base de datos existe
    if not os.path.exists(DB_PATH):
        print(f"Error: La base de datos {DB_PATH} no existe.")
        print("Ejecuta primero el sistema principal para crear la base de datos.")
        return
    
    # Verificar estructura de la tabla de producción
    columnas_produccion = obtener_estructura_tabla_produccion()
    print(f"Estructura de tabla producción: {columnas_produccion}")
    
    # Verificar y crear tabla de producción si es necesario
    if not verificar_tabla_produccion():
        print("Creando tabla de producción simplificada...")
        crear_tabla_produccion_simple()
    
    # Verificar si existe tabla de asistencias
    if not verificar_tabla_asistencias():
        print("Error: La tabla de asistencias no existe.")
        print("Ejecuta primero el sistema principal para crear todas las tablas.")
        return
    
    # Intentar modificar la constraint de la tabla asistencias
    print("Intentando modificar constraint de tabla asistencias...")
    if not modificar_constraint_asistencias():
        print("Usando 'Muy Tarde' para inasistencias (fallback)")
    
    # Obtener o crear empleados
    empleados = crear_empleados_si_faltan()
    
    print(f"\nEmpleados disponibles: {len(empleados)}")
    for i, emp in enumerate(empleados[:5], 1):  # Mostrar primeros 5
        print(f"  {i}. {emp['nombre_completo']} - {emp['turno']}")
    if len(empleados) > 5:
        print(f"  ... y {len(empleados) - 5} más")
    
    # Preguntar al usuario
    print("\n¿Qué deseas hacer?")
    print("1. Generar nuevos datos (30 días)")
    print("2. Mostrar estadísticas actuales")
    print("3. Limpiar datos existentes")
    print("4. Salir")
    
    opcion = input("\nSelecciona una opción (1-4): ").strip()
    
    if opcion == '1':
        # Limpiar datos existentes (opcional)
        limpiar = input("¿Limpiar datos existentes antes de generar? (s/n): ").lower().strip()
        if limpiar == 's':
            limpiar_datos_existentes()
        
        # Generar nuevos datos
        generar_datos_30_dias(empleados)
        mostrar_estadisticas()
        
    elif opcion == '2':
        mostrar_estadisticas()
    
    elif opcion == '3':
        confirmar = input("¿Estás seguro de eliminar todos los datos de producción y asistencia? (s/n): ").lower().strip()
        if confirmar == 's':
            limpiar_datos_existentes()
        else:
            print("Operación cancelada.")
    
    elif opcion == '4':
        print("Saliendo...")
        return
    
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()