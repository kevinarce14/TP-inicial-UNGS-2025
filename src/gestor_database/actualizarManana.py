#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para modificar la restricción CHECK y actualizar turnos
Guarda como: corregir_restriccion_turnos.py
Ejecuta con: python corregir_restriccion_turnos.py
"""

import sqlite3
import os

# Ruta a tu base de datos
DB_RUTA = 'database/asistencia_empleados.db'

def corregir_restriccion_y_datos():
    """Modifica la restricción CHECK y actualiza los datos"""
    try:
        print("Conectando a la base de datos...")
        conexion = sqlite3.connect(DB_RUTA)
        cursor = conexion.cursor()
        
        # Verificar datos actuales
        print("\nDatos actuales:")
        cursor.execute("SELECT DISTINCT Turno FROM empleados")
        turnos_actuales = [row[0] for row in cursor.fetchall()]
        print(f"Turnos en empleados: {turnos_actuales}")
        
        # PASO 1: Crear tablas temporales sin restricciones CHECK
        print("\nPaso 1: Creando tablas temporales...")
        
        # Tabla empleados temporal
        cursor.execute('''
        CREATE TABLE empleados_temp (
            ID_Empleado INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            Apellido TEXT NOT NULL,
            Departamento TEXT,
            Turno TEXT,
            Foto_Path TEXT,
            Embedding BLOB NOT NULL
        )
        ''')
        
        # Tabla asistencias temporal
        cursor.execute('''
        CREATE TABLE asistencias_temp (
            ID_Asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha DATE NOT NULL,
            ID_Empleado INTEGER NOT NULL,
            Turno TEXT,
            Hora_Ingreso TIME,
            Hora_Egreso TIME,
            Estado_Asistencia BOOLEAN,
            Minutos_Tarde INTEGER,
            Observacion TEXT,
            FOREIGN KEY (ID_Empleado) REFERENCES empleados_temp(ID_Empleado)
        )
        ''')
        
        # PASO 2: Copiar datos a tablas temporales con turnos corregidos
        print("Paso 2: Copiando y corrigiendo datos...")
        
        cursor.execute('''
        INSERT INTO empleados_temp 
        SELECT ID_Empleado, Nombre, Apellido, Departamento, 
               CASE 
                   WHEN Turno IN ('Mañana', 'MaÃ±ana') THEN 'Manana'
                   ELSE Turno 
               END,
               Foto_Path, Embedding
        FROM empleados
        ''')
        
        cursor.execute('''
        INSERT INTO asistencias_temp 
        SELECT ID_Asistencia, Fecha, ID_Empleado,
               CASE 
                   WHEN Turno IN ('Mañana', 'MaÃ±ana') THEN 'Manana'
                   ELSE Turno 
               END,
               Hora_Ingreso, Hora_Egreso, Estado_Asistencia, 
               Minutos_Tarde, Observacion
        FROM asistencias
        ''')
        
        # PASO 3: Eliminar tablas originales
        print("Paso 3: Eliminando tablas originales...")
        cursor.execute('DROP TABLE empleados')
        cursor.execute('DROP TABLE asistencias')
        
        # PASO 4: Crear tablas definitivas con restricciones CHECK corregidas
        print("Paso 4: Creando tablas definitivas con restricciones corregidas...")
        
        cursor.execute('''
        CREATE TABLE empleados (
            ID_Empleado INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            Apellido TEXT NOT NULL,
            Departamento TEXT CHECK(Departamento IN ('Administración', 'Ventas', 'Producción', 'Recursos Humanos')),
            Turno TEXT CHECK(Turno IN ('Manana', 'Tarde', 'Noche')),
            Foto_Path TEXT,
            Embedding BLOB NOT NULL
        )
        ''')
        
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
            Observacion TEXT CHECK(Observacion IN ('Puntual', 'Medio Tarde', 'Muy Tarde')),
            FOREIGN KEY (ID_Empleado) REFERENCES empleados(ID_Empleado)
        )
        ''')
        
        # PASO 5: Copiar datos de tablas temporales a definitivas
        print("Paso 5: Copiando datos a tablas definitivas...")
        
        cursor.execute('''
        INSERT INTO empleados 
        SELECT * FROM empleados_temp
        ''')
        
        cursor.execute('''
        INSERT INTO asistencias 
        SELECT * FROM asistencias_temp
        ''')
        
        # PASO 6: Eliminar tablas temporales
        print("Paso 6: Limpiando tablas temporales...")
        cursor.execute('DROP TABLE empleados_temp')
        cursor.execute('DROP TABLE asistencias_temp')
        
        # PASO 7: Recrear índices
        print("Paso 7: Recreando índices...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_fecha ON asistencias(Fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asistencias_empleado ON asistencias(ID_Empleado)')
        
        # Confirmar cambios
        conexion.commit()
        
        # Verificar resultados
        print("\nVerificando resultados:")
        cursor.execute("SELECT DISTINCT Turno FROM empleados")
        nuevos_turnos = [row[0] for row in cursor.fetchall()]
        print(f"Turnos actualizados: {nuevos_turnos}")
        
        cursor.execute("SELECT Nombre, Apellido, Turno FROM empleados WHERE Turno = 'Manana'")
        empleados_manana = cursor.fetchall()
        print(f"\nEmpleados del turno Manana ({len(empleados_manana)}):")
        for emp in empleados_manana:
            print(f"  - {emp[0]} {emp[1]}")
        
        conexion.close()
        print("\nB Corrección completada exitosamente!")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conexion' in locals():
            conexion.rollback()
            conexion.close()

if __name__ == "__main__":
    print("=" * 60)
    print("CORRECCION DE RESTRICCIONES CHECK Y DATOS DE TURNOS")
    print("=" * 60)
    print("Este script:")
    print("1. Modifica las restricciones CHECK para permitir 'Manana' sin tilde")
    print("2. Actualiza todos los datos existentes")
    print("3. Mantiene la integridad de la base de datos")
    
    if not os.path.exists(DB_RUTA):
        print(f"\nError: No se encuentra la base de datos en {DB_RUTA}")
        exit(1)
    
    respuesta = input("\n¿Continuar con la corrección? (s/N): ").strip().lower()
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        # Hacer backup de la base de datos
        import shutil
        backup_path = DB_RUTA + '.backup'
        print(f"\nCreando backup en: {backup_path}")
        shutil.copy2(DB_RUTA, backup_path)
        
        corregir_restriccion_y_datos()
        print(f"\nNota: Se creó un backup de tu base de datos en: {backup_path}")
    else:
        print("Operación cancelada")