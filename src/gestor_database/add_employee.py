import sqlite3
import face_recognition
import numpy as np
import os

def agregar_empleado(nombre, apellido, departamento, turno, foto_path):
    # Validar departamento
    departamentos_validos = ['Administración', 'Ventas', 'Producción', 'Recursos Humanos']
    if departamento not in departamentos_validos:
        print(f"Departamento inválido. Debe ser uno de: {', '.join(departamentos_validos)}")
        return False
    
    # Validar turno
    turnos_validos = ['Mañana', 'Tarde', 'Noche']
    if turno not in turnos_validos:
        print(f"Turno inválido. Debe ser uno de: {', '.join(turnos_validos)}")
        return False
    
    # Verificar que el archivo existe
    if not os.path.exists(foto_path):
        print(f"El archivo {foto_path} no existe")
        return False
    
    # Cargar y codificar la imagen
    image = face_recognition.load_image_file(foto_path)
    encodings = face_recognition.face_encodings(image)
    
    if not encodings:
        print(f"No se pudo detectar un rostro en {foto_path}")
        return False
    
    # Guardar como float32 para evitar errores de dimensión
    encoding_blob = encodings[0].astype(np.float32).tobytes()
    
    # Conectar a la base de datos y guardar
    conn = sqlite3.connect('asistencia_empleados.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO empleados (Nombre, Apellido, Departamento, Turno, Foto_Path, Embedding)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (nombre, apellido, departamento, turno, foto_path, encoding_blob))
    
    conn.commit()
    conn.close()
    
    print(f"Empleado {nombre} {apellido} agregado exitosamente!")
    return True

if __name__ == "__main__":
    # Ejemplo de uso
    agregar_empleado(
        nombre="Kevin",
        apellido="Arce",
        departamento="Producción",
        turno="Tarde",
        foto_path="imagenes_empleados/Kevin.png"
    )
