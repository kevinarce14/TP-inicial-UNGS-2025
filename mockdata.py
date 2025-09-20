import psycopg2
import random
from datetime import datetime, timedelta
import numpy as np

DB_CONFIG = {
    'host': "ep-wispy-breeze-acjxjbvm-pooler.sa-east-1.aws.neon.tech",
    'port': 5432,
    'dbname': "neondb",
    'user': "neondb_owner",
    'password': "npg_gRD2wkVuvYH4",
    'sslmode': "require"
}

PRODUCTOS = [
    'Leche Entera','Queso Fresco','Manteca','Dulce de Leche',
    'Queso Untable','Flan','Yogur'
]

NOMBRES = ['Juan','Maria','Carlos','Laura','Pedro','Ana','Luis','Elena','Miguel','Sofia']
APELLIDOS = ['Garcia','Rodriguez','Gonzalez','Fernandez','Lopez','Martinez','Sanchez','Perez']
DEPARTAMENTOS = ['Administración','Ventas','Producción','Recursos Humanos']
TURNOS = ['Manana','Tarde','Noche']

HORARIOS_TURNOS = {
    'Manana': {'entrada':'07:30:00','salida':'15:30:00'},
    'Tarde': {'entrada':'15:30:00','salida':'23:30:00'},
    'Noche': {'entrada':'23:30:00','salida':'07:30:00'}
}

PROB_INASISTENCIA = {'Manana':0.15,'Tarde':0.08,'Noche':0.20}

def conectar_db():
    return psycopg2.connect(**DB_CONFIG)

def crear_empleados(conn, cantidad=20):
    cur = conn.cursor()
    empleados = []
    for _ in range(cantidad):
        nombre = random.choice(NOMBRES)
        apellido = random.choice(APELLIDOS)
        depto = random.choice(DEPARTAMENTOS)
        turno = random.choice(TURNOS)
        embedding = np.zeros(128, dtype=np.float32).tobytes()
        cur.execute("""
            INSERT INTO empleados (nombre, apellido, departamento, turno, foto_path, embedding)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id_empleado, nombre, apellido, turno
        """,(nombre,apellido,depto,turno,f"{nombre.lower()}_{apellido.lower()}.png",embedding))
        row = cur.fetchone()
        empleados.append({'id':row[0],'nombre':row[1],'apellido':row[2],'turno':row[3]})
    conn.commit()
    return empleados

def calcular_metricas(produccion_real, produccion_buena, produccion_defectuosa, tiempo_planificado, tiempo_paradas):
    tiempo_operativo = tiempo_planificado - tiempo_paradas
    disponibilidad = (tiempo_operativo / tiempo_planificado) * 100 if tiempo_planificado > 0 else 0
    rendimiento = (produccion_real / ((tiempo_operativo/60)*100))*100 if tiempo_operativo>0 and produccion_real>0 else 0
    calidad = (produccion_buena/produccion_real)*100 if produccion_real>0 else 0
    oee = (disponibilidad/100) * (rendimiento/100) * (calidad/100) * 100
    return tiempo_operativo, oee, disponibilidad, rendimiento, calidad

def generar_datos(conn, empleados, dias=30):
    fecha_fin=datetime.now().date()
    fecha_inicio=fecha_fin-timedelta(days=dias)

    cur_asist = conn.cursor()
    cur_prod = conn.cursor()

    asistencias = []
    producciones = []

    for i in range(dias):
        fecha=fecha_inicio+timedelta(days=i)
        if fecha.weekday()>=5:  # saltear sábados y domingos
            continue

        # asistencias
        for emp in empleados:
            turno = emp['turno']
            if random.random()<PROB_INASISTENCIA[turno]:
                asistencias.append((
                    fecha, emp['id'], turno, None, None, False, None, 'Ausente'
                ))
            else:
                minutos_tarde = random.randint(0,30)
                hora_ingreso = (datetime.strptime(HORARIOS_TURNOS[turno]['entrada'],'%H:%M:%S')
                                + timedelta(minutes=minutos_tarde)).time()
                hora_egreso = HORARIOS_TURNOS[turno]['salida']
                if minutos_tarde<=10: obs="Puntual"
                elif minutos_tarde<=30: obs="Medio Tarde"
                else: obs="Muy Tarde"
                asistencias.append((
                    fecha, emp['id'], turno, hora_ingreso, hora_egreso, True, minutos_tarde, obs
                ))

        # producción
        for _ in range(random.randint(3,6)):
            turno=random.choice(TURNOS)
            producto=random.choice(PRODUCTOS)
            if turno=='Manana':
                produccion_real=random.randint(300,500)
                defectuosa=random.randint(40,80)
                tiempo_plan=480
                tiempo_par=random.randint(120,180)
            elif turno=='Tarde':
                produccion_real=random.randint(600,800)
                defectuosa=random.randint(10,30)
                tiempo_plan=480
                tiempo_par=random.randint(30,60)
            else:
                produccion_real=random.randint(400,600)
                defectuosa=random.randint(30,60)
                tiempo_plan=480
                tiempo_par=random.randint(60,120)

            buena = produccion_real - defectuosa
            t_op, oee, disp, rend, cal = calcular_metricas(produccion_real, buena, defectuosa, tiempo_plan, tiempo_par)

            producciones.append((
                fecha, turno, random.choice(empleados)['id'], producto,
                produccion_real, buena, defectuosa, tiempo_plan, tiempo_par,
                t_op, oee, disp, rend, cal, None
            ))

    # insertar en batch
    cur_asist.executemany("""
        INSERT INTO asistencias
        (fecha,id_empleado,turno,hora_ingreso,hora_egreso,estado_asistencia,minutos_tarde,observacion)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, asistencias)

    cur_prod.executemany("""
        INSERT INTO production
        (fecha,turno,id_empleado,producto,produccion_real,produccion_buena,produccion_defectuosa,
         tiempo_planificado,tiempo_paradas,tiempo_operativo,oee,disponibilidad,rendimiento,calidad,observaciones)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, producciones)

    conn.commit()

def main():
    conn = conectar_db()
    empleados = crear_empleados(conn, cantidad=20)
    generar_datos(conn, empleados, dias=30)
    conn.close()
    print("✅ Datos generados con éxito en PostgreSQL")

if __name__=="__main__":
    main()
