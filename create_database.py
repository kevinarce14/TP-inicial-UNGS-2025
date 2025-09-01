import sqlite3
import os

def create_database():
    # Conectar a la base de datos (se creará si no existe)
    conn = sqlite3.connect('asistencia_empleados.db')
    cursor = conn.cursor()
    
    # Crear tabla de empleados
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS empleados (
        ID_Empleado INTEGER PRIMARY KEY AUTOINCREMENT,
        Nombre TEXT NOT NULL,
        Apellido TEXT NOT NULL,
        Departamento TEXT CHECK(Departamento IN ('Administración', 'Ventas', 'Producción', 'Recursos Humanos')),
        Turno TEXT CHECK(Turno IN ('Mañana', 'Tarde', 'Noche')),
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
        Turno TEXT CHECK(Turno IN ('Mañana', 'Tarde', 'Noche')),
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
    
    conn.commit()
    conn.close()
    print("Base de datos creada exitosamente!")

if __name__ == "__main__":
    create_database()