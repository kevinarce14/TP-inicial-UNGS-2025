"""
Módulo core - Lógica de negocio central
"""

from .administrador_database import DatabaseManager
from .face_recognition_engine import FaceRecognitionEngine
from .asistencia_logica import AttendanceManager
from . import config

__all__ = [
    'DatabaseManager',
    'FaceRecognitionEngine', 
    'AttendanceManager',
    'config'
]