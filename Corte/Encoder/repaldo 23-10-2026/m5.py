import network
import urequests
import gc
from machine import Pin, I2C, RTC
import ssd1306
import time
import esp32
import ntptime
import machine


# --- Configuración ---
SSID = "BITS Portable"
PASSWORD = "ccex3HamAqY9cgk50uZx"
URL_DB = "http://mxloficina.corp.internal.bergstrominc.com/ToI/Corte/Encoder/cuentaPulsos.php"

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

Start_Signal = Pin(5, Pin.IN, Pin.PULL_DOWN)
Work_Signal = Pin(18, Pin.IN, Pin.PULL_DOWN)

Encoder_A = Pin(15, Pin.IN, Pin.PULL_UP)
Encoder_B = Pin(23, Pin.IN, Pin.PULL_UP)

Led1_On = Pin(2, Pin.OUT)
Led2_Working = Pin(4, Pin.OUT)

# Variables
pulsos = 0

# Encoder 360 PPR
PPR = 360

# Perimetro rodillo en mm
perimetro = 100

# TPM
ultimo_pulso_tiempo = time.ticks_ms()
ultimo_loop = time.ticks_ms()

tiempo_trabajo = 0
tiempo_paro = 0

# Antirrebote (en microsegundos). 50us era prácticamente nulo; se sube a un
# valor razonable para un encoder mecánico/óptico. Ajustar según el encoder real.
DEBOUNCE_US = 800
ultimo_irq = 0

# --- Ciclo de pantalla: 5 min encendida / 55 min apagada (ciclo de 1h) ---
CICLO_PANTALLA_TOTAL_MS = 5 * 60 * 1000   # 60 minutos
PANTALLA_ON_MS = 5 * 60 * 1000             # primeros 5 minutos encendida
inicio_ciclo_pantalla = time.ticks_ms()
pantalla_encendida = True

# --- Reset periódico cada 3 horas ---
RESET_INTERVAL_MS = 1 * 60 * 60 * 1000
tiempo_para_reseteo = time.ticks_ms()

# --- Limpieza de memoria periódica ---
GC_INTERVAL_MS = 7 * 60 * 1000
ultimo_gc = time.ticks_ms()


def encoder_callback(pin):
    global pulsos, ultimo_irq, ultimo_pulso_tiempo

    ahora_us = time.ticks_us()

    # Filtro rebote
    if time.ticks_diff(ahora_us, ultimo_irq) < DEBOUNCE_US:
        return

    ultimo_irq = ahora_us

    # Leer estados
    a = Encoder_A.value()
    b = Encoder_B.value()

    # Direccion
    if a != b:
        pulsos += 1
    else:
        pulsos -= 1

    ultimo_pulso_tiempo = time.ticks_ms()


Encoder_A.irq(trigger=Pin.IRQ_RISING, handler=encoder_callback)


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi", end="")

    oled.fill(0)
    oled.text("Conectando a la", 0, 20)
    oled.text("red...", 0, 30)
    oled.show()

    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.5)

    # Este print ahora sí ocurre después de confirmar la conexión real
    print("\nConectado! IP:", wlan.ifconfig()[0])


def enviar_datos(valor, estado, maquina):
    print("Enviando a DB: {} ({}) maquina={}".format(valor, estado, maquina))
    res = None
    try:
        data = "valor={}&estado={}&maquina={}".format(valor, estado, maquina)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = urequests.post(URL_DB, data=data, headers=headers)
        print("Respuesta servidor:", res.status_code)
    except Exception as e:
        print("Error enviando datos:", e)
    finally:
        if res is not None:
            res.close()


def formatear_tiempo(ms):
    segundos = ms // 1000
    minutos = segundos // 60
    horas = minutos // 60

    if horas > 0:
        return "{:.1f}h".format(segundos / 3600)
    elif minutos > 0:
        return "{:.1f}m".format(segundos / 60)
    else:
        return str(segundos) + "s"


def leer_temperatura_c():
    # esp32.raw_temperature() no existe / falla en algunas variantes (S2/S3/C3)
    # y en algunos builds. Se protege para que nunca tumbe el loop principal.
    try:
        temperature = esp32.raw_temperature()
        return round((temperature - 32) / 1.8, 1)
    except Exception:
        return None


def actualizar_ciclo_pantalla(ahora):
    """Mantiene un ciclo continuo de 60 min: 5 min pantalla ON, 55 min OFF.
    No apaga el ESP32 (a diferencia del deepsleep original), así que el
    conteo de pulsos, WiFi y RTC no se pierden."""
    global inicio_ciclo_pantalla, pantalla_encendida

    transcurrido = time.ticks_diff(ahora, inicio_ciclo_pantalla)

    if transcurrido >= CICLO_PANTALLA_TOTAL_MS:
        inicio_ciclo_pantalla = ahora
        transcurrido = 0

    debe_estar_encendida = transcurrido < PANTALLA_ON_MS

    if debe_estar_encendida and not pantalla_encendida:
        oled.poweron()
        pantalla_encendida = True
    elif not debe_estar_encendida and pantalla_encendida:
        oled.fill(0)
        oled.show()
        oled.poweroff()
        pantalla_encendida = False

    return pantalla_encendida


# --- Ejecución Principal ---
conectar_wifi()

ZONA_HORARIA = -6  # México / Central Standard Time
rtc = machine.RTC()

try:
    ntptime.settime()
    print("Sincronización NTP exitosa.")

    segundos_locales = time.time() + (ZONA_HORARIA * 3600)
    (anio, mes, dia, hora, minuto, segundo, dia_semana, dia_anio) = time.localtime(segundos_locales)

    rtc.datetime((anio, mes, dia, dia_semana, hora, minuto, segundo, 0))

    print("Hora del RTC (Minuto):", rtc.datetime()[5])
    print("Hora extraída directamente:", hora, ":", minuto)

except Exception as e:
    print("Error al sincronizar o configurar el RTC:", e)

while True:

    # Espera Start
    while not Start_Signal.value():

        Led1_On.value(0)
        Led2_Working.value(0)

        ahora = time.ticks_ms()
        actualizar_ciclo_pantalla(ahora)

        if pantalla_encendida:
            oled.fill(0)
            oled.text("Esperando...", 0, 25)
            oled.show()

        if time.ticks_diff(ahora, ultimo_gc) > GC_INTERVAL_MS:
            gc.collect()
            ultimo_gc = ahora

        time.sleep(0.1)

    # Reset de variables de ciclo de trabajo
    pulsos = 0
    tiempo_trabajo = 0
    tiempo_paro = 0
    lastSignal = ""

    ultimo_loop = time.ticks_ms()

    # Maquina encendida
    while Start_Signal.value():

        ahora = time.ticks_ms()

        # Reset completo cada 3 horas
        if time.ticks_diff(ahora, tiempo_para_reseteo) > RESET_INTERVAL_MS:
            machine.reset()

        # Ciclo de pantalla 5min ON / 55min OFF (no apaga el ESP32)
        actualizar_ciclo_pantalla(ahora)

        # Limpieza de memoria periódica
        if time.ticks_diff(ahora, ultimo_gc) > GC_INTERVAL_MS:
            gc.collect()
            ultimo_gc = ahora

        delta = time.ticks_diff(ahora, ultimo_loop)
        ultimo_loop = ahora

        chambeando = Work_Signal.value()

        # LEDs
        Led1_On.value(1)
        Led2_Working.value(chambeando)

        # TPM
        if chambeando and time.ticks_diff(ahora, ultimo_pulso_tiempo) < 500:
            estado = "RUN"
            tiempo_trabajo += delta
            if estado != lastSignal:
                enviar_datos(tiempo_trabajo, "STOP", "M5")
                enviar_datos(tiempo_trabajo, "RUN", "M5")
                time.sleep(0.02)
            lastSignal = estado

        else:
            estado = "STOP"
            tiempo_paro += delta
            if estado != lastSignal:
                enviar_datos(tiempo_paro, "RUN", "M5")
                enviar_datos(tiempo_paro, "STOP", "M5")
                time.sleep(0.02)
            lastSignal = estado

        # Disponibilidad
        total = tiempo_trabajo + tiempo_paro
        disponibilidad = (tiempo_trabajo / total) * 100 if total > 0 else 0

        pulsos_local = pulsos

        # Longitud
        longitud = (pulsos_local / PPR) * perimetro

        # Solo se reconstruyen strings y se dibuja el OLED si está encendido:
        # ahorra CPU/memoria durante los 55 minutos de pantalla apagada.
        if pantalla_encendida:

            if longitud < 1000:
                texto_longitud = str(int(longitud)) + "mm"
            else:
                texto_longitud = "{:.2f}m".format(longitud / 1000)

            texto_tiempo = formatear_tiempo(tiempo_trabajo)
            celsius = leer_temperatura_c()
            texto_temp = "{} C".format(celsius) if celsius is not None else "N/A"

            oled.fill(0)
            oled.text(estado, 0, 0)
            oled.text("P:" + str(pulsos_local), 0, 15)
            #oled.text("L:" + texto_longitud, 0, 20)
            #oled.text("T:" + texto_tiempo, 0, 30)
            oled.text("D:" + str(int(disponibilidad)) + "%", 0, 40)
            oled.text("TEMP: " + texto_temp, 0, 50)
            oled.show()

        time.sleep(0.02)
    

