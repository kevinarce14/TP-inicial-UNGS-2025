import sqlite3
import face_recognition
import numpy as np
import os
from datetime import datetime, date, timedelta
from .config import DB_RUTA

class DatabaseManager:
    def __init__(self, db_path=DB_RUTA):
        self.db_path = db_path
    
    def verificar_tablas(self):
        """Verifica y crea las tablas si no existen"""
        if not os.path.exists(self.db_path):
            print("La base de datos no existe. Creándola...")
            self._crear_database()
        else:
            conexion = sqlite3.connect(self.db_path)
            cursor = conexion.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM empleados")
                conexion.close()
            except sqlite3.OperationalError:
                print("Las tablas no existen. Creándolas...")
                conexion.close()
                self._crear_database()
    
    def _crear_database(self):
        """Crea la base de datos con las tablas necesarias"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        # Crear tabla de empleados
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            ID_Empleado INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            Apellido TEXT NOT NULL,
            Departamento TEXT CHECK(Departamento IN ('Administración', 'Ventas', 'Producción', 'Recursos Humanos')),
            Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
            Foto_Path TEXT,
            Embedding BLOB NOT NULL
        )
        ''')
        
        # Crear tabla de asistencias
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            ID_Asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha DATE NOT NULL,
            ID_Empleado INTEGER NOT NULL,
            Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
            Hora_Ingreso TIME,
            Hora_Egreso TIME,
            Estado_Asistencia BOOLEAN,
            Minutos_Tarde INTEGER,
            Observacion TEXT CHECK(Observacion IN ('Puntual', 'Medio Tarde', 'Muy Tarde')),
            FOREIGN KEY (ID_Empleado) REFERENCES empleados(ID_Empleado)
        )
        ''')
        
        # Crear índices para mejorar el rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_fecha ON asistencias(Fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_empleado ON asistencias(ID_Empleado)')
        
        conexion.commit()
        conexion.close()
        print("Base de datos creada exitosamente!")
    
    def cargar_embeddings(self):
        """Carga todos los embeddings de empleados desde la base de datos"""
        conexion = sqlite3.connect(self.db_path)
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
            nombre_completo = f"{nombre} {apellido}"
            empleados_nombres.append(nombre_completo)
            empleados_ids.append(empleado_id)
        
        conexion.close()
        return empleados_caras, empleados_nombres, empleados_ids
    
    def obtener_empleado(self, empleado_id):
        """Obtiene información de un empleado por su ID"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT ID_Empleado, Nombre, Apellido, Departamento, Turno, Foto_Path
            FROM empleados 
            WHERE ID_Empleado = ?
        """, (empleado_id,))
        
        resultado = cursor.fetchone()
        conexion.close()
        
        if resultado:
            return {
                'id': resultado[0],
                'nombre': resultado[1],
                'apellido': resultado[2],
                'nombre_completo': f"{resultado[1]} {resultado[2]}",
                'departamento': resultado[3],
                'turno': resultado[4],
                'foto_path': resultado[5]
            }
        return None
    
    def verificar_asistencia_hoy(self, empleado_id):
        """Verifica si el empleado ya registró asistencia hoy"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        fecha_actual = datetime.now().date().isoformat()
        
        cursor.execute('''
        SELECT ID_Asistencia, Hora_Ingreso, Hora_Egreso 
        FROM asistencias 
        WHERE ID_Empleado = ? AND Fecha = ?
        ''', (empleado_id, fecha_actual))
        
        registro = cursor.fetchone()
        conexion.close()
        
        if registro:
            return {
                'id_asistencia': registro[0],
                'hora_ingreso': registro[1],
                'hora_egreso': registro[2],
                'tiene_ingreso': registro[1] is not None,
                'tiene_egreso': registro[2] is not None
            }
        return None
    
    def registrar_ingreso(self, empleado_id, turno, hora_actual, minutos_tarde, observacion):
        """Registra el ingreso de un empleado"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        fecha_actual = datetime.now().date().isoformat()
        
        cursor.execute('''
        INSERT INTO asistencias 
        (Fecha, ID_Empleado, Turno, Hora_Ingreso, Estado_Asistencia, Minutos_Tarde, Observacion)
        VALUES (?, ?, ?, ?, TRUE, ?, ?)
        ''', (fecha_actual, empleado_id, turno, hora_actual, minutos_tarde, observacion))
        
        conexion.commit()
        conexion.close()
        return cursor.lastrowid
    
    def registrar_egreso(self, empleado_id, hora_actual):
        """Registra el egreso de un empleado"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        fecha_actual = datetime.now().date().isoformat()
        
        cursor.execute('''
        UPDATE asistencias 
        SET Hora_Egreso = ?
        WHERE ID_Empleado = ? AND Fecha = ? AND Hora_Egreso IS NULL
        ''', (hora_actual, empleado_id, fecha_actual))
        
        conexion.commit()
        rows_affected = cursor.rowcount
        conexion.close()
        
        return rows_affected > 0
    
    def crear_tabla_denegaciones(self):
        """Crea la tabla de denegaciones si no existe"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS denegaciones (
            id_denegacion INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            id_empleado INTEGER NULL,
            motivo TEXT NOT NULL CHECK(motivo IN (
                'llegada_tarde',
                'turno_no_corresponde', 
                'persona_no_registrada',
                'sin_ingreso_previo'
            )),
            modo_operacion TEXT NOT NULL CHECK(modo_operacion IN ('ingreso', 'egreso')),
            minutos_tarde INTEGER NULL,
            turno_esperado TEXT NULL,
            turno_detectado TEXT NULL,
            nombre_detectado TEXT NULL,
            observaciones TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_empleado) REFERENCES empleados(ID_Empleado)
        )
        ''')
    
        # Crear índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_denegaciones_fecha ON denegaciones(fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_denegaciones_empleado ON denegaciones(id_empleado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_denegaciones_motivo ON denegaciones(motivo)')
    
        conexion.commit()
        conexion.close()

    def registrar_denegacion(self, motivo, modo_operacion, id_empleado=None, 
                            minutos_tarde=None, turno_esperado=None, turno_detectado=None,
                            nombre_detectado=None, observaciones=None):
        """Registra una denegación de acceso"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
    
        ahora = datetime.now()
        fecha_actual = ahora.date().isoformat()
        hora_actual = ahora.strftime("%H:%M:%S")
    
        cursor.execute('''
        INSERT INTO denegaciones 
        (fecha, hora, id_empleado, motivo, modo_operacion, minutos_tarde, 
        turno_esperado, turno_detectado, nombre_detectado, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha_actual, hora_actual, id_empleado, motivo, modo_operacion,
            minutos_tarde, turno_esperado, turno_detectado, nombre_detectado, observaciones))
    
        conexion.commit()
        denegacion_id = cursor.lastrowid
        conexion.close()
    
        return denegacion_id

    def obtener_denegaciones_por_empleado(self, id_empleado, fecha_inicio=None, fecha_fin=None):
        """Obtiene las denegaciones de un empleado en un rango de fechas"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
    
        query = "SELECT * FROM denegaciones WHERE id_empleado = ?"
        params = [id_empleado]
    
        if fecha_inicio:
            query += " AND fecha >= ?"
            params.append(fecha_inicio)
    
        if fecha_fin:
            query += " AND fecha <= ?"
            params.append(fecha_fin)
        
        query += " ORDER BY fecha DESC, hora DESC"
    
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conexion.close()
    
        return resultados

    def obtener_estadisticas_denegaciones(self, fecha_inicio=None, fecha_fin=None):
        """Obtiene estadísticas de denegaciones"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
    
        query_base = "SELECT motivo, COUNT(*) as cantidad FROM denegaciones"
        params = []
    
        if fecha_inicio or fecha_fin:
            query_base += " WHERE"
            conditions = []
        
            if fecha_inicio:
                conditions.append(" fecha >= ?")
                params.append(fecha_inicio)
            if fecha_fin:
                conditions.append(" fecha <= ?")
                params.append(fecha_fin)
            
            query_base += " AND".join(conditions)
    
        query_base += " GROUP BY motivo ORDER BY cantidad DESC"
    
        cursor.execute(query_base, params)
        resultados = cursor.fetchall()
        conexion.close()
    
        return resultados
    
    
    def agregar_empleado(self, nombre, apellido, departamento, turno, foto_path):
        # Validar departamento
        departamentos_validos = ['Administración', 'Ventas', 'Producción', 'Recursos Humanos']
        if departamento not in departamentos_validos:
            print(f"Departamento inválido. Debe ser uno de: {', '.join(departamentos_validos)}")
            return False
    
        # Validar turno
        turnos_validos = ['Manana', 'Tarde', 'Noche']
        if turno not in turnos_validos:
            print(f"Turno inválido. Debe ser uno de: {', '.join(turnos_validos)}")
            return False
    
        # Verificar que el archivo existe
        if not os.path.exists(foto_path):
            print(f"El archivo {foto_path} no existe")
            return False
    
        # Cargar y codificar la imagen
        image = face_recognition.load_image_file(foto_path)
        encodings = face_recognition.face_encodings(image)
    
        if not encodings:
            print(f"No se pudo detectar un rostro en {foto_path}")
            return False
    
        # Guardar como float32 para evitar errores de dimensión
        encoding_blob = encodings[0].astype(np.float32).tobytes()
    
        # Conectar a la base de datos y guardar
        # POR ESTA:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        cursor.execute('''
        INSERT INTO empleados (Nombre, Apellido, Departamento, Turno, Foto_Path, Embedding)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, departamento, turno, foto_path, encoding_blob))
    
        conn.commit()
        conn.close()
    
        print(f"Empleado {nombre} {apellido} agregado exitosamente!")
        return True