import time
from datetime import datetime
from .administrador_database import DatabaseManager
from ..utils.time_utils import determinar_turno_actual, calcular_minutos_tarde, determinar_observacion
from .config import MAX_MINUTOS_TARDE, REGISTRO_COOLDOWN

class AttendanceManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.ultimo_registro = {}  # Para evitar registros múltiples
        
    def process_entry(self, empleado_id, nombre_completo):
        """Procesa el ingreso de un empleado"""
        # Verificar cooldown
        if not self._verificar_cooldown(empleado_id):
            # No devolver mensaje si está en cooldown, solo ignorar
            return None
        
        # Obtener información del empleado
        empleado = self.db_manager.obtener_empleado(empleado_id)
        if not empleado:
            return {
                'success': False,
                'message': f"Error: Empleado {empleado_id} no encontrado",
                'type': 'error',
                'empleado_id': None  # No es persistente, no hay empleado válido
            }
        
        # Verificar si ya registró asistencia hoy
        asistencia_hoy = self.db_manager.verificar_asistencia_hoy(empleado_id)
        if asistencia_hoy and asistencia_hoy['tiene_ingreso']:
            return {
                'success': False,
                'message': f"{nombre_completo} ya registro ingreso hoy",
                'type': 'success',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
        
        # Validar turno
        turno_actual = determinar_turno_actual()
        if empleado['turno'] != turno_actual:
            return {
                'success': False,
                'message': f"Acceso denegado: {nombre_completo} No pertenece al turno {turno_actual}",
                'type': 'error',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
        
        # Calcular tardanza
        ahora = datetime.now()
        minutos_tarde = calcular_minutos_tarde(ahora.time(), empleado['turno'])
        
        # Verificar límite de tardanza
        if minutos_tarde > MAX_MINUTOS_TARDE:
            return {
                'success': False,
                'message': f"Acceso denegado: {nombre_completo} llego {minutos_tarde} minutos tarde",
                'type': 'error',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
        
        # Registrar ingreso
        observacion = determinar_observacion(minutos_tarde)
        hora_actual = ahora.strftime("%H:%M:%S")
        
        success = self.db_manager.registrar_ingreso(
            empleado_id, empleado['turno'], hora_actual, minutos_tarde, observacion
        )
        
        if not success:
            return {
                'success': False,
                'message': f"Error al registrar ingreso de {nombre_completo}",
                'type': 'error',
                'empleado_id': None  # Mensaje temporal
            }
        
        # Actualizar cooldown
        self._actualizar_cooldown(empleado_id)
        
        # Generar mensaje de éxito
        if observacion == 'Puntual':
            message = f"Ingreso registrado para {nombre_completo} a las {hora_actual}"
            msg_type = 'success'
        else:
            message = f"Ingreso registrado para {nombre_completo} a las {hora_actual}. {observacion}"
            msg_type = 'warning'
        
        return {
            'success': True,
            'message': message,
            'type': msg_type,
            'empleado_id': None,  # Mensaje temporal (se registró exitosamente)
            'data': {
                'empleado_id': empleado_id,
                'hora': hora_actual,
                'minutos_tarde': minutos_tarde,
                'observacion': observacion
            }
        }
    
    def process_exit(self, empleado_id, nombre_completo):
        """Procesa la salida de un empleado"""
        # Verificar cooldown
        if not self._verificar_cooldown(empleado_id):
            # No devolver mensaje si está en cooldown, solo ignorar
            return None
        
        # Verificar si tiene ingreso registrado hoy
        asistencia_hoy = self.db_manager.verificar_asistencia_hoy(empleado_id)
        if not asistencia_hoy or not asistencia_hoy['tiene_ingreso']:
            return {
                'success': False,
                'message': f"{nombre_completo} no tiene ingreso registrado hoy",
                'type': 'error',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
        
        # Verificar si ya registró salida
        if asistencia_hoy['tiene_egreso']:
            return {
                'success': False,
                'message': f"{nombre_completo} ya registro salida hoy",
                'type': 'success',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
        
        # Registrar salida
        ahora = datetime.now()
        hora_actual = ahora.strftime("%H:%M:%S")
        
        success = self.db_manager.registrar_egreso(empleado_id, hora_actual)
        
        if success:
            # Actualizar cooldown
            self._actualizar_cooldown(empleado_id)
            
            return {
                'success': True,
                'message': f"Salida registrada para {nombre_completo} a las {hora_actual}",
                'type': 'success',
                'empleado_id': None,  # Mensaje temporal (se registró exitosamente)
                'data': {
                    'empleado_id': empleado_id,
                    'hora': hora_actual
                }
            }
        else:
            return {
                'success': False,
                'message': f"Error al registrar salida de {nombre_completo}",
                'type': 'error',
                'empleado_id': empleado_id  # Mensaje persistente para este empleado
            }
    
    def _verificar_cooldown(self, empleado_id):
        """Verifica si ha pasado suficiente tiempo desde el ultimo registro"""
        ahora = time.time()
        if empleado_id in self.ultimo_registro:
            tiempo_transcurrido = ahora - self.ultimo_registro[empleado_id]
            return tiempo_transcurrido > REGISTRO_COOLDOWN
        return True
    
    def _actualizar_cooldown(self, empleado_id):
        """Actualiza el timestamp del último registro"""
        self.ultimo_registro[empleado_id] = time.time()
    
    def get_employee_status_today(self, empleado_id):
        """Obtiene el estado de asistencia del empleado hoy"""
        asistencia = self.db_manager.verificar_asistencia_hoy(empleado_id)
        empleado = self.db_manager.obtener_empleado(empleado_id)
        
        if not empleado:
            return None
        
        status = {
            'empleado': empleado,
            'tiene_ingreso': False,
            'tiene_egreso': False,
            'hora_ingreso': None,
            'hora_egreso': None
        }
        
        if asistencia:
            status.update({
                'tiene_ingreso': asistencia['tiene_ingreso'],
                'tiene_egreso': asistencia['tiene_egreso'],
                'hora_ingreso': asistencia['hora_ingreso'],
                'hora_egreso': asistencia['hora_egreso']
            })
        
        return status