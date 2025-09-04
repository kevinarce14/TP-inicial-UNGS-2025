import face_recognition
import cv2
import numpy as np
from .config import TOLERANCIA, MODEL, FRAME_SCALE
from .administrador_database import DatabaseManager

class FaceRecognitionEngine:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.empleados_caras = []
        self.empleados_nombres = []
        self.empleados_ids = []
        self.last_matches = []  # Para reutilizar encodings previos
        
    def load_known_faces(self):
        """Carga las caras conocidas desde la base de datos"""
        print("Cargando imágenes conocidas desde la base de datos...")
        self.empleados_caras, self.empleados_nombres, self.empleados_ids = self.db_manager.cargar_embeddings()
        print(f"Cargadas {len(self.empleados_caras)} caras conocidas")
        return len(self.empleados_caras) > 0
    
    def detect_and_encode_faces(self, frame):
        """Detecta y codifica caras en un frame"""
        # Redimensionar para acelerar
        small_frame = cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE)
        
        # Detectar ubicaciones
        face_locations = face_recognition.face_locations(small_frame, model=MODEL)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        # Escalar ubicaciones al tamaño original
        scale_factor = int(1 / FRAME_SCALE)
        face_locations = [(t*scale_factor, r*scale_factor, b*scale_factor, l*scale_factor) 
                         for (t, r, b, l) in face_locations]
        
        return face_locations, face_encodings
    
    def recognize_faces(self, frame):
        """Reconoce caras en un frame y devuelve coincidencias"""
        if not self.empleados_caras:
            return []
        
        face_locations, face_encodings = self.detect_and_encode_faces(frame)
        current_matches = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            match_id = None
            match_name = None
            
            # Reutilizar coincidencia anterior si la cara está cerca
            for last_id, last_name, last_loc in self.last_matches:
                if self._misma_cara(face_location, last_loc):
                    match_id = last_id
                    match_name = last_name
                    break
            
            # Si no estaba, comparar contra base de datos
            if match_id is None:
                results = face_recognition.compare_faces(self.empleados_caras, face_encoding, TOLERANCIA)
                if True in results:
                    match_index = results.index(True)
                    match_id = self.empleados_ids[match_index]
                    match_name = self.empleados_nombres[match_index]
            
            current_matches.append((match_id, match_name, face_location))
        
        # Actualizar matches previos
        self.last_matches = current_matches.copy()
        return current_matches
    
    def _misma_cara(self, loc1, loc2, threshold=50):
        """Determina si dos ubicaciones corresponden a la misma cara"""
        return abs(loc1[0] - loc2[0]) < threshold and abs(loc1[1] - loc2[1]) < threshold
    
    def encode_face_from_file(self, image_path):
        """Codifica una cara desde un archivo de imagen"""
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            
            if not encodings:
                return None
            
            return encodings[0]
        except Exception as e:
            print(f"Error al codificar imagen {image_path}: {e}")
            return None
    
    def reload_faces(self):
        """Recarga las caras conocidas (útil después de agregar empleados)"""
        return self.load_known_faces()