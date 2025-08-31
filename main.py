import threading
import cv2
import face_recognition
import os
import time

# ------------------------------
# CONFIGURACIÓN
# ------------------------------
KNOWN_FACES_DIR = 'known_faces'
TOLERANCE = 0.6
FRAME_THICKNESS = 3
FONT_THICKNESS = 2
MODEL = 'hog'  # 'hog' en CPU, 'cnn' con GPU CUDA

print("Cargando imágenes conocidas...")

known_faces = []
known_names = []

for name in os.listdir(KNOWN_FACES_DIR):
    for filename in os.listdir(f"{KNOWN_FACES_DIR}/{name}"):
        image = face_recognition.load_image_file(f"{KNOWN_FACES_DIR}/{name}/{filename}")
        encoding = face_recognition.face_encodings(image)[0]
        known_faces.append(encoding)
        known_names.append(name)

print("Listo! Iniciando cámara...")

# ------------------------------
# VARIABLES COMPARTIDAS ENTRE HILOS
# ------------------------------
frame_lock = threading.Lock()
current_frame = None
current_results = []

# Para reutilizar encodings previos
last_matches = []  # [(nombre, (top,right,bottom,left)), ...]

def same_face(loc1, loc2, threshold=50):
    """Compara si dos caras están cerca en píxeles"""
    return abs(loc1[0] - loc2[0]) < threshold and abs(loc1[1] - loc2[1]) < threshold

# ------------------------------
# HILO DE CAPTURA
# ------------------------------
def capture_thread():
    global current_frame
    video = cv2.VideoCapture(0)
    video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = video.read()
        if not ret:
            break
        with frame_lock:
            current_frame = frame.copy()
    video.release()

# ------------------------------
# HILO DE RECONOCIMIENTO
# ------------------------------
def recognition_thread():
    global current_frame, current_results, last_matches
    while True:
        time.sleep(0.05)  # evita uso 100% CPU

        with frame_lock:
            if current_frame is None:
                continue
            frame = current_frame.copy()

        # Redimensionar para acelerar
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Detectar ubicaciones
        face_locations = face_recognition.face_locations(small_frame, model=MODEL)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        # Escalar ubicaciones al tamaño original
        face_locations = [(t*4, r*4, b*4, l*4) for (t, r, b, l) in face_locations]

        current_matches = []

        for face_encoding, face_location in zip(face_encodings, face_locations):
            match = None

            # Reutilizar coincidencia anterior si la cara está cerca
            for last_name, last_loc in last_matches:
                if same_face(face_location, last_loc):
                    match = last_name
                    break

            # Si no estaba, comparar contra base de datos
            if match is None:
                results = face_recognition.compare_faces(known_faces, face_encoding, TOLERANCE)
                if True in results:
                    match = known_names[results.index(True)]
                    print(f"Rostro reconocido: {match}")

            current_matches.append((match, face_location))

        # Actualizar variables compartidas
        with frame_lock:
            current_results = current_matches
            last_matches = current_matches.copy()

# ------------------------------
# INICIO DE HILOS
# ------------------------------
threading.Thread(target=capture_thread, daemon=True).start()
threading.Thread(target=recognition_thread, daemon=True).start()

# ------------------------------
# BUCLE PRINCIPAL DE VISUALIZACIÓN
# ------------------------------
while True:
    with frame_lock:
        if current_frame is None:
            continue
        frame = current_frame.copy()
        results = current_results.copy()

    # Dibujar resultados
    for name, (top, right, bottom, left) in results:
        color = (0, 255, 0) if name else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, FRAME_THICKNESS)
        if name:
            cv2.putText(frame, name, (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, FONT_THICKNESS)

    cv2.imshow("Reconocimiento Facial (Optimizado)", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
