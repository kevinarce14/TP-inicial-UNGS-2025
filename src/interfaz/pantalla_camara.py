import cv2
import threading
import time
from datetime import datetime
from ..logica.config import (
    CAMERA_WIDTH, CAMERA_HEIGHT, GROSOR_MARCO_CARA, 
    GROSOR_FUENTE_MARCO, RECOGNITION_SLEEP
)
from ..utils.time_utils import determinar_turno_actual
from .manejador_mensajes import MessageHandler


class CameraDisplay:
    def __init__(self):
        self.frame_lock = threading.Lock()
        self.current_frame = None
        self.current_results = []
        self.running = False
        self.video = None
        self.last_access_status = {}  # Diccionario para guardar el último estado de acceso por empleado
        
    def setup_camera(self):
        """Configura e inicializa la cámara"""
        self.video = cv2.VideoCapture(0)
        if not self.video.isOpened():
            return False
            
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        return True
    
    def capture_thread(self, message_handler):
        """Hilo para capturar frames de la cámara"""
        try:
            while self.running:
                ret, frame = self.video.read()
                if not ret:
                    message_handler.add_message("Error: No se pudo leer el frame de la cámara", 'error')
                    break
                
                with self.frame_lock:
                    self.current_frame = frame.copy()
                    
        except Exception as e:
            message_handler.add_message(f"Error en hilo de captura: {e}", 'error')
    
    def recognition_thread(self, face_engine, attendance_manager, message_handler, mode='entry'):
        """Hilo para reconocimiento facial y procesamiento de asistencia"""
        try:
            while self.running:
                time.sleep(RECOGNITION_SLEEP)
                
                with self.frame_lock:
                    if self.current_frame is None:
                        continue
                    frame = self.current_frame.copy()
                
                # Reconocer caras
                matches = face_engine.recognize_faces(frame)
                
                # Procesar asistencia para cada cara reconocida
                for empleado_id, nombre, face_location in matches:
                    if empleado_id:  # Solo si se reconoció al empleado
                        # Actualizar que la persona fue vista
                        message_handler.update_person_seen(empleado_id)
                        
                        # Procesar según el modo
                        if mode == 'entry':
                            result = attendance_manager.process_entry(empleado_id, nombre)
                        else:  # mode == 'exit'
                            result = attendance_manager.process_exit(empleado_id, nombre)
                        
                        # Guardar el estado de acceso para usar en draw_face_rectangles
                        if result and 'type' in result:
                            self.last_access_status[empleado_id] = result['type']
                        
                        # Mostrar mensaje si hay resultado
                        if result and 'message' in result:
                            result_empleado_id = result.get('empleado_id')
                            if result_empleado_id is not None:
                                # Mensaje persistente (ligado al empleado específico)
                                message_handler.add_persistent_message(
                                    result_empleado_id, result['message'], result.get('type', 'info')
                                )
                            else:
                                # Mensaje temporal
                                message_handler.add_temporary_message(
                                    result['message'], result.get('type', 'info')
                                )
                    else:  # 👈 Caso NO reconocido
                                # Solo procesar desconocidos si no se procesó recientemente
                        #if "desconocido" not in self.last_access_status:
                            result = attendance_manager.process_entry(None, nombre or "Desconocido")
                        #else:
                        #    result = None
    
                    # Guardar el estado de acceso para usar en draw_face_rectangles
                    if result and 'type' in result:
                            key = empleado_id if empleado_id else "desconocido"
                            self.last_access_status[key] = result['type']

                    # Mostrar mensaje si hay resultado
                    if result and 'message' in result:
                        result_empleado_id = result.get('empleado_id')
                        if result_empleado_id is not None:
                            message_handler.add_persistent_message(
                            result_empleado_id, result['message'], result.get('type', 'info')
                        )
                        else:
                            message_handler.add_temporary_message(
                            result['message'], result.get('type', 'info')
                        )
                
                # Actualizar resultados para display
                with self.frame_lock:
                    self.current_results = matches
                    
        except Exception as e:
            message_handler.add_message(f"Error en hilo de reconocimiento: {e}", 'error')
    
    def draw_face_rectangles(self, frame, results):
        """Dibuja rectángulos alrededor de las caras detectadas"""
        for empleado_id, nombre, (top, right, bottom, left) in results:
            # Color verde si se reconoce y acceso permitido, rojo si acceso denegado
            if empleado_id:
                # Verificar si el último acceso fue denegado
                access_type = self.last_access_status.get(empleado_id, 'success')
                color = (0, 255, 0) if access_type == 'success' else (0, 0, 255)  # Verde para éxito, rojo para error/denegado
            else:
                color = (0, 0, 255)  # Rojo para no reconocido
            
            # Dibujar rectángulo alrededor de la cara
            cv2.rectangle(frame, (left, top), (right, bottom), color, GROSOR_MARCO_CARA)
            
            if nombre:
                # Calcular tamaño del texto para el fondo (con fuente más gruesa)
                text_size = cv2.getTextSize(nombre, cv2.FONT_HERSHEY_DUPLEX, 0.5, 2)[0]  # Fuente más gruesa (DUPLEX) y grosor 2
                
                # Dibujar fondo para el nombre (usando el mismo color que el rectángulo)
                cv2.rectangle(frame, (left, top-25), (left + text_size[0] + 10, top), color, -1)
                
                # Dibujar nombre en NEGRO con fuente más gruesa
                cv2.putText(frame, nombre, (left + 5, top-5),
                           cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 0), 2)  # Fuente DUPLEX y grosor 2
    
    def draw_center_message(self, frame, message_handler):
        """Dibuja el mensaje principal en la esquina izquierda de la pantalla SIN salto de línea"""
        center_msg = message_handler.get_center_message()
        if not center_msg:
            return

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        color = message_handler.get_color_for_type(center_msg.tipo)

        # Posición inicial en la esquina izquierda
        start_x = 20
        start_y = 50

        # Fondo siempre negro y borde del color del acceso
        bg_color = (0, 0, 0)  # Fondo negro como solicitado
        border_color = color
    
        # Calcular tamaño del texto SIN dividir en líneas
        text_size = cv2.getTextSize(center_msg.text, font, font_scale, thickness)[0]

        # Fondo
        padding = 8
        cv2.rectangle(frame,
                        (start_x - padding, start_y - text_size[1] - padding),
                        (start_x + text_size[0] + padding, start_y + padding),
                        bg_color, -1)
    
        # Borde
        cv2.rectangle(frame,
                        (start_x - padding, start_y - text_size[1] - padding),
                        (start_x + text_size[0] + padding, start_y + padding),
                        border_color, 2)

        # Texto con el color del tipo de acceso
        cv2.putText(frame, center_msg.text, (start_x, start_y), font, font_scale, color, thickness)
    
    def draw_temporary_messages(self, frame, message_handler):
        """Dibuja mensajes temporales en la esquina superior izquierda"""
        temp_messages = message_handler.get_temporary_messages()
        
        y_offset = 30
        for message in temp_messages:
            color = message_handler.get_color_for_type(message.tipo)
            
            # Calcular tamaño del texto
            text_size = cv2.getTextSize(message.text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            
            # Determinar color de fondo según el tipo de mensaje
            bg_color = (0, 0, 0)
            
            if message.tipo == 'success':
                bg_color = (0, 80, 0)
            elif message.tipo == 'error' or message.tipo == 'denied':
                bg_color = (0, 0, 80)
            elif message.tipo == 'warning':
                bg_color = (0, 80, 80)
            
            # Dibujar fondo del mensaje
            cv2.rectangle(frame, (10, y_offset - 20), (text_size[0] + 15, y_offset + 5), bg_color, -1)
            cv2.rectangle(frame, (10, y_offset - 20), (text_size[0] + 15, y_offset + 5), color, 1)
            
            # Dibujar texto del mensaje
            cv2.putText(frame, message.text, (12, y_offset - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            y_offset += 35
    
    def draw_info_panel(self, frame, mode='entry'):
        """Dibuja panel de información en la esquina superior derecha"""
        hora_actual = datetime.now().strftime("%H:%M:%S")
        turno_actual = determinar_turno_actual()
        modo_texto = "INGRESO" if mode == 'entry' else "EGRESO"
        info_text = f"{hora_actual} - Turno: {turno_actual} - {modo_texto}"
        
        # Calcular posición
        font_scale = 0.5
        thickness = 1
        text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        frame_width = frame.shape[1]
        
        # Dibujar fondo
        cv2.rectangle(frame, (frame_width - text_size[0] - 15, 5), 
                     (frame_width - 5, 25), (0, 0, 0), -1)
        cv2.rectangle(frame, (frame_width - text_size[0] - 15, 5), 
                     (frame_width - 5, 25), (255, 255, 255), 1)
        
        # Dibujar texto
        cv2.putText(frame, info_text, (frame_width - text_size[0] - 10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
    
    def run(self, face_engine, attendance_manager, message_handler, mode='entry'):
        """Ejecuta el sistema de visualización de cámara"""
        # Configurar cámara
        if not self.setup_camera():
            message_handler.add_message("Error: No se pudo abrir la cámara", 'error')
            return False
        
        self.running = True
        
        # Iniciar hilos
        capture_thread = threading.Thread(
            target=self.capture_thread, 
            args=(message_handler,), 
            daemon=True
        )
        
        recognition_thread = threading.Thread(
            target=self.recognition_thread,
            args=(face_engine, attendance_manager, message_handler, mode),
            daemon=True
        )
        
        capture_thread.start()
        recognition_thread.start()
        
        # Bucle principal de visualización
        try:
            while self.running:
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.1)
                        continue
                    frame = self.current_frame.copy()
                    results = self.current_results.copy()
                
                # Dibujar elementos en el frame
                self.draw_face_rectangles(frame, results)
                self.draw_center_message(frame, message_handler)
                self.draw_temporary_messages(frame, message_handler)
                self.draw_info_panel(frame, mode)
                
                # Mostrar frame
                cv2.imshow("Sistema de Control de Asistencia", frame)
                
                # Verificar teclas y estado de ventana
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("c"):  # Limpiar mensajes
                    message_handler.clear_all_messages()
                
                # Verificar si la ventana todavía existe
                if cv2.getWindowProperty("Sistema de Control de Asistencia", cv2.WND_PROP_VISIBLE) < 1:
                    break
                    
        except KeyboardInterrupt:
            message_handler.add_message("Sistema interrumpido por el usuario", 'info')
        except Exception as e:
            message_handler.add_message(f"Error en el bucle principal: {e}", 'error')
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Detiene el sistema de cámara"""
        self.running = False
        
        if self.video:
            self.video.release()
        
        try:
            cv2.destroyAllWindows()
        except:
            pass