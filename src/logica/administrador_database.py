import psycopg2
import face_recognition
import numpy as np
import os
from datetime import datetime, date, timedelta
from .config import DB_CONFIG
import io

class DatabaseManager:
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def _get_connection(self):
        """Establece conexión con PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"Error conectando a PostgreSQL: {e}")
            raise
    
    def verificar_tablas(self):
        """Verifica y crea las tablas si no existen"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            # Verificar si existe la tabla empleados
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'empleados'
                );
            """)
            tabla_existe = cursor.fetchone()[0]
            
            if not tabla_existe:
                print("Las tablas no existen. Creándolas...")
                self._crear_database()
            else:
                print("Las tablas ya existen.")
                
        except Exception as e:
            print(f"Error verificando tablas: {e}")
            conexion.rollback()
        finally:
            cursor.close()
            conexion.close()
    
    def _crear_database(self):
        """Crea la base de datos con las tablas necesarias"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            # Crear tabla de empleados
            cursor.execute('''
            CREATE TABLE empleados (
                ID_Empleado SERIAL PRIMARY KEY,
                Nombre TEXT NOT NULL,
                Apellido TEXT NOT NULL,
                Departamento TEXT CHECK(Departamento IN ('Administración', 'Ventas', 'Producción', 'Recursos Humanos')),
                Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
                Foto_Path TEXT,
                Embedding BYTEA NOT NULL
            )
            ''')
            
            # Crear tabla de asistencias
            cursor.execute('''
            CREATE TABLE asistencias (
                ID_Asistencia SERIAL PRIMARY KEY,
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
            cursor.execute('CREATE INDEX idx_asistencias_fecha ON asistencias(Fecha)')
            cursor.execute('CREATE INDEX idx_asistencias_empleado ON asistencias(ID_Empleado)')
            
            conexion.commit()
            print("Base de datos creada exitosamente!")
            
        except Exception as e:
            print(f"Error creando tablas: {e}")
            conexion.rollback()
        finally:
            cursor.close()
            conexion.close()
    
    def cargar_embeddings(self):
        """Carga todos los embeddings de empleados desde la base de datos"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            cursor.execute("SELECT ID_Empleado, Nombre, Apellido, Embedding FROM empleados")
            filas = cursor.fetchall()
            
            empleados_caras = []
            empleados_nombres = []
            empleados_ids = []
            
            for fila in filas:
                empleado_id, nombre, apellido, embedding_blob = fila
                # Convertir bytes de PostgreSQL a numpy array
                embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                empleados_caras.append(embedding)
                nombre_completo = f"{nombre} {apellido}"
                empleados_nombres.append(nombre_completo)
                empleados_ids.append(empleado_id)
            
            return empleados_caras, empleados_nombres, empleados_ids
            
        except Exception as e:
            print(f"Error cargando embeddings: {e}")
            return [], [], []
        finally:
            cursor.close()
            conexion.close()
    
    def obtener_empleado(self, empleado_id):
        """Obtiene información de un empleado por su ID"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            cursor.execute("""
                SELECT ID_Empleado, Nombre, Apellido, Departamento, Turno, Foto_Path
                FROM empleados 
                WHERE ID_Empleado = %s
            """, (empleado_id,))
            
            resultado = cursor.fetchone()
            
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
            
        except Exception as e:
            print(f"Error obteniendo empleado: {e}")
            return None
        finally:
            cursor.close()
            conexion.close()
    
    def verificar_asistencia_hoy(self, empleado_id):
        """Verifica si el empleado ya registró asistencia hoy"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            fecha_actual = datetime.now().date().isoformat()
            
            cursor.execute('''
            SELECT ID_Asistencia, Hora_Ingreso, Hora_Egreso 
            FROM asistencias 
            WHERE ID_Empleado = %s AND Fecha = %s
            ''', (empleado_id, fecha_actual))
            
            registro = cursor.fetchone()
            
            if registro:
                return {
                    'id_asistencia': registro[0],
                    'hora_ingreso': registro[1],
                    'hora_egreso': registro[2],
                    'tiene_ingreso': registro[1] is not None,
                    'tiene_egreso': registro[2] is not None
                }
            return None
            
        except Exception as e:
            print(f"Error verificando asistencia: {e}")
            return None
        finally:
            cursor.close()
            conexion.close()
    
    def registrar_ingreso(self, empleado_id, turno, hora_actual, minutos_tarde, observacion):
        """Registra el ingreso de un empleado"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            fecha_actual = datetime.now().date().isoformat()
            
            cursor.execute('''
            INSERT INTO asistencias 
            (Fecha, ID_Empleado, Turno, Hora_Ingreso, Estado_Asistencia, Minutos_Tarde, Observacion)
            VALUES (%s, %s, %s, %s, TRUE, %s, %s)
            RETURNING ID_Asistencia
            ''', (fecha_actual, empleado_id, turno, hora_actual, minutos_tarde, observacion))
            
            id_asistencia = cursor.fetchone()[0]
            conexion.commit()
            return id_asistencia
            
        except Exception as e:
            print(f"Error registrando ingreso: {e}")
            conexion.rollback()
            return None
        finally:
            cursor.close()
            conexion.close()
    
    def registrar_egreso(self, empleado_id, hora_actual):
        """Registra el egreso de un empleado"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            fecha_actual = datetime.now().date().isoformat()
            
            cursor.execute('''
            UPDATE asistencias 
            SET Hora_Egreso = %s
            WHERE ID_Empleado = %s AND Fecha = %s AND Hora_Egreso IS NULL
            ''', (hora_actual, empleado_id, fecha_actual))
            
            conexion.commit()
            rows_affected = cursor.rowcount
            
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error registrando egreso: {e}")
            conexion.rollback()
            return False
        finally:
            cursor.close()
            conexion.close()
    
    def crear_tabla_denegaciones(self):
        """Crea la tabla de denegaciones si no existe"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS denegaciones (
                id_denegacion SERIAL PRIMARY KEY,
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
            
        except Exception as e:
            print(f"Error creando tabla denegaciones: {e}")
            conexion.rollback()
        finally:
            cursor.close()
            conexion.close()

    def registrar_denegacion(self, motivo, modo_operacion, id_empleado=None, 
                            minutos_tarde=None, turno_esperado=None, turno_detectado=None,
                            nombre_detectado=None, observaciones=None):
        """Registra una denegación de acceso"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            ahora = datetime.now()
            fecha_actual = ahora.date().isoformat()
            hora_actual = ahora.strftime("%H:%M:%S")
            
            cursor.execute('''
            INSERT INTO denegaciones 
            (fecha, hora, id_empleado, motivo, modo_operacion, minutos_tarde, 
            turno_esperado, turno_detectado, nombre_detectado, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_denegacion
            ''', (fecha_actual, hora_actual, id_empleado, motivo, modo_operacion,
                minutos_tarde, turno_esperado, turno_detectado, nombre_detectado, observaciones))
            
            denegacion_id = cursor.fetchone()[0]
            conexion.commit()
            
            return denegacion_id
            
        except Exception as e:
            print(f"Error registrando denegación: {e}")
            conexion.rollback()
            return None
        finally:
            cursor.close()
            conexion.close()

    def obtener_denegaciones_por_empleado(self, id_empleado, fecha_inicio=None, fecha_fin=None):
        """Obtiene las denegaciones de un empleado en un rango de fechas"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            query = "SELECT * FROM denegaciones WHERE id_empleado = %s"
            params = [id_empleado]
            
            if fecha_inicio:
                query += " AND fecha >= %s"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query += " AND fecha <= %s"
                params.append(fecha_fin)
            
            query += " ORDER BY fecha DESC, hora DESC"
            
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            
            return resultados
            
        except Exception as e:
            print(f"Error obteniendo denegaciones: {e}")
            return []
        finally:
            cursor.close()
            conexion.close()

    def obtener_estadisticas_denegaciones(self, fecha_inicio=None, fecha_fin=None):
        """Obtiene estadísticas de denegaciones"""
        conexion = self._get_connection()
        cursor = conexion.cursor()
        
        try:
            query_base = "SELECT motivo, COUNT(*) as cantidad FROM denegaciones"
            params = []
            
            if fecha_inicio or fecha_fin:
                query_base += " WHERE"
                conditions = []
                
                if fecha_inicio:
                    conditions.append(" fecha >= %s")
                    params.append(fecha_inicio)
                if fecha_fin:
                    conditions.append(" fecha <= %s")
                    params.append(fecha_fin)
                
                query_base += " AND".join(conditions)
            
            query_base += " GROUP BY motivo ORDER BY cantidad DESC"
            
            cursor.execute(query_base, params)
            resultados = cursor.fetchall()
            
            return resultados
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return []
        finally:
            cursor.close()
            conexion.close()
    
    def agregar_empleado(self, nombre, apellido, departamento, turno, foto_path):
        print(f"=== DATABASEMANAGER - AGREGANDO EMPLEADO ===")
        print(f"Nombre: {nombre}, Apellido: {apellido}")
        print(f"Departamento: {departamento}, Turno: {turno}")
        print(f"Foto path: {foto_path}")
        
        # Validar departamento
        departamentos_validos = ['Administración', 'Ventas', 'Producción', 'Recursos Humanos']
        if departamento not in departamentos_validos:
            print(f"❌ Departamento inválido: {departamento}")
            return False
        
        # Validar turno
        turnos_validos = ['Manana', 'Tarde', 'Noche']
        if turno not in turnos_validos:
            print(f"❌ Turno inválido: {turno}")
            return False
        
        # Verificar que el archivo existe
        if not os.path.exists(foto_path):
            print(f"❌ El archivo no existe: {foto_path}")
            return False
        
        print(f"✅ Archivo encontrado: {foto_path}")
        
        # Cargar y codificar la imagen
        try:
            print("🔄 Cargando y codificando imagen...")
            image = face_recognition.load_image_file(foto_path)
            encodings = face_recognition.face_encodings(image)
            
            if not encodings:
                print(f"❌ No se pudo detectar un rostro en {foto_path}")
                return False
            
            print("✅ Rostro detectado y codificado correctamente")
            encoding_blob = encodings[0].astype(np.float32).tobytes()
            
        except Exception as e:
            print(f"❌ Error procesando imagen: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Conectar a la base de datos y guardar
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Insertando en base de datos...")
            cursor.execute('''
            INSERT INTO empleados (nombre, apellido, departamento, turno, foto_path, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_empleado
            ''', (nombre, apellido, departamento, turno, foto_path, psycopg2.Binary(encoding_blob)))
            
            empleado_id = cursor.fetchone()[0]
            conn.commit()
            
            print(f"✅ Empleado {nombre} {apellido} agregado exitosamente! ID: {empleado_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error en base de datos: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()