#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funciones para limpiar registros de denegaciones
Agregar al archivo database_manager.py o crear como archivo separado
"""

import sqlite3
from datetime import datetime, timedelta

class DenegacionCleaner:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def contar_denegaciones(self, filtros=None):
        """Cuenta el total de denegaciones con filtros opcionales"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        query = "SELECT COUNT(*) FROM denegaciones"
        params = []
        
        if filtros:
            conditions = []
            if 'fecha_desde' in filtros:
                conditions.append("fecha >= ?")
                params.append(filtros['fecha_desde'])
            if 'fecha_hasta' in filtros:
                conditions.append("fecha <= ?")
                params.append(filtros['fecha_hasta'])
            if 'motivo' in filtros:
                conditions.append("motivo = ?")
                params.append(filtros['motivo'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conexion.close()
        return total
    
    def eliminar_todas_denegaciones(self, confirmacion=False):
        """Elimina TODAS las denegaciones - USAR CON CUIDADO"""
        if not confirmacion:
            print("ADVERTENCIA: Esta función eliminará TODAS las denegaciones")
            print("Para confirmar, llama a la función con confirmacion=True")
            return 0
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        # Contar antes de eliminar
        total_antes = self.contar_denegaciones()
        
        cursor.execute("DELETE FROM denegaciones")
        conexion.commit()
        eliminadas = cursor.rowcount
        
        # Reiniciar el contador de ID
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='denegaciones'")
        conexion.commit()
        
        conexion.close()
        
        print(f"Se eliminaron {eliminadas} denegaciones (total antes: {total_antes})")
        return eliminadas
    
    def eliminar_denegaciones_por_fecha(self, dias_antiguedad=7, confirmacion=False):
        """Elimina denegaciones más antiguas que X días"""
        if not confirmacion:
            print(f"Esta función eliminará denegaciones más antiguas que {dias_antiguedad} días")
            print("Para confirmar, llama a la función con confirmacion=True")
            return 0
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        fecha_limite = (datetime.now() - timedelta(days=dias_antiguedad)).date().isoformat()
        
        # Contar antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM denegaciones WHERE fecha < ?", (fecha_limite,))
        total_a_eliminar = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM denegaciones WHERE fecha < ?", (fecha_limite,))
        conexion.commit()
        eliminadas = cursor.rowcount
        
        conexion.close()
        
        print(f"Se eliminaron {eliminadas} denegaciones anteriores a {fecha_limite}")
        return eliminadas
    
    def eliminar_denegaciones_por_motivo(self, motivo, confirmacion=False):
        """Elimina denegaciones de un motivo específico"""
        if not confirmacion:
            print(f"Esta función eliminará todas las denegaciones con motivo '{motivo}'")
            print("Para confirmar, llama a la función con confirmacion=True")
            return 0
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        # Contar antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM denegaciones WHERE motivo = ?", (motivo,))
        total_a_eliminar = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM denegaciones WHERE motivo = ?", (motivo,))
        conexion.commit()
        eliminadas = cursor.rowcount
        
        conexion.close()
        
        print(f"Se eliminaron {eliminadas} denegaciones con motivo '{motivo}'")
        return eliminadas
    
    def eliminar_denegaciones_duplicadas(self, confirmacion=False):
        """Elimina denegaciones duplicadas (mismo empleado, motivo, fecha y hora)"""
        if not confirmacion:
            print("Esta función eliminará denegaciones duplicadas")
            print("Para confirmar, llama a la función con confirmacion=True")
            return 0
        
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        # Encontrar y eliminar duplicados manteniendo solo el registro con ID más bajo
        cursor.execute('''
        DELETE FROM denegaciones 
        WHERE id_denegacion NOT IN (
            SELECT MIN(id_denegacion)
            FROM denegaciones 
            GROUP BY COALESCE(id_empleado, nombre_detectado), motivo, fecha, hora
        )
        ''')
        
        conexion.commit()
        eliminadas = cursor.rowcount
        conexion.close()
        
        print(f"Se eliminaron {eliminadas} denegaciones duplicadas")
        return eliminadas
    
    def limpiar_denegaciones_masivo(self, mantener_dias=7, eliminar_duplicados=True, 
                                   motivos_a_eliminar=None, confirmacion=False):
        """Función integral de limpieza"""
        if not confirmacion:
            print("LIMPIEZA MASIVA DE DENEGACIONES")
            print("=" * 40)
            print(f"- Mantener solo últimos {mantener_dias} días")
            if eliminar_duplicados:
                print("- Eliminar duplicados")
            if motivos_a_eliminar:
                print(f"- Eliminar motivos: {motivos_a_eliminar}")
            print("\nPara confirmar, llama con confirmacion=True")
            return 0
        
        total_eliminadas = 0
        
        print("Iniciando limpieza masiva...")
        
        # 1. Eliminar por motivos específicos
        if motivos_a_eliminar:
            for motivo in motivos_a_eliminar:
                eliminadas = self.eliminar_denegaciones_por_motivo(motivo, confirmacion=True)
                total_eliminadas += eliminadas
        
        # 2. Eliminar duplicados
        if eliminar_duplicados:
            eliminadas = self.eliminar_denegaciones_duplicadas(confirmacion=True)
            total_eliminadas += eliminadas
        
        # 3. Eliminar por antigüedad
        eliminadas = self.eliminar_denegaciones_por_fecha(mantener_dias, confirmacion=True)
        total_eliminadas += eliminadas
        
        print(f"\nLimpieza completada. Total eliminadas: {total_eliminadas}")
        return total_eliminadas
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas de las denegaciones actuales"""
        conexion = sqlite3.connect(self.db_path)
        cursor = conexion.cursor()
        
        print("ESTADÍSTICAS DE DENEGACIONES")
        print("=" * 30)
        
        # Total general
        cursor.execute("SELECT COUNT(*) FROM denegaciones")
        total = cursor.fetchone()[0]
        print(f"Total de denegaciones: {total}")
        
        if total == 0:
            print("No hay denegaciones registradas.")
            conexion.close()
            return
        
        # Por motivo
        print("\nPor motivo:")
        cursor.execute("SELECT motivo, COUNT(*) FROM denegaciones GROUP BY motivo ORDER BY COUNT(*) DESC")
        for motivo, cantidad in cursor.fetchall():
            print(f"  {motivo}: {cantidad}")
        
        # Por fecha (últimos 7 días)
        print("\nÚltimos 7 días:")
        cursor.execute('''
        SELECT fecha, COUNT(*) 
        FROM denegaciones 
        WHERE fecha >= date('now', '-7 days')
        GROUP BY fecha 
        ORDER BY fecha DESC
        ''')
        for fecha, cantidad in cursor.fetchall():
            print(f"  {fecha}: {cantidad}")
        
        # Registro más antiguo y más reciente
        cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM denegaciones")
        fecha_min, fecha_max = cursor.fetchone()
        print(f"\nRango de fechas: {fecha_min} a {fecha_max}")
        
        conexion.close()

# Funciones standalone para usar directamente
def limpiar_denegaciones_rapido(db_path='database/asistencia_empleados.db'):
    """Función rápida para limpieza básica"""
    cleaner = DenegacionCleaner(db_path)
    
    print("LIMPIEZA RÁPIDA DE DENEGACIONES")
    print("=" * 35)
    
    # Mostrar estadísticas actuales
    cleaner.mostrar_estadisticas()
    
    # Opciones de limpieza
    print("\nOpciones disponibles:")
    print("1. Eliminar denegaciones más antiguas que 7 días")
    print("2. Eliminar denegaciones duplicadas")
    print("3. Eliminar TODAS las denegaciones")
    print("4. Limpieza personalizada")
    print("0. Solo ver estadísticas (no eliminar nada)")
    
    opcion = input("\nSelecciona una opción (0-4): ").strip()
    
    if opcion == "1":
        dias = input("¿Cuántos días mantener? (default: 7): ").strip()
        dias = int(dias) if dias.isdigit() else 7
        cleaner.eliminar_denegaciones_por_fecha(dias, confirmacion=True)
    
    elif opcion == "2":
        cleaner.eliminar_denegaciones_duplicadas(confirmacion=True)
    
    elif opcion == "3":
        confirmacion = input("¿SEGURO que quieres eliminar TODAS? (escribe 'SI'): ").strip()
        if confirmacion == "SI":
            cleaner.eliminar_todas_denegaciones(confirmacion=True)
        else:
            print("Operación cancelada")
    
    elif opcion == "4":
        print("Limpieza personalizada:")
        dias = input("Días a mantener (default: 7): ").strip()
        dias = int(dias) if dias.isdigit() else 7
        
        duplicados = input("¿Eliminar duplicados? (s/N): ").strip().lower() 
        eliminar_duplicados = duplicados in ['s', 'si', 'sí']
        
        cleaner.limpiar_denegaciones_masivo(
            mantener_dias=dias,
            eliminar_duplicados=eliminar_duplicados,
            confirmacion=True
        )
    
    elif opcion == "0":
        print("No se eliminó nada.")
    
    else:
        print("Opción no válida")

if __name__ == "__main__":
    # Ejecutar limpieza rápida
    limpiar_denegaciones_rapido()