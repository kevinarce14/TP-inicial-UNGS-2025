import os
import re
from ..logica.config import DEPARTAMENTOS_VALIDOS, TURNOS_VALIDOS

def validar_departamento(departamento):
    """Valida si el departamento es válido"""
    if departamento not in DEPARTAMENTOS_VALIDOS:
        return False, f"Departamento inválido. Debe ser uno de: {', '.join(DEPARTAMENTOS_VALIDOS)}"
    return True, ""

def validar_turno(turno):
    """Valida si el turno es válido"""
    if turno not in TURNOS_VALIDOS:
        return False, f"Turno inválido. Debe ser uno de: {', '.join(TURNOS_VALIDOS)}"
    return True, ""

def validar_archivo_imagen(foto_path):
    """Valida si el archivo de imagen existe y tiene extensión válida"""
    if not os.path.exists(foto_path):
        return False, f"El archivo {foto_path} no existe"
    
    # Verificar extensión
    extensiones_validas = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    _, extension = os.path.splitext(foto_path.lower())
    
    if extension not in extensiones_validas:
        return False, f"Formato de imagen no válido. Extensiones permitidas: {', '.join(extensiones_validas)}"
    
    return True, ""

def validar_nombre(nombre):
    """Valida si el nombre es válido"""
    if not nombre or len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    if not re.match("^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", nombre.strip()):
        return False, "El nombre solo puede contener letras y espacios"
    
    return True, ""

def validar_apellido(apellido):
    """Valida si el apellido es válido"""
    if not apellido or len(apellido.strip()) < 2:
        return False, "El apellido debe tener al menos 2 caracteres"
    
    if not re.match("^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", apellido.strip()):
        return False, "El apellido solo puede contener letras y espacios"
    
    return True, ""

def validar_empleado_completo(nombre, apellido, departamento, turno, foto_path):
    """Valida todos los datos de un empleado"""
    validaciones = [
        validar_nombre(nombre),
        validar_apellido(apellido),
        validar_departamento(departamento),
        validar_turno(turno),
        validar_archivo_imagen(foto_path)
    ]
    
    errores = []
    for es_valido, mensaje in validaciones:
        if not es_valido:
            errores.append(mensaje)
    
    if errores:
        return False, "; ".join(errores)
    
    return True, "Validación exitosa"

def limpiar_string(texto):
    """Limpia y normaliza strings de entrada"""
    if not texto:
        return ""
    return texto.strip().title()

def es_email_valido(email):
    """Valida formato básico de email"""
    if not email:
        return False, "Email requerido"
    
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron, email):
        return False, "Formato de email inválido"
    
    return True, ""

def validar_rango_horas(hora_inicio, hora_fin):
    """Valida que el rango de horas sea lógico"""
    if hora_inicio >= hora_fin:
        return False, "La hora de inicio debe ser anterior a la hora de fin"
    return True, ""