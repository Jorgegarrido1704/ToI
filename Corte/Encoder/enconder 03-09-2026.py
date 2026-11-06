from machine import Pin
import time

# =========================================================================
# CONFIGURACION DE LOGICA DE LOS RELEVADORES
# =========================================================================
RELE_ENCENDIDO = False
RELE_APAGADO = not RELE_ENCENDIDO

# Mapeo de Pines (Indices: 0=Blanco, 1=Azul, 2=Verde, 3=Amarillo, 4=Rojo)
LED_PINS = [13, 14,27, 26, 25]

# Inicializar todos los relevadores en APAGADO
leds = [Pin(p, Pin.OUT, value=1) for p in LED_PINS]

# Configuracion de Botones (PULL_UP -> presionado = 0)
op_req_cal_btn    = Pin(15, Pin.IN, Pin.PULL_DOWN)
op_req_mant_btn   = Pin(2,  Pin.IN, Pin.PULL_DOWN)
tec_cal_help_btn  = Pin(19,  Pin.IN, Pin.PULL_DOWN)
tec_mant_help_btn = Pin(21, Pin.IN, Pin.PULL_DOWN)

# Estados de las areas
ope_cal = True
ope_mant = True
tec_cal = True
tec_mant = True

# Estado anterior de cada boton, para detectar flanco de bajada (pulsacion)
prev_op_cal = 1
prev_op_mant = 1
prev_tec_cal = 1
prev_tec_mant = 1

# Variables para el parpadeo NO BLOQUEANTE (Millis) -- no usadas aun,
# quedan listas si luego quieres pasar el parpadeo a no bloqueante
ultimo_parpadeo = time.ticks_ms()
INTERVALO_PARPADEO = 50  # ms


def parpadeo(accion):
    if accion == 0:
        leds[2].value(1)
        leds[1].value(0)
        leds[3].value(0)
        leds[4].value(0)
        leds[0].value(0)
        
    elif accion == 1:  # operador Calidad
        leds[2].value(0)
        leds[4].value(1)
        leds[1].value(1)
        leds[3].value(0)
        leds[0].value(0)
        time.sleep(1)
        leds[1].value(0)
        leds[4].value(0)
    elif accion == 2:  # tecnico Calidad
        leds[4].value(1)
        leds[1].value(1)
        leds[3].value(0)
        leds[0].value(0)
        leds[2].value(0)
    elif accion == 3:  # operador mantenimiento
        leds[2].value(0)
        leds[4].value(1)
        leds[3].value(1)
        leds[0].value(0)
        leds[1].value(0)
        time.sleep(1)
        leds[4].value(0)
        leds[3].value(0)
    elif accion == 4:  # tecnico mantenimiento
        leds[4].value(1)
        leds[3].value(1)
        leds[0].value(0)
        leds[1].value(0)
        leds[2].value(0)


accion = 0

while True:
    # --- Lectura de botones ---
    actual_op_cal = op_req_cal_btn.value()
    actual_op_mant = op_req_mant_btn.value()
    actual_tec_cal = tec_cal_help_btn.value()
    actual_tec_mant = tec_mant_help_btn.value()
    

    # --- Boton Operador Calidad: dispara solo en flanco de bajada (1 -> 0) ---
    if prev_op_cal == 1 and actual_op_cal == 0:
        if ope_cal:
            accion = 0
            ope_cal = False
            print("bien")
        else:
            accion = 1
            ope_cal = True
            print("Llamada opt cal")

    # --- Boton Operador Mantenimiento ---
    if prev_op_mant == 1 and actual_op_mant == 0:
        if ope_mant:
            accion = 0
            ope_mant = False
            print("bien")
        else:
            accion = 3
            ope_mant = True
            print("Llamada opt mant")

    # --- Boton Tecnico Calidad ---
    if prev_tec_cal == 1 and actual_tec_cal == 0:
        if tec_cal:
            accion = 0
            tec_cal = False
            print("bien")
        else:
            accion = 2
            tec_cal = True
            print("Llamada tec cal")

    # --- Boton Tecnico Mantenimiento ---
    if prev_tec_mant == 1 and actual_tec_mant == 0:
        if tec_mant:
            accion = 0
            tec_mant = False
            print("bien")
        else:
            accion = 4
            tec_mant = True
            print("Llamada tec mant")

    # Guardar estado actual como "anterior" para la siguiente vuelta
    prev_op_cal = actual_op_cal
    prev_op_mant = actual_op_mant
    prev_tec_cal = actual_tec_cal
    prev_tec_mant = actual_tec_mant

    parpadeo(accion)
    time.sleep(0.02)  

