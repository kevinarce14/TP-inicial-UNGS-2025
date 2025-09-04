#!/usr/bin/env python3
"""
Sistema de Control de Asistencia con Reconocimiento Facial
Punto de entrada principal

Uso:
    python main.py [--mode entry|exit] [--config config.json]
    
Comandos:
    --mode entry    : Modo ingreso (por defecto)
    --mode exit     : Modo egreso  
    --config FILE   : Archivo de configuración personalizado
    
Controles durante ejecución:
    'q' - Salir del sistema
    'c' - Limpiar mensajes en pantalla
"""

import sys
import argparse
import os

# Agregar src al path para importaciones
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logica.face_recognition_engine import FaceRecognitionEngine
from src.logica.asistencia_logica import AttendanceManager
from src.logica.administrador_database import DatabaseManager
from src.interfaz.pantalla_camara import CameraDisplay
from src.interfaz.manejador_mensajes import MessageHandler

def setup_system():
    """Inicializa y configura el sistema"""
    print("=" * 60)
    print("SISTEMA DE CONTROL DE ASISTENCIA")
    print("=" * 60)
    
    # Inicializar componentes
    print("Inicializando componentes del sistema...")
    
    try:
        db_manager = DatabaseManager()
        face_engine = FaceRecognitionEngine()
        attendance_manager = AttendanceManager()
        camera_display = CameraDisplay()
        message_handler = MessageHandler()
        
        print("✓ Componentes inicializados correctamente")
        
        # Verificar y crear base de datos si es necesario
        print("Verificando base de datos...")
        db_manager.verificar_tablas()
        print("✓ Base de datos verificada")
        
        # Cargar caras conocidas
        print("Cargando empleados registrados...")
        if not face_engine.load_known_faces():
            message_handler.add_message("Advertencia: No se encontraron empleados registrados", 'warning')
            print("⚠ No se encontraron empleados registrados")
        else:
            print("✓ Empleados cargados correctamente")
        
        return face_engine, attendance_manager, camera_display, message_handler
        
    except Exception as e:
        print(f"✗ Error durante la inicialización: {e}")
        return None

def run_entry_mode():
    """Ejecuta el sistema en modo INGRESO"""
    print("\n" + "=" * 30)
    print("MODO: CONTROL DE INGRESOS")
    print("=" * 30)
    
    components = setup_system()
    if not components:
        return False
    
    face_engine, attendance_manager, camera_display, message_handler = components
    
    print("\nIniciando sistema de control de ingresos...")
    print("Presiona 'q' para salir, 'c' para limpiar mensajes")
    print("-" * 50)
    
    try:
        return camera_display.run(
            face_engine=face_engine,
            attendance_manager=attendance_manager,
            message_handler=message_handler,
            mode='entry'
        )
    except KeyboardInterrupt:
        print("\n\nSistema interrumpido por el usuario")
        return True
    except Exception as e:
        print(f"\nError durante la ejecución: {e}")
        return False

def run_exit_mode():
    """Ejecuta el sistema en modo EGRESO"""
    print("\n" + "=" * 30)
    print("MODO: CONTROL DE EGRESOS")
    print("=" * 30)
    
    components = setup_system()
    if not components:
        return False
    
    face_engine, attendance_manager, camera_display, message_handler = components
    
    print("\nIniciando sistema de control de egresos...")
    print("Presiona 'q' para salir, 'c' para limpiar mensajes")
    print("-" * 50)
    
    try:
        return camera_display.run(
            face_engine=face_engine,
            attendance_manager=attendance_manager,
            message_handler=message_handler,
            mode='exit'
        )
    except KeyboardInterrupt:
        print("\n\nSistema interrumpido por el usuario")
        return True
    except Exception as e:
        print(f"\nError durante la ejecución: {e}")
        return False

def show_system_info():
    """Muestra información del sistema"""
    try:
        from src.logica.config import TURNOS, DB_RUTA, DEPARTAMENTOS_VALIDOS
        from src.utils.time_utils import determinar_turno_actual
        
        print("\n" + "=" * 50)
        print("INFORMACIÓN DEL SISTEMA")
        print("=" * 50)
        print(f"Base de datos: {DB_RUTA}")
        print(f"Turno actual: {determinar_turno_actual()}")
        print(f"Departamentos: {', '.join(DEPARTAMENTOS_VALIDOS)}")
        print("\nHorarios de turnos:")
        for turno, horario in TURNOS.items():
            print(f"  {turno}: {horario['inicio']} - {horario['fin']}")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error al mostrar información: {e}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Sistema de Control de Asistencia con Reconocimiento Facial",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    # Modo ingreso (por defecto)
  python main.py --mode entry       # Modo ingreso explícito
  python main.py --mode exit        # Modo egreso
  python main.py --info             # Mostrar información del sistema
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['entry', 'exit'],
                       default='entry',
                       help='Modo de operación: entry (ingreso) o exit (egreso)')
    
    parser.add_argument('--info',
                       action='store_true',
                       help='Mostrar información del sistema y salir')
    
    args = parser.parse_args()
    
    # Mostrar información si se solicita
    if args.info:
        show_system_info()
        return 0
    
    # Ejecutar según el modo seleccionado
    try:
        if args.mode == 'entry':
            success = run_entry_mode()
        elif args.mode == 'exit':
            success = run_exit_mode()
        else:
            print(f"Error: Modo '{args.mode}' no reconocido")
            return 1
        
        if success:
            print("\nSistema terminado correctamente")
            return 0
        else:
            print("\nSistema terminado con errores")
            return 1
            
    except Exception as e:
        print(f"\nError crítico: {e}")
        return 1
    finally:
        print("\nGracias por usar el Sistema de Control de Asistencia")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)