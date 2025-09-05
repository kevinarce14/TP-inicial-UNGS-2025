# src/logica/production_manager.py

import sqlite3
from datetime import datetime, date
from .administrador_database import DatabaseManager
from .config import DB_RUTA

class ProductionManager:
    def __init__(self, db_path=DB_RUTA):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self._crear_tabla_produccion()
    
    def _crear_tabla_produccion(self):
        """Crea la tabla de producción si no existe"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS produccion (
            ID_Produccion INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha DATE NOT NULL,
            Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
            ID_Empleado INTEGER NOT NULL,
            Producto TEXT NOT NULL,
            Produccion_Real INTEGER NOT NULL CHECK(Produccion_Real >= 0),
            Produccion_Buena INTEGER NOT NULL CHECK(Produccion_Buena >= 0),
            Produccion_Defectuosa INTEGER NOT NULL CHECK(Produccion_Defectuosa >= 0),
            Tiempo_Planificado INTEGER NOT NULL CHECK(Tiempo_Planificado > 0), -- en minutos
            Tiempo_Paradas INTEGER NOT NULL DEFAULT 0 CHECK(Tiempo_Paradas >= 0), -- en minutos
            OEE REAL GENERATED ALWAYS AS (
                CASE 
                    WHEN Tiempo_Planificado > 0 AND Produccion_Real > 0 
                    THEN (
                        -- Disponibilidad
                        (CAST(Tiempo_Planificado - Tiempo_Paradas AS REAL) / Tiempo_Planificado) *
                        -- Rendimiento (asumiendo 100 unidades/hora como tasa ideal)
                        (CAST(Produccion_Real AS REAL) / 
                         ((CAST(Tiempo_Planificado - Tiempo_Paradas AS REAL) / 60.0) * 100)) *
                        -- Calidad  
                        (CAST(Produccion_Buena AS REAL) / Produccion_Real)
                    ) * 100
                    ELSE 0 
                END
            ) STORED,
            Tiempo_Operativo REAL GENERATED ALWAYS AS (
                CAST(Tiempo_Planificado - Tiempo_Paradas AS REAL)
            ) STORED,
            Disponibilidad REAL GENERATED ALWAYS AS (
                CASE 
                    WHEN Tiempo_Planificado > 0 
                    THEN (CAST(Tiempo_Planificado - Tiempo_Paradas AS REAL) / Tiempo_Planificado) * 100
                    ELSE 0 
                END
            ) STORED,
            Rendimiento REAL GENERATED ALWAYS AS (
                CASE 
                    WHEN Tiempo_Planificado > Tiempo_Paradas AND Produccion_Real > 0
                    THEN (CAST(Produccion_Real AS REAL) / 
                          ((CAST(Tiempo_Planificado - Tiempo_Paradas AS REAL) / 60.0) * 100)) * 100
                    ELSE 0 
                END
            ) STORED,
            Calidad REAL GENERATED ALWAYS AS (
                CASE 
                    WHEN Produccion_Real > 0 
                    THEN (CAST(Produccion_Buena AS REAL) / Produccion_Real) * 100
                    ELSE 0 
                END
            ) STORED,
            Observaciones TEXT,
            Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Updated_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            FOREIGN KEY (ID_Empleado) REFERENCES empleados(ID_Empleado),
            CHECK (Produccion_Buena + Produccion_Defectuosa = Produccion_Real),
            CHECK (Tiempo_Paradas <= Tiempo_Planificado)
        )
        ''')
        
        # Crear índices para mejorar rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produccion_fecha ON produccion(Fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produccion_empleado ON produccion(ID_Empleado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produccion_turno ON produccion(Turno)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produccion_producto ON produccion(Producto)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produccion_oee ON produccion(OEE)')
        
        # Trigger para actualizar Updated_At
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_produccion_timestamp
        AFTER UPDATE ON produccion
        BEGIN
            UPDATE produccion SET Updated_At = CURRENT_TIMESTAMP WHERE ID_Produccion = NEW.ID_Produccion;
        END
        ''')
        
        conexion.commit()
        conexion.close()
        print("Tabla de producción creada exitosamente!")
    
    def registrar_produccion(self, fecha, turno, id_empleado, producto, 
                           produccion_real, produccion_buena, produccion_defectuosa,
                           tiempo_planificado, tiempo_paradas=0, observaciones=None):
        """
        Registra un nuevo registro de producción
        
        Args:
            fecha (str): Fecha en formato YYYY-MM-DD
            turno (str): 'Manana', 'Tarde', 'Noche'
            id_empleado (int): ID del empleado
            producto (str): Tipo de producto
            produccion_real (int): Total de unidades producidas
            produccion_buena (int): Unidades buenas
            produccion_defectuosa (int): Unidades defectuosas  
            tiempo_planificado (int): Tiempo planificado en minutos
            tiempo_paradas (int): Tiempo de paradas en minutos
            observaciones (str): Observaciones adicionales
        """
        
        # Validaciones
        if produccion_buena + produccion_defectuosa != produccion_real:
            raise ValueError("La suma de producción buena y defectuosa debe igual a producción real")
        
        if tiempo_paradas > tiempo_planificado:
            raise ValueError("El tiempo de paradas no puede ser mayor al tiempo planificado")
        
        # Verificar que el empleado existe
        empleado = self.db_manager.obtener_empleado(id_empleado)
        if not empleado:
            raise ValueError(f"Empleado con ID {id_empleado} no encontrado")
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute('''
        INSERT INTO produccion (
            Fecha, Turno, ID_Empleado, Producto,
            Produccion_Real, Produccion_Buena, Produccion_Defectuosa,
            Tiempo_Planificado, Tiempo_Paradas, Observaciones
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, turno, id_empleado, producto, produccion_real, 
              produccion_buena, produccion_defectuosa, tiempo_planificado, 
              tiempo_paradas, observaciones))
        
        conexion.commit()
        produccion_id = cursor.lastrowid
        conexion.close()
        
        return produccion_id
    
    def obtener_produccion_por_fecha(self, fecha_inicio, fecha_fin=None):
        """Obtiene registros de producción por rango de fechas"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        if fecha_fin is None:
            fecha_fin = fecha_inicio
        
        cursor.execute('''
        SELECT p.*, e.Nombre, e.Apellido 
        FROM produccion p
        JOIN empleados e ON p.ID_Empleado = e.ID_Empleado
        WHERE p.Fecha BETWEEN ? AND ?
        ORDER BY p.Fecha DESC, p.Turno
        ''', (fecha_inicio, fecha_fin))
        
        resultados = cursor.fetchall()
        conexion.close()
        
        return resultados
    
    def obtener_produccion_por_empleado(self, id_empleado, fecha_inicio=None, fecha_fin=None):
        """Obtiene producción de un empleado específico"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        if fecha_inicio and fecha_fin:
            cursor.execute('''
            SELECT * FROM produccion 
            WHERE ID_Empleado = ? AND Fecha BETWEEN ? AND ?
            ORDER BY Fecha DESC
            ''', (id_empleado, fecha_inicio, fecha_fin))
        else:
            cursor.execute('''
            SELECT * FROM produccion 
            WHERE ID_Empleado = ?
            ORDER BY Fecha DESC LIMIT 50
            ''', (id_empleado,))
        
        resultados = cursor.fetchall()
        conexion.close()
        
        return resultados
    
    def calcular_oee_promedio(self, fecha_inicio, fecha_fin, turno=None, empleado=None, producto=None):
        """Calcula el OEE promedio según filtros"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        query = '''
        SELECT 
            AVG(OEE) as OEE_Promedio,
            AVG(Disponibilidad) as Disponibilidad_Promedio,
            AVG(Rendimiento) as Rendimiento_Promedio,
            AVG(Calidad) as Calidad_Promedio,
            COUNT(*) as Total_Registros,
            SUM(Produccion_Real) as Total_Produccion,
            SUM(Produccion_Buena) as Total_Buena,
            SUM(Produccion_Defectuosa) as Total_Defectuosa
        FROM produccion 
        WHERE Fecha BETWEEN ? AND ?
        '''
        params = [fecha_inicio, fecha_fin]
        
        if turno:
            query += ' AND Turno = ?'
            params.append(turno)
        
        if empleado:
            query += ' AND ID_Empleado = ?'
            params.append(empleado)
            
        if producto:
            query += ' AND Producto = ?'
            params.append(producto)
        
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        conexion.close()
        
        return {
            'oee_promedio': round(resultado[0] or 0, 2),
            'disponibilidad_promedio': round(resultado[1] or 0, 2),
            'rendimiento_promedio': round(resultado[2] or 0, 2),
            'calidad_promedio': round(resultado[3] or 0, 2),
            'total_registros': resultado[4] or 0,
            'total_produccion': resultado[5] or 0,
            'total_buena': resultado[6] or 0,
            'total_defectuosa': resultado[7] or 0
        }
    
    def obtener_productos_disponibles(self):
        """Obtiene lista de productos únicos"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute('SELECT DISTINCT Producto FROM produccion ORDER BY Producto')
        productos = [row[0] for row in cursor.fetchall()]
        
        conexion.close()
        return productos
    
    def obtener_ranking_empleados_oee(self, fecha_inicio, fecha_fin, limit=10):
        """Obtiene ranking de empleados por OEE"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute('''
        SELECT 
            p.ID_Empleado,
            e.Nombre,
            e.Apellido,
            AVG(p.OEE) as OEE_Promedio,
            COUNT(*) as Total_Registros,
            SUM(p.Produccion_Real) as Total_Produccion
        FROM produccion p
        JOIN empleados e ON p.ID_Empleado = e.ID_Empleado
        WHERE p.Fecha BETWEEN ? AND ?
        GROUP BY p.ID_Empleado, e.Nombre, e.Apellido
        ORDER BY OEE_Promedio DESC
        LIMIT ?
        ''', (fecha_inicio, fecha_fin, limit))
        
        resultados = cursor.fetchall()
        conexion.close()
        
        return resultados
    
    def actualizar_produccion(self, id_produccion, **campos):
        """Actualiza campos específicos de un registro de producción"""
        campos_permitidos = [
            'Fecha', 'Turno', 'Producto', 'Produccion_Real', 'Produccion_Buena',
            'Produccion_Defectuosa', 'Tiempo_Planificado', 'Tiempo_Paradas', 'Observaciones'
        ]
        
        campos_a_actualizar = {k: v for k, v in campos.items() if k in campos_permitidos}
        
        if not campos_a_actualizar:
            raise ValueError("No se proporcionaron campos válidos para actualizar")
        
        # Validar que producción buena + defectuosa = real si se actualizan estos campos
        if any(campo in campos_a_actualizar for campo in ['Produccion_Real', 'Produccion_Buena', 'Produccion_Defectuosa']):
            # Obtener valores actuales
            actual = self.obtener_produccion_por_id(id_produccion)
            if actual:
                real = campos_a_actualizar.get('Produccion_Real', actual['Produccion_Real'])
                buena = campos_a_actualizar.get('Produccion_Buena', actual['Produccion_Buena'])
                defectuosa = campos_a_actualizar.get('Produccion_Defectuosa', actual['Produccion_Defectuosa'])
                
                if buena + defectuosa != real:
                    raise ValueError("La suma de producción buena y defectuosa debe igual a producción real")
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        set_clause = ', '.join([f"{campo} = ?" for campo in campos_a_actualizar.keys()])
        valores = list(campos_a_actualizar.values()) + [id_produccion]
        
        cursor.execute(f'''
        UPDATE produccion 
        SET {set_clause}
        WHERE ID_Produccion = ?
        ''', valores)
        
        conexion.commit()
        filas_afectadas = cursor.rowcount
        conexion.close()
        
        return filas_afectadas > 0
    
    def obtener_produccion_por_id(self, id_produccion):
        """Obtiene un registro de producción por su ID"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        cursor.execute('''
        SELECT p.*, e.Nombre, e.Apellido
        FROM produccion p
        JOIN empleados e ON p.ID_Empleado = e.ID_Empleado  
        WHERE p.ID_Produccion = ?
        ''', (id_produccion,))
        
        resultado = cursor.fetchone()
        conexion.close()
        
        if resultado:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, resultado))
        
        return None