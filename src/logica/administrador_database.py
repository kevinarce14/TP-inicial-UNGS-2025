import sqlite3
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
    
    def agregar_empleado(self, nombre, apellido, departamento, turno, foto_path, embedding):
        """Agrega un nuevo empleado a la base de datos"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        # Convertir embedding a bytes
        encoding_blob = embedding.astype(np.float32).tobytes()
        
        cursor.execute('''
        INSERT INTO empleados (Nombre, Apellido, Departamento, Turno, Foto_Path, Embedding)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, departamento, turno, foto_path, encoding_blob))
        
        conexion.commit()
        empleado_id = cursor.lastrowid
        conexion.close()
        
        return empleado_id