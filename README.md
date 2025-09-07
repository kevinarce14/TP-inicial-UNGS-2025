Prototipo de Control de Ingreso con Reconocimiento Facial

## Requerimientos

* Python 3.12
* opencv-python==4.7.0.72
* numpy
* flask
* Pillow
* imutils

## Instalación

Situados en la raíz del proyecto: 

* pip install -r requirements.txt
* python -m web.app

## Uso
Se puede acceder a la pagina de la aplicacion mediante la instalacion local o mediante el siguente link: https://grupo12.pythonanywhere.com/
Una vez en la pagina de la aplicacion se puede visualizar:
* Tabla de empleados resgistrados
* Tabla de asistencias registradas
* Tabla de denegaciones registradas
* Tabla de produccion 
* Metricas e indicadores respecto a las demás tablas  
* Apartado para agregar un empleado: Se solicita completar todos los campos del formulario. Además, se requiere una fotografía del rostro de
  la persona que se va a registrar, la cual se capturará automáticamente. Una vez que la imagen sea capturada correctamente, el empleado será registrado en el sistema.
