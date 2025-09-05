from datetime import datetime, timedelta
from ..logica.config import (
    TASA_IDEAL_PRODUCCION, OEE_EXCELENTE, OEE_BUENO, 
    OEE_REGULAR, COLOR_OEE_EXCELENTE, COLOR_OEE_BUENO, 
    COLOR_OEE_REGULAR, COLOR_OEE_DEFICIENTE
)

def calcular_oee_manual(produccion_real, produccion_buena, tiempo_planificado, tiempo_paradas):
    """
    Calcula manualmente el OEE y sus componentes
    
    Args:
        produccion_real (int): Total de unidades producidas
        produccion_buena (int): Unidades buenas producidas  
        tiempo_planificado (int): Tiempo planificado en minutos
        tiempo_paradas (int): Tiempo de paradas en minutos
        
    Returns:
        dict: Diccionario con OEE y sus componentes
    """
    if tiempo_planificado <= 0 or produccion_real <= 0:
        return {
            'oee': 0,
            'disponibilidad': 0,
            'rendimiento': 0,
            'calidad': 0,
            'tiempo_operativo': 0
        }
    
    # Tiempo operativo en minutos
    tiempo_operativo = tiempo_planificado - tiempo_paradas
    
    if tiempo_operativo <= 0:
        return {
            'oee': 0,
            'disponibilidad': 0,
            'rendimiento': 0, 
            'calidad': 0,
            'tiempo_operativo': 0
        }
    
    # Cálculos de componentes OEE
    disponibilidad = (tiempo_operativo / tiempo_planificado) * 100
    
    # Rendimiento basado en tasa ideal (100 unidades/hora)
    tiempo_operativo_horas = tiempo_operativo / 60.0
    produccion_teorica = tiempo_operativo_horas * TASA_IDEAL_PRODUCCION
    rendimiento = (produccion_real / produccion_teorica) * 100 if produccion_teorica > 0 else 0
    
    calidad = (produccion_buena / produccion_real) * 100
    
    # OEE total
    oee = (disponibilidad / 100) * (rendimiento / 100) * (calidad / 100) * 100
    
    return {
        'oee': round(oee, 2),
        'disponibilidad': round(disponibilidad, 2),
        'rendimiento': round(rendimiento, 2),
        'calidad': round(calidad, 2),
        'tiempo_operativo': tiempo_operativo
    }

def clasificar_oee(valor_oee):
    """
    Clasifica un valor OEE en categorías
    
    Args:
        valor_oee (float): Valor OEE a clasificar
        
    Returns:
        tuple: (categoria, color)
    """
    if valor_oee >= OEE_EXCELENTE:
        return ('Excelente', COLOR_OEE_EXCELENTE)
    elif valor_oee >= OEE_BUENO:
        return ('Bueno', COLOR_OEE_BUENO)
    elif valor_oee >= OEE_REGULAR:
        return ('Regular', COLOR_OEE_REGULAR)
    else:
        return ('Deficiente', COLOR_OEE_DEFICIENTE)

def validar_datos_produccion(produccion_real, produccion_buena, produccion_defectuosa, 
                           tiempo_planificado, tiempo_paradas):
    """
    Valida los datos de producción antes de registrar
    
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    errores = []
    
    # Validar que todos los valores sean números positivos o cero
    if produccion_real < 0:
        errores.append("La producción real no puede ser negativa")
    
    if produccion_buena < 0:
        errores.append("La producción buena no puede ser negativa")
        
    if produccion_defectuosa < 0:
        errores.append("La producción defectuosa no puede ser negativa")
    
    if tiempo_planificado <= 0:
        errores.append("El tiempo planificado debe ser mayor a 0")
        
    if tiempo_paradas < 0:
        errores.append("El tiempo de paradas no puede ser negativo")
    
    # Validar que producción buena + defectuosa = real
    if produccion_buena + produccion_defectuosa != produccion_real:
        errores.append("La suma de producción buena y defectuosa debe igual a producción real")
    
    # Validar que tiempo paradas <= tiempo planificado
    if tiempo_paradas > tiempo_planificado:
        errores.append("El tiempo de paradas no puede ser mayor al tiempo planificado")
    
    if errores:
        return False, "; ".join(errores)
    
    return True, "Validación exitosa"

def calcular_perdidas_oee(oee_actual, produccion_real, tiempo_planificado, tiempo_paradas):
    """
    Calcula las pérdidas potenciales basadas en el OEE
    
    Returns:
        dict: Diccionario con análisis de pérdidas
    """
    tiempo_operativo = tiempo_planificado - tiempo_paradas
    tiempo_operativo_horas = tiempo_operativo / 60.0
    
    # Producción máxima teórica (100% OEE)
    produccion_maxima_teorica = tiempo_operativo_horas * TASA_IDEAL_PRODUCCION
    
    # Pérdidas
    perdida_por_disponibilidad = (tiempo_paradas / 60.0) * TASA_IDEAL_PRODUCCION
    perdida_por_rendimiento = produccion_maxima_teorica - produccion_real
    
    # Calcular producción defectuosa (asumiendo que existe)
    componentes_oee = calcular_oee_manual(produccion_real, produccion_real, tiempo_planificado, tiempo_paradas)
    calidad_actual = componentes_oee['calidad']
    produccion_buena_estimada = (calidad_actual / 100) * produccion_real
    perdida_por_calidad = produccion_real - produccion_buena_estimada
    
    return {
        'produccion_maxima_teorica': round(produccion_maxima_teorica, 0),
        'perdida_por_disponibilidad': round(perdida_por_disponibilidad, 0),
        'perdida_por_rendimiento': round(max(0, perdida_por_rendimiento), 0),
        'perdida_por_calidad': round(perdida_por_calidad, 0),
        'produccion_perdida_total': round(produccion_maxima_teorica - produccion_buena_estimada, 0)
    }

def generar_reporte_resumen(datos_produccion):
    """
    Genera un resumen estadístico de datos de producción
    
    Args:
        datos_produccion (list): Lista de tuplas con datos de producción
        
    Returns:
        dict: Resumen estadístico
    """
    if not datos_produccion:
        return {
            'total_registros': 0,
            'oee_promedio': 0,
            'produccion_total': 0,
            'mejor_oee': 0,
            'peor_oee': 0
        }
    
    # Extraer valores (asumiendo que OEE está en posición específica)
    oees = []
    produccion_total = 0
    
    for registro in datos_produccion:
        # Adaptar índices según estructura real de datos
        if len(registro) > 10:  # Asegurar que tiene datos suficientes
            oee = registro[10] if registro[10] is not None else 0  # Posición del OEE
            produccion = registro[5] if registro[5] is not None else 0  # Producción real
            
            oees.append(oee)
            produccion_total += produccion
    
    if not oees:
        return {
            'total_registros': len(datos_produccion),
            'oee_promedio': 0,
            'produccion_total': produccion_total,
            'mejor_oee': 0,
            'peor_oee': 0
        }
    
    return {
        'total_registros': len(datos_produccion),
        'oee_promedio': round(sum(oees) / len(oees), 2),
        'produccion_total': produccion_total,
        'mejor_oee': round(max(oees), 2),
        'peor_oee': round(min(oees), 2),
        'registros_excelentes': len([oee for oee in oees if oee >= OEE_EXCELENTE]),
        'registros_buenos': len([oee for oee in oees if OEE_BUENO <= oee < OEE_EXCELENTE]),
        'registros_regulares': len([oee for oee in oees if OEE_REGULAR <= oee < OEE_BUENO]),
        'registros_deficientes': len([oee for oee in oees if oee < OEE_REGULAR])
    }

def formatear_tiempo_minutos(minutos):
    """Convierte minutos a formato HH:MM"""
    horas = minutos // 60
    mins = minutos % 60
    return f"{horas:02d}:{mins:02d}"

def calcular_fechas_periodo(periodo='mes_actual'):
    """
    Calcula fechas de inicio y fin para diferentes períodos
    
    Args:
        periodo (str): 'hoy', 'semana_actual', 'mes_actual', 'ultimos_30_dias'
        
    Returns:
        tuple: (fecha_inicio, fecha_fin)
    """
    hoy = datetime.now().date()
    
    if periodo == 'hoy':
        return hoy, hoy
    elif periodo == 'semana_actual':
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        return inicio_semana, hoy
    elif periodo == 'mes_actual':
        inicio_mes = hoy.replace(day=1)
        return inicio_mes, hoy
    elif periodo == 'ultimos_30_dias':
        inicio_30_dias = hoy - timedelta(days=30)
        return inicio_30_dias, hoy
    else:
        return hoy, hoy