from machine import Pin
import time

# =========================================================================
# CONFIGURACIÓN DE LÓGICA DE LOS RELEVADORES
# =========================================================================
RELE_ENCENDIDO = False
RELE_APAGADO = not RELE_ENCENDIDO

# Mapeo de Pines (Índices: 0=Blanco, 1=Azul, 2=Verde, 3=Amarillo, 4=Rojo)
LED_PINS = [13, 25, 14, 27, 26] 

# Inicializar todos los relevadores en APAGADO
leds = [Pin(p, Pin.OUT, value=RELE_APAGADO) for p in LED_PINS]

def set_leds(index, estado_deseado):
    """Enciende (1) o apaga (0) el relé"""
    if estado_deseado == 1:
        leds[index].value(RELE_ENCENDIDO)
    else:
        leds[index].value(RELE_APAGADO)

# Configuración de Botones
op_req_cal_btn    = Pin(15, Pin.IN, Pin.PULL_UP) 
op_req_mant_btn   = Pin(2,  Pin.IN, Pin.PULL_UP) 
tec_cal_help_btn  = Pin(4,  Pin.IN, Pin.PULL_UP) 
tec_mant_help_btn = Pin(16, Pin.IN, Pin.PULL_UP)

# Variables de Estado
estado_calidad = False       # False = Apagado, True = Azul
estado_mantenimiento = False # False = Apagado, True = Amarillo
estado_tecnico = False       # True = Parpadeando rojo

# Variables para el parpadeo NO BLOQUEANTE (Millis)
ultimo_parpadeo = time.ticks_ms()
estado_luz_parpadeo = False
INTERVALO_PARPADEO = 500 # Tiempo en milisegundos para el parpadeo

def actualizar_luces():
    """Actualiza la torre Andon según las prioridades del sistema"""
    # Si el técnico está activo, tiene prioridad de parpadeo (Rojo)
    # Pero respetamos los estados de los demás leds
    set_leds(1, 1 if estado_calidad else 0)
    
    # Lógica de Mantenimiento / Verde
    if estado_mantenimiento:
        set_leds(3, 1) # Amarillo encendido
        set_leds(2, 0) # Verde apagado
    else:
        set_leds(3, 0) # Amarillo apagado
        # El verde se enciende si mantenimiento está apagado y calidad no está activa
        if not estado_calidad:
            set_leds(2, 1)
        else:
            set_leds(2, 0)

# Estado inicial: Operación normal (Verde encendido)
actualizar_luces()

while True:
    tiempo_actual = time.ticks_ms()
    hubo_cambio = False


    # 1. Botón Calidad -> Enciende Azul fijo
    if not op_req_cal_btn.value():
        if not estado_calidad:
            estado_calidad = True
            estado_tecnico = False # Al oprimir otro, apaga técnico
            hubo_cambio = True
            print("[BOTÓN] Calidad Activa (Azul)")
        time.sleep(0.2) # Antirebote

    # 2. Botón Mantenimiento -> Toggle (Amarillo / Verde)
    if not op_req_mant_btn.value():
        estado_mantenimiento = not estado_mantenimiento # Cambia de estado
        estado_tecnico = False # Al oprimir otro, apaga técnico
        hubo_cambio = True
        print(f"[BOTÓN] Mantenimiento cambiado a: {estado_mantenimiento}")
        time.sleep(0.2)

    # 3. Botones de Técnico (Calidad o Mantenimiento) -> Toggle Parpadeo Rojo
    if not tec_cal_help_btn.value() or not tec_mant_help_btn.value():
        estado_tecnico = not estado_tecnico # Toggle parpadeo
        hubo_cambio = True
        if not estado_tecnico:
            set_leds(4, 0) # Asegurar que se apague el rojo al desactivar
        print(f"[BOTÓN] Estado Técnico (Parpadeo): {estado_tecnico}")
        time.sleep(0.2)

    if estado_tecnico:
        if time.ticks_diff(tiempo_actual, ultimo_parpadeo) >= INTERVALO_PARPADEO:
            estado_luz_parpadeo = not estado_luz_parpadeo
            set_leds(4, 1 if estado_luz_parpadeo else 0) # Parpadea el led Rojo
            ultimo_parpadeo = tiempo_actual
    else:
        set_leds(4, 0) # Forzar apagado de led de técnico si está inactivo

    if hubo_cambio:
        actualizar_luces()

    time.sleep(0.01) # Mini pausa para estabilidad
