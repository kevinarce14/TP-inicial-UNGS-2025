import time
import threading
from datetime import datetime
from ..logica.config import DURACION_MENSAJE

class PersistentMessage:
    def __init__(self, empleado_id, mensaje, mensaje_tipo='info'):
        self.empleado_id = empleado_id
        self.text = mensaje
        self.tipo = mensaje_tipo
        self.timestamp = time.time()
        self.last_seen = time.time()
        
    def update_last_seen(self):
        """Actualiza el timestamp de última vez visto"""
        self.last_seen = time.time()
        
    def is_person_gone(self, timeout=2.0):
        """Verifica si la persona ya no está en la imagen (no vista por X segundos)"""
        return time.time() - self.last_seen > timeout

class TemporaryMessage:
    def __init__(self, mensaje, mensaje_tipo='info'):
        self.text = mensaje
        self.timestamp = time.time()
        self.tipo = mensaje_tipo
        
    def is_expired(self):
        return time.time() - self.timestamp > DURACION_MENSAJE

class MessageHandler:
    def __init__(self):
        self.persistent_messages = {}  # {empleado_id: PersistentMessage}
        self.temporary_messages = []   # Lista de mensajes temporales
        self.lock_mensajes = threading.Lock()
        self.mensaje_mostrado = {}     # Para evitar spam en consola
    
    def add_message(self, mensaje, mensaje_tipo='info', empleado_id=None):
        """
        Método general para agregar mensajes.
        Si se proporciona empleado_id, crea un mensaje persistente.
        Si no, crea un mensaje temporal.
        """
        if empleado_id is not None:
            self.add_persistent_message(empleado_id, mensaje, mensaje_tipo)
        else:
            self.add_temporary_message(mensaje, mensaje_tipo)
    
    def add_persistent_message(self, empleado_id, mensaje, mensaje_tipo='info'):
        """Agrega un mensaje persistente para un empleado específico"""
        with self.lock_mensajes:
            # Solo agregar si no existe ya un mensaje para este empleado
            if empleado_id not in self.persistent_messages:
                self.persistent_messages[empleado_id] = PersistentMessage(empleado_id, mensaje, mensaje_tipo)
                
                # Imprimir en consola solo una vez
                if empleado_id not in self.mensaje_mostrado:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] {mensaje}")
                    self.mensaje_mostrado[empleado_id] = True
    
    def add_temporary_message(self, mensaje, mensaje_tipo='info'):
        """Agrega un mensaje temporal (no ligado a un empleado específico)"""
        with self.lock_mensajes:
            self.temporary_messages.append(TemporaryMessage(mensaje, mensaje_tipo))
            
        # Imprimir en consola
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {mensaje}")
    
    def update_person_seen(self, empleado_id):
        """Actualiza que la persona fue vista (para mantener el mensaje)"""
        with self.lock_mensajes:
            if empleado_id in self.persistent_messages:
                self.persistent_messages[empleado_id].update_last_seen()
    
    def get_center_message(self):
        """Obtiene el mensaje para mostrar en el centro (solo uno, el más reciente)"""
        with self.lock_mensajes:
            # Limpiar mensajes de personas que ya no están
            to_remove = []
            for empleado_id, msg in self.persistent_messages.items():
                if msg.is_person_gone():
                    to_remove.append(empleado_id)
            
            for empleado_id in to_remove:
                del self.persistent_messages[empleado_id]
                # Limpiar también el flag de mensaje mostrado
                if empleado_id in self.mensaje_mostrado:
                    del self.mensaje_mostrado[empleado_id]
            
            # Retornar el mensaje persistente más reciente
            if self.persistent_messages:
                latest_msg = max(self.persistent_messages.values(), key=lambda x: x.timestamp)
                return latest_msg
            
            return None
    
    def get_temporary_messages(self):
        """Obtiene los mensajes temporales activos"""
        with self.lock_mensajes:
            # Limpiar mensajes expirados
            self.temporary_messages = [msg for msg in self.temporary_messages if not msg.is_expired()]
            return list(self.temporary_messages)
    
    def get_active_messages(self):
        """Obtiene todos los mensajes activos (temporales + el persistente más reciente)"""
        messages = []
        
        # Agregar mensaje central (persistente)
        center_msg = self.get_center_message()
        if center_msg:
            messages.append(center_msg)
        
        # Agregar mensajes temporales
        temp_messages = self.get_temporary_messages()
        messages.extend(temp_messages)
        
        return messages
    
    def clear_all_messages(self):
        """Limpia todos los mensajes"""
        with self.lock_mensajes:
            self.persistent_messages.clear()
            self.temporary_messages.clear()
            self.mensaje_mostrado.clear()
    
    def clear_person_message(self, empleado_id):
        """Limpia el mensaje de una persona específica"""
        with self.lock_mensajes:
            if empleado_id in self.persistent_messages:
                del self.persistent_messages[empleado_id]
            if empleado_id in self.mensaje_mostrado:
                del self.mensaje_mostrado[empleado_id]
    
    def get_color_for_type(self, mensaje_tipo):
        """Obtiene el color BGR para un tipo de mensaje"""
        colores = {
            'success': (0, 150, 0),    # Verde
            'error': (0, 0, 255),      # Rojo
            'warning': (0, 165, 255),  # Naranja
            'info': (255, 255, 255)    # Blanco
        }
        return colores.get(mensaje_tipo, (255, 255, 255))