# actualizar_bd_produccion.py - Script para agregar módulo de producción a BD existente

import sys
import os
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logica.administrador_database import DatabaseManager
from src.logica.production_manager import ProductionManager

def main():
    print("=" * 60)
    print("ACTUALIZACIÓN DE BASE DE DATOS - MÓDULO PRODUCCIÓN")
    print("=" * 60)
    
    try:
        # Verificar BD existente
        print("\n1. Verificando base de datos existente...")
        db_manager = DatabaseManager()
        db_manager.verificar_tablas()
        print("B Base de datos de asistencia verificada")
        
        # Crear tabla de denegaciones si no existe (tu código actual)
        print("\n2. Verificando tabla de denegaciones...")
        db_manager.crear_tabla_denegaciones()
        print("B Tabla de denegaciones verificada")
        
        # Crear módulo de producción
        print("\n3. Creando módulo de producción...")
        production_manager = ProductionManager()
        print("B Tabla de producción creada con:")
        print("  - Cálculo automático de OEE")
        print("  - Disponibilidad, Rendimiento y Calidad")
        print("  - Validaciones de integridad")
        print("  - Índices optimizados")
        print("  - Triggers de actualización")
        
        # Verificar empleados existentes
        print("\n4. Verificando empleados registrados...")
        empleados_caras, empleados_nombres, empleados_ids = db_manager.cargar_embeddings()
        print(f"B Encontrados {len(empleados_ids)} empleados registrados")
        
        if empleados_ids:
            print("\n5. Empleados disponibles para producción:")
            for emp_id, nombre in zip(empleados_ids[:5], empleados_nombres[:5]):
                print(f"   ID {emp_id}: {nombre}")
            if len(empleados_ids) > 5:
                print(f"   ... y {len(empleados_ids) - 5} más")
        else:
            print("\n⚠ NOTA: No hay empleados registrados.")
            print("  Para usar el módulo de producción, primero registre empleados con:")
            print("  python src/gestor_database/add_employee.py")
        
        print("\n" + "=" * 60)
        print("ACTUALIZACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        
        print("\n📋 ESTRUCTURA DE BD ACTUALIZADA:")
        print("└── asistencia_empleados.db")
        print("    ├── empleados (existente)")
        print("    ├── asistencias (existente)")
        print("    ├── denegaciones (verificada)")
        print("    └── produccion (nueva)")
        print("        ├── Cálculos automáticos de OEE")
        print("        ├── Métricas de Disponibilidad, Rendimiento, Calidad")
        print("        ├── Validaciones de integridad")
        print("        └── Índices optimizados")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("1. Ejecutar: python ejemplo_produccion.py")
        print("2. Integrar módulo con interfaz de usuario")
        print("3. Crear reportes y dashboards")
        print("4. Configurar alertas por OEE bajo")
        
        print("\n💡 FUNCIONALIDADES DISPONIBLES:")
        print("- Registro de producción por empleado/turno")
        print("- Cálculo automático de OEE (Overall Equipment Effectiveness)")
        print("- Análisis de pérdidas por Disponibilidad/Rendimiento/Calidad")
        print("- Ranking de empleados por rendimiento")
        print("- Estadísticas y reportes por período")
        print("- Clasificación automática (Excelente/Bueno/Regular/Deficiente)")
        print("- Consultas por fecha, empleado, producto, turno")
        
    except Exception as e:
        print(f"\nX ERROR durante la actualización: {e}")
        print("\nVerifique:")
        print("1. Que la estructura de carpetas src/ sea correcta")
        print("2. Que los archivos Python estén en sus ubicaciones")
        print("3. Que tenga permisos de escritura en database/")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        print(f"\n✅ Base de datos actualizada correctamente")
        print("La tabla de producción está lista para usar!")
    else:
        print(f"\nX Error en la actualización")
    
    sys.exit(exit_code)