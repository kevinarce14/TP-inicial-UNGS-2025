## Prototipo de Control de Ingreso con Reconocimiento Facial

## Requerimientos
| Librería             | Versión recomendada | Uso                               |
| -------------------- | ------------------- | --------------------------------- |
| Python               | 3.10 o 3.11         | Base del proyecto                 |
| opencv-python        | 4.7.0.72            | Procesamiento de imágenes y video |
| dlib                 | 19.24.1             | Detección de rostros y landmarks  |
| face-recognition     | 1.3.0               | Reconocimiento facial sobre dlib  |
| numpy                | 1.26.0              | Manejo de matrices e imágenes     |
| Pillow               | 10.0.0              | Manipulación de imágenes          |
| imutils              | 0.5.4               | Funciones auxiliares para OpenCV  |
| flask                | 2.3.2               | Aplicaciones web en Python        |

## Instalación

En la terminal, situados en la raíz del proyecto ejecutar los siguientes comando: 

Crear un entorno virtual (solo la primera vez):
* python -m venv venv

Dar permisos para ejecutar scripts en PowerShell (solo la primera vez):
* Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Activá tu entorno virtual con el comando:
* .\venv\Scripts\Activate.ps1

Instalá todas las dependencias (solo la primera vez):
* pip install -r requirements.txt

Ejecutá la aplicación web:
* python -m web.app

Ejecutar la aplicación de escritorio:
* python -m main.py

## Uso de la pagina de la aplicacion
Se puede acceder a la pagina de la aplicacion mediante la instalacion local o mediante el siguente link: https://grupo12.pythonanywhere.com/
Una vez en la pagina de la aplicacion se puede visualizar:
* Tabla de empleados resgistrados:
 <img width="1305" height="579" alt="image" src="https://github.com/user-attachments/assets/6bf31dd4-24fe-460c-8975-7e57c565dbd2" />
* Tabla de asistencias registradas
  <img width="1320" height="648" alt="image" src="https://github.com/user-attachments/assets/4de28c00-7e31-4a26-9314-daa440b0b6f3" />
* Tabla de denegaciones registradas
  <img width="1316" height="611" alt="image" src="https://github.com/user-attachments/assets/97061d1b-1c64-4d2a-943c-0dd331d162bb" />
* Tabla de produccion
 <img width="1348" height="576" alt="image" src="https://github.com/user-attachments/assets/51a881e0-63c3-457d-88d2-bd6eb27df8f1" />
* Metricas e indicadores respecto a las demás tablas
  <img width="1723" height="617" alt="image" src="https://github.com/user-attachments/assets/6867bd35-0c70-4f64-8b2e-152ccad50317" />
* Apartado para agregar un empleado
  <img width="937" height="433" alt="image" src="https://github.com/user-attachments/assets/c395ff83-0007-4b5e-af96-39665649cdaf" />

  Se solicita completar todos los campos del formulario. Además, se requiere una fotografía del rostro de
  la persona que se va a registrar, la cual se capturará automáticamente. Una vez que la imagen sea capturada correctamente, el empleado será registrado en el sistema.

## Uso del prototipo de Control de Ingreso/Egreso con Reconocimiento Facial
Situados en la raíz del proyecto: 

Comandos:

     python main.py --mode entry    : Modo ingreso (por defecto)
     python main.py --mode exit     : Modo egreso  

