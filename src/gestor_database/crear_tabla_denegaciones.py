#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la tabla de denegaciones
Guarda como: crear_tabla_denegaciones.py
Ejecuta con: python crear_tabla_denegaciones.py
"""

import sqlite3
import os
import sys

# Agregar src al path si es necesario
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.logica.config import DB_RUTA
except ImportError:
    DB_RUTA = 'database/asistencia_empleados.db'

def crear_tabla_denegaciones():
    """Crea la tabla de denegaciones y sus índices"""
    try:
        print("Conectando a la base de datos...")
        conexion = sqlite3.connect(DB_RUTA)
        cursor = conexion.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='denegaciones'")
        if cursor.fetchone():
            print("La tabla 'denegaciones' ya existe.")
            respuesta = input("¿Deseas recrearla? (s/N): ").strip().lower()
            if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Operación cancelada")
                return
            cursor.execute("DROP TABLE denegaciones")
            print("Tabla existente eliminada.")
        
        print("Creando tabla 'denegaciones'...")
        cursor.execute('''
        CREATE TABLE denegaciones (
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
        
        print("Creando índices...")
        cursor.execute('CREATE INDEX idx_denegaciones_fecha ON denegaciones(fecha)')
        cursor.execute('CREATE INDEX idx_denegaciones_empleado ON denegaciones(id_empleado)')
        cursor.execute('CREATE INDEX idx_denegaciones_motivo ON denegaciones(motivo)')
        
        conexion.commit()
        conexion.close()
        
        print("✓ Tabla 'denegaciones' creada exitosamente!")
        
        # Mostrar estructura de la tabla
        print("\nEstructura de la tabla:")
        print("- id_denegacion: Clave primaria")
        print("- fecha, hora: Momento de la denegación")  
        print("- id_empleado: ID del empleado (NULL para no registrados)")
        print("- motivo: Razón de la denegación")
        print("- modo_operacion: 'ingreso' o 'egreso'")
        print("- minutos_tarde: Solo para motivo 'llegada_tarde'")
        print("- turno_esperado/detectado: Solo para 'turno_no_corresponde'")
        print("- nombre_detectado: Solo para 'persona_no_registrada'")
        print("- observaciones: Información adicional")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("=" * 50)
    print("CREACIÓN DE TABLA DE DENEGACIONES")
    print("=" * 50)
    
    if not os.path.exists(DB_RUTA):
        print(f"Error: No se encuentra la base de datos en {DB_RUTA}")
        exit(1)
    
    crear_tabla_denegaciones()