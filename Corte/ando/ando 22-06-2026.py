from machine import Pin
import time

# =========================================================================
# CONFIGURACIÓN DE LÓGICA DE LOS RELEVADORES
# =========================================================================
RELE_ENCENDIDO = False
RELE_APAGADO = not RELE_ENCENDIDO

# Mapeo de Pines (Índices: 0=Blanco, 1=Azul, 2=Verde, 3=Amarillo, 4=Rojo)
LED_PINS = [13, 14, 27, 26, 25]
BLANCO, AZUL, VERDE, AMARILLO, ROJO = 0, 1, 2, 3, 4

leds = [Pin(p, Pin.OUT, value=RELE_APAGADO) for p in LED_PINS]

def set_led(indice, encendido):
    """Enciende (True) o apaga (False) el relé/LED."""
    leds[indice].value(RELE_ENCENDIDO if encendido else RELE_APAGADO)

# =========================================================================
# BOTONES
# =========================================================================
op_req_cal_btn    = Pin(15, Pin.IN, Pin.PULL_UP)
op_req_mant_btn   = Pin(16, Pin.IN, Pin.PULL_UP)
tec_cal_help_btn  = Pin(21, Pin.IN, Pin.PULL_DOWN)
tec_mant_help_btn = Pin(19, Pin.IN, Pin.PULL_DOWN)

ANTIREBOTE_MS = 150

class Boton:
    """Botón con antirebote y detección de flanco, sin bloquear el loop."""
    def __init__(self, pin, pull_up=True):
        self.pin = pin
        self.ultimo_cambio = 0
        self.pull_up = pull_up
        self.estado_anterior = 1 if pull_up else 0  # reposo

    def presionado(self):
        """Devuelve True solo en el instante en que se detecta la pulsación."""
        ahora = time.ticks_ms()
        actual = self.pin.value()
        if actual != self.estado_anterior and time.ticks_diff(ahora, self.ultimo_cambio) > ANTIREBOTE_MS:
            self.ultimo_cambio = ahora
            self.estado_anterior = actual
            if self.pull_up:
                return actual == 0  # presionado = LOW
            else:
                return actual == 1  # presionado = HIGH
        if actual != self.estado_anterior:
            self.estado_anterior = actual
        return False

btn_op_cal   = Boton(op_req_cal_btn,   pull_up=True)
btn_op_mant  = Boton(op_req_mant_btn,  pull_up=True)
btn_tec_cal  = Boton(tec_cal_help_btn, pull_up=False)
btn_tec_mant = Boton(tec_mant_help_btn,pull_up=False)

# =========================================================================
# ESTADOS
# =========================================================================
estado_calidad = False         # Azul fijo solicitado por operador
estado_mantenimiento = False   # Amarillo fijo solicitado por operador
estado_tecnico_calidad = False # Técnico atendiendo calidad (parpadeo)
estado_tecnico_mant = False    # Técnico atendiendo mantenimiento (parpadeo)

# --- Parpadeo no bloqueante, INDEPENDIENTE para cada luz ---
INTERVALO_PARPADEO = 500  # ms

ultimo_parpadeo_azul = time.ticks_ms()
azul_blink_on = False

ultimo_parpadeo_amarillo = time.ticks_ms()
amarillo_blink_on = False

def actualizar_parpadeo_azul():
    global ultimo_parpadeo_azul, azul_blink_on
    ahora = time.ticks_ms()
    if time.ticks_diff(ahora, ultimo_parpadeo_azul) >= INTERVALO_PARPADEO:
        ultimo_parpadeo_azul = ahora
        azul_blink_on = not azul_blink_on
        set_led(AZUL, azul_blink_on)

def actualizar_parpadeo_amarillo():
    global ultimo_parpadeo_amarillo, amarillo_blink_on
    ahora = time.ticks_ms()
    if time.ticks_diff(ahora, ultimo_parpadeo_amarillo) >= INTERVALO_PARPADEO:
        ultimo_parpadeo_amarillo = ahora
        amarillo_blink_on = not amarillo_blink_on
        set_led(AMARILLO, amarillo_blink_on)

# Estado inicial: todo apagado, verde encendido (sistema OK)
set_led(VERDE, True)

while True:
    # --- AZUL: parpadeo si hay técnico atendiendo, fijo si solo el operador pidió, apagado si nada ---
    if estado_tecnico_calidad:
        actualizar_parpadeo_azul()
    elif estado_calidad:
        set_led(AZUL, True)
    else:
        set_led(AZUL, False)
        azul_blink_on = False

    # --- AMARILLO: igual lógica que el azul ---
    if estado_tecnico_mant:
        actualizar_parpadeo_amarillo()
    elif estado_mantenimiento:
        set_led(AMARILLO, True)
    else:
        set_led(AMARILLO, False)
        amarillo_blink_on = False

    # --- VERDE / ROJO: dependen del estado GLOBAL, no de un solo evento ---
    hay_algo_activo = (estado_calidad or estado_mantenimiento or
                        estado_tecnico_calidad or estado_tecnico_mant)
    set_led(ROJO, hay_algo_activo)
    set_led(VERDE, not hay_algo_activo)

    # --- Botón Calidad -> Toggle Azul fijo ---
    if btn_op_cal.presionado():
        estado_calidad = not estado_calidad
        print("op_cal" if estado_calidad else "opx_cal")

    # --- Botón Mantenimiento -> Toggle Amarillo fijo ---
    if btn_op_mant.presionado():
        estado_mantenimiento = not estado_mantenimiento
        print("op_mant" if estado_mantenimiento else "opx_mant")

    # --- Botón Técnico Calidad -> Toggle parpadeo Azul ---
    if btn_tec_cal.presionado():
        estado_tecnico_calidad = not estado_tecnico_calidad
        azul_blink_on = False  # arranca el parpadeo siempre desde "apagado"
        if estado_tecnico_calidad:
            print("tec_cal")
        else:
            # Al salir del modo técnico: fijo si el operador sigue activo, si no, apagado
            set_led(AZUL, estado_calidad)
            print("tecx_cal")

    # --- Botón Técnico Mantenimiento -> Toggle parpadeo Amarillo ---
    if btn_tec_mant.presionado():
        estado_tecnico_mant = not estado_tecnico_mant
        amarillo_blink_on = False  # arranca el parpadeo siempre desde "apagado"
        if estado_tecnico_mant:
            print("tec_mant")
        else:
            # Al salir del modo técnico: fijo si el operador sigue activo, si no, apagado
            set_led(AMARILLO, estado_mantenimiento)
            print("tecx_mant")

    time.sleep_ms(10)  # pausa mínima, no bloquea botones ni parpadeo
