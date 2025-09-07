import time
from datetime import datetime
from .administrador_database import DatabaseManager
from ..utils.time_utils import determinar_turno_actual, calcular_minutos_tarde, determinar_observacion
from .config import MAX_MINUTOS_TARDE, REGISTRO_COOLDOWN, DENEGACION_COOLDOWN

class AttendanceManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.ultimo_registro = {}  # Para evitar registros múltiples
        self.ultima_denegacion = {}  # Para evitar denegaciones múltiples
        
    def process_entry(self, empleado_id, nombre_completo):
        """Procesa el ingreso de un empleado"""
        # Verificar cooldown
        if not self._verificar_cooldown(empleado_id):
            # No devolver mensaje si está en cooldown, solo ignorar
            return None
        
        # Obtener información del empleado
        empleado = self.db_manager.obtener_empleado(empleado_id)
        if not empleado:
            #unknown_key = nombre_completo or "desconocido"
            key = "persona_no_registrada_global"
            # Solo mostrar mensaje y devolver dict si pasa cooldown

            if self._cooldown_take(self.ultima_denegacion, key, DENEGACION_COOLDOWN):
                print('persona_no_registrada')
                self.db_manager.registrar_denegacion(
                    motivo='persona_no_registrada',
                    modo_operacion='ingreso',
                    nombre_detectado=nombre_completo
                )
                #self._actualizar_cooldown_denegacion('persona_no_registrada', unknown_key)

                return {
                    'success': False,
                    'message': f"Error: Empleado  no registrado",
                    'type': 'error',
                    'empleado_id': None
                }

            # Si está en cooldown, no devolver nada (ignorar)
            return None
        
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
            # REGISTRAR DENEGACIÓN: Turno no corresponde (con cooldown)
            if self._verificar_cooldown_denegacion('turno_no_corresponde', empleado_id):
                self.db_manager.registrar_denegacion(
                    motivo='turno_no_corresponde',
                    modo_operacion='ingreso',
                    id_empleado=empleado_id,
                    turno_esperado=empleado['turno'],
                    turno_detectado=turno_actual
                )
                self._actualizar_cooldown_denegacion('turno_no_corresponde', empleado_id)
            
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
            # REGISTRAR DENEGACIÓN: Llegada tarde (con cooldown)
            if self._verificar_cooldown_denegacion('llegada_tarde', empleado_id):
                self.db_manager.registrar_denegacion(
                    motivo='llegada_tarde',
                    modo_operacion='ingreso',
                    id_empleado=empleado_id,
                    minutos_tarde=minutos_tarde,
                    observaciones=f"Llego {minutos_tarde} minutos tarde (limite: {MAX_MINUTOS_TARDE})"
                )
                self._actualizar_cooldown_denegacion('llegada_tarde', empleado_id)
            
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
            # REGISTRAR DENEGACIÓN: Sin ingreso previo (con cooldown)
            if self._verificar_cooldown_denegacion('sin_ingreso_previo', empleado_id):
                self.db_manager.registrar_denegacion(
                    motivo='sin_ingreso_previo',
                    modo_operacion='egreso',
                    id_empleado=empleado_id,
                    observaciones="Intento registrar egreso sin tener ingreso"
                )
                self._actualizar_cooldown_denegacion('sin_ingreso_previo', empleado_id)
            
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
    
    def _verificar_cooldown_denegacion(self, motivo, empleado_id):
        """Verifica si ha pasado suficiente tiempo desde la última denegación del mismo tipo"""
        ahora = time.time()
        clave = f"{motivo}_{empleado_id}"
        
        if clave in self.ultima_denegacion:
            tiempo_transcurrido = ahora - self.ultima_denegacion[clave]
            return tiempo_transcurrido > DENEGACION_COOLDOWN
        return True
    
    def _actualizar_cooldown_denegacion(self, motivo, empleado_id):
        """Actualiza el timestamp de la última denegación"""
        clave = f"{motivo}_{empleado_id}"
        self.ultima_denegacion[clave] = time.time()
    
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
    
    def _cooldown_take(self, bucket: dict, key: str, window) -> bool:
        """
        Intenta 'tomar' el cooldown. Devuelve True si corresponde ejecutar la acción y
        actualiza el timestamp en el mismo paso (atómico). Si no, devuelve False.
        Soporta window en segundos o datetime.timedelta.
        """
        now = time.time()

        # Normalizar window a segundos
        try:
            win = float(window.total_seconds())  # si es timedelta
        except AttributeError:
            win = float(window)  # si ya es número

        last = bucket.get(key, 0.0)
        if now - last > win:
            bucket[key] = now
            return True
        return False