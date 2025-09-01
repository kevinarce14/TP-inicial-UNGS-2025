-- SQLite
delete from asistencias where ID_Asistencia = 1;
delete from asistencias where ID_Asistencia = 2;
delete from asistencias where ID_Asistencia = 3;
delete from asistencias where ID_Asistencia = 4;
delete from asistencias where ID_Asistencia = 5;
delete from asistencias where ID_Asistencia = 2;
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (1, "2025-09-01", 3, "Noche", "01:00:13", null, 1, 0, "Puntual");
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (2, "2025-09-01", 6, "Noche", "01:07:40", null, 1, 7, "Puntual");
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (3, "2025-09-01", 1, "Noche", "01:33:03", null, 1, 33, "Muy Tarde");
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (4, "2025-09-01", 4, "Mañana", "07:30:09", null, 1, 0, "Puntual");
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (5, "2025-09-01", 5, "Mañana", "07:31:20", null, 1, 1, "Puntual");
INSERT INTO asistencias (ID_Asistencia, Fecha, ID_Empleado, Turno, Hora_Ingreso, Hora_Egreso, Estado_Asistencia, Minutos_Tarde ,Observacion) VALUES (6, "2025-09-01", 2, "Tarde", "15:11:47", null, 1, 11, "Tarde");
select * from asistencias;

select * from empleados;