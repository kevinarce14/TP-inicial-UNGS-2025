from datetime import datetime, timedelta
from ..logica.config import TURNOS, LIMITE_PUNTUAL, LIMITE_MEDIO_TARDE

def determinar_turno_actual():
    """Determina el turno actual basado en la hora"""
    ahora = datetime.now().time()
    hora_actual = ahora.hour + ahora.minute/60
    
    if 7.5 <= hora_actual < 15.5:
        return 'Manana'
    elif 15.5 <= hora_actual < 23.5:
        return 'Tarde'
    else:
        return 'Noche'

def calcular_minutos_tarde(hora_ingreso, turno):
    """Calcula los minutos de tardanza basado en el horario del turno"""
    ahora = datetime.now()
    hora_ingreso_dt = datetime.combine(ahora.date(), hora_ingreso)
    
    if turno == 'Manana':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Manana']['inicio'])
    elif turno == 'Tarde':
        hora_esperada = datetime.combine(ahora.date(), TURNOS['Tarde']['inicio'])
    else:  # Noche
        # El turno de noche puede empezar el día anterior
        if ahora.hour < 12:  # Si estamos en la madrugada
            hora_esperada = datetime.combine(ahora.date() - timedelta(days=1), TURNOS['Noche']['inicio'])
        else:
            hora_esperada = datetime.combine(ahora.date(), TURNOS['Noche']['inicio'])
    
    diferencia = hora_ingreso_dt - hora_esperada
    minutos_tarde = max(0, int(diferencia.total_seconds() / 60))
    return minutos_tarde

def determinar_observacion(minutos_tarde):
    """Determina la observación basada en los minutos de tardanza"""
    if minutos_tarde <= LIMITE_PUNTUAL:
        return 'Puntual'
    elif minutos_tarde <= LIMITE_MEDIO_TARDE:
        return 'Medio Tarde'
    else:
        return 'Muy Tarde'

def is_within_shift_hours(turno, hora_actual=None):
    """Verifica si una hora está dentro del rango del turno"""
    if hora_actual is None:
        hora_actual = datetime.now().time()
    
    turno_info = TURNOS.get(turno)
    if not turno_info:
        return False
    
    inicio = turno_info['inicio']
    fin = turno_info['fin']
    
    # Manejar turnos que cruzan medianoche (como el turno de noche)
    if inicio > fin:  # Turno nocturno
        return hora_actual >= inicio or hora_actual <= fin
    else:
        return inicio <= hora_actual <= fin

def get_shift_duration_minutes(turno):
    """Obtiene la duración del turno en minutos"""
    turno_info = TURNOS.get(turno)
    if not turno_info:
        return 0
    
    inicio = turno_info['inicio']
    fin = turno_info['fin']
    
    # Convertir a minutos desde medianoche
    inicio_mins = inicio.hour * 60 + inicio.minute
    fin_mins = fin.hour * 60 + fin.minute
    
    # Manejar turnos que cruzan medianoche
    if inicio_mins > fin_mins:
        return (24 * 60 - inicio_mins) + fin_mins
    else:
        return fin_mins - inicio_mins

def format_time_duration(minutos):
    """Formatea una duración en minutos a formato legible"""
    if minutos < 60:
        return f"{minutos} minutos"
    else:
        horas = minutos // 60
        mins_restantes = minutos % 60
        if mins_restantes == 0:
            return f"{horas} hora{'s' if horas != 1 else ''}"
        else:
            return f"{horas} hora{'s' if horas != 1 else ''} y {mins_restantes} minutos"