import network
import socket
import gc
import time
import esp32
import ntptime
import machine
import ssd1306
from machine import Pin, I2C, WDT

# --- Configuración ---
SSID = "BITS Portable"
PASSWORD = "ccex3HamAqY9cgk50uZx"
HOST = "mxloficina.corp.internal.bergstrominc.com"
PATH = "/ToI/Corte/Encoder/cuentaPulsos.php"
MAQUINA = "M3"

# Watchdog: si el loop no lo "alimenta" en 30 s, el ESP32 se reinicia solo.
# OJO: una vez iniciado no se puede detener (durante pruebas por REPL, la
# placa se reiniciará sola si interrumpes con Ctrl+C).
WDT_TIMEOUT_MS = 30000
wdt = WDT(timeout=WDT_TIMEOUT_MS)

# --- Hardware ---
# 100 kHz es más tolerante a ruido que la velocidad por defecto (400 kHz)
i2c = None
oled = None


def iniciar_oled():
    global i2c, oled
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)


iniciar_oled()

Start_Signal = Pin(5, Pin.IN, Pin.PULL_DOWN)
Work_Signal = Pin(18, Pin.IN, Pin.PULL_DOWN)
Encoder_A = Pin(15, Pin.IN, Pin.PULL_UP)
Encoder_B = Pin(23, Pin.IN, Pin.PULL_UP)
Led1_On = Pin(2, Pin.OUT)
Led2_Working = Pin(4, Pin.OUT)

# --- Variables ---
pulsos = 0
PPR = 360
perimetro = 100

ultimo_pulso_tiempo = time.ticks_ms()
ultimo_loop = time.ticks_ms()
tiempo_trabajo = 0
tiempo_paro = 0

DEBOUNCE_US = 800
ultimo_irq = 0

# Ciclo de pantalla: 5 min ON / 3 min OFF
CICLO_PANTALLA_TOTAL_MS = 3 * 60 * 1000
PANTALLA_ON_MS = 5 * 60 * 1000
inicio_ciclo_pantalla = time.ticks_ms()
pantalla_encendida = True

# Reset periódico cada 12 horas
RESET_INTERVAL_MS = 12 * 60 * 60 * 1000
tiempo_para_reseteo = time.ticks_ms()

# Limpieza de memoria
GC_INTERVAL_MS = 60 * 1000
ultimo_gc = time.ticks_ms()

# Re-inicialización periódica del controlador del OLED (cura "congelados"
# silenciosos causados por ruido eléctrico)
OLED_REINIT_MS = 30 * 1000
ultimo_oled_reinit = time.ticks_ms()

# Fallas consecutivas del OLED antes de reiniciar el ESP32
fallas_oled = 0
MAX_FALLAS_OLED = 5

# Vigilancia de WiFi
WIFI_CHECK_MS = 10 * 1000
ultimo_wifi_check = time.ticks_ms()
wlan = network.WLAN(network.STA_IF)


# --- Encoder ---
def encoder_callback(pin):
    global pulsos, ultimo_irq, ultimo_pulso_tiempo

    ahora_us = time.ticks_us()
    if time.ticks_diff(ahora_us, ultimo_irq) < DEBOUNCE_US:
        return
    ultimo_irq = ahora_us

    if Encoder_A.value() != Encoder_B.value():
        pulsos += 1
    else:
        pulsos -= 1

    ultimo_pulso_tiempo = time.ticks_ms()


Encoder_A.irq(trigger=Pin.IRQ_RISING, handler=encoder_callback)


# --- OLED a prueba de fallos ---
def oled_dibujar(lineas):
    """lineas = [(texto, x, y), ...]. Nunca lanza excepción; si el OLED falla
    repetidamente, reinicia el ESP32."""
    global fallas_oled
    try:
        oled.fill(0)
        for texto, x, y in lineas:
            oled.text(texto, x, y)
        oled.show()
        fallas_oled = 0
        return True
    except Exception as e:
        fallas_oled += 1
        print("Error OLED ({}): {}".format(fallas_oled, e))
        try:
            iniciar_oled()
        except Exception as e2:
            print("Error reiniciando OLED:", e2)
        if fallas_oled >= MAX_FALLAS_OLED:
            print("OLED no responde, reiniciando ESP32")
            machine.reset()
        return False


def oled_reinit_si_toca(ahora):
    global ultimo_oled_reinit
    if pantalla_encendida and time.ticks_diff(ahora, ultimo_oled_reinit) > OLED_REINIT_MS:
        ultimo_oled_reinit = ahora
        try:
            oled.init_display()
        except Exception as e:
            print("Error init_display:", e)
            try:
                iniciar_oled()
            except Exception:
                pass


# --- WiFi ---
def conectar_wifi(timeout_s=20):
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi", end="")
    oled_dibujar([("Conectando a la", 0, 20), ("red...", 0, 30)])

    inicio = time.ticks_ms()
    while not wlan.isconnected():
        wdt.feed()
        if time.ticks_diff(time.ticks_ms(), inicio) > timeout_s * 1000:
            print("\nSin WiFi (se reintentará en segundo plano)")
            return False
        print(".", end="")
        time.sleep(0.5)

    print("\nConectado! IP:", wlan.ifconfig()[0])
    return True


def vigilar_wifi(ahora):
    """No bloquea: si se cayó el WiFi, lanza la reconexión y sigue."""
    global ultimo_wifi_check
    if time.ticks_diff(ahora, ultimo_wifi_check) < WIFI_CHECK_MS:
        return
    ultimo_wifi_check = ahora
    if not wlan.isconnected():
        print("WiFi caído, reconectando...")
        try:
            wlan.disconnect()
            wlan.connect(SSID, PASSWORD)
        except Exception as e:
            print("Error reconectando:", e)


# --- HTTP con timeout (reemplaza urequests, que puede bloquearse para siempre) ---
def http_post(data):
    s = None
    try:
        addr = socket.getaddrinfo(HOST, 80)[0][-1]
        s = socket.socket()
        s.settimeout(3)
        s.connect(addr)
        req = ("POST {} HTTP/1.0\r\nHost: {}\r\n"
               "Content-Type: application/x-www-form-urlencoded\r\n"
               "Content-Length: {}\r\nConnection: close\r\n\r\n{}"
               ).format(PATH, HOST, len(data), data)
        s.write(req.encode())
        resp = s.read(64)
        if resp:
            return resp.split(b"\r\n")[0]
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def enviar_datos(valor, estado, maquina):
    wdt.feed()
    if not wlan.isconnected():
        print("Sin WiFi, no se envía")
        return
    print("Enviando a DB: {} ({}) maquina={}".format(valor, estado, maquina))
    try:
        data = "valor={}&estado={}&maquina={}".format(valor, estado, maquina)
        print("Respuesta servidor:", http_post(data))
    except Exception as e:
        print("Error enviando datos:", e)
    wdt.feed()


# --- Utilidades ---
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
    try:
        temperature = esp32.raw_temperature()
        return round((temperature - 32) / 1.8, 1)
    except Exception:
        return None


def actualizar_ciclo_pantalla(ahora):
    global inicio_ciclo_pantalla, pantalla_encendida

    transcurrido = time.ticks_diff(ahora, inicio_ciclo_pantalla)
    if transcurrido >= CICLO_PANTALLA_TOTAL_MS:
        inicio_ciclo_pantalla = ahora
        transcurrido = 0

    debe_estar_encendida = transcurrido < PANTALLA_ON_MS

    if debe_estar_encendida and not pantalla_encendida:
        try:
            iniciar_oled()          # re-inicialización completa al encender
        except Exception as e:
            print("Error iniciando OLED:", e)
        pantalla_encendida = True
    elif not debe_estar_encendida and pantalla_encendida:
        try:
            oled.fill(0)
            oled.show()
            oled.poweroff()
        except Exception as e:
            print("Error apagando OLED:", e)
        pantalla_encendida = False

    return pantalla_encendida


def tareas_periodicas(ahora):
    """Se llama en TODOS los loops: watchdog, reset programado, gc, wifi, oled."""
    global ultimo_gc

    wdt.feed()

    if time.ticks_diff(ahora, tiempo_para_reseteo) > RESET_INTERVAL_MS:
        machine.reset()

    actualizar_ciclo_pantalla(ahora)
    oled_reinit_si_toca(ahora)
    vigilar_wifi(ahora)

    if time.ticks_diff(ahora, ultimo_gc) > GC_INTERVAL_MS:
        gc.collect()
        ultimo_gc = ahora


# --- Programa principal ---
def sincronizar_hora():
    ZONA_HORARIA = -6
    rtc = machine.RTC()
    if not wlan.isconnected():
        print("Sin WiFi, se omite NTP")
        return
    try:
        ntptime.settime()
        segundos_locales = time.time() + (ZONA_HORARIA * 3600)
        (anio, mes, dia, hora, minuto, segundo, dia_semana, dia_anio) = time.localtime(segundos_locales)
        rtc.datetime((anio, mes, dia, dia_semana, hora, minuto, segundo, 0))
        print("Sincronización NTP exitosa:", hora, ":", minuto)
    except Exception as e:
        print("Error al sincronizar RTC:", e)


def main():
    global pulsos, tiempo_trabajo, tiempo_paro, ultimo_loop

    conectar_wifi()
    sincronizar_hora()

    while True:

        # ---- Espera Start ----
        while not Start_Signal.value():
            Led1_On.value(0)
            Led2_Working.value(0)

            ahora = time.ticks_ms()
            tareas_periodicas(ahora)

            if pantalla_encendida:
                oled_dibujar([("Esperando...", 0, 25)])

            time.sleep(0.1)

        # ---- Reset de variables de ciclo ----
        pulsos = 0
        tiempo_trabajo = 0
        tiempo_paro = 0
        lastSignal = ""
        ultimo_loop = time.ticks_ms()

        # ---- Máquina encendida ----
        while Start_Signal.value():
            ahora = time.ticks_ms()
            tareas_periodicas(ahora)

            delta = time.ticks_diff(ahora, ultimo_loop)
            ultimo_loop = ahora

            chambeando = Work_Signal.value()

            Led1_On.value(1)
            Led2_Working.value(chambeando)

            if chambeando and time.ticks_diff(ahora, ultimo_pulso_tiempo) < 450:
                estado = "RUN"
                tiempo_trabajo += delta
                if estado != lastSignal:
                    enviar_datos(tiempo_trabajo, "STOP", MAQUINA)
                    enviar_datos(tiempo_trabajo, "RUN", MAQUINA)
                    time.sleep(0.02)
                lastSignal = estado
            else:
                estado = "STOP"
                tiempo_paro += delta
                if estado != lastSignal:
                    enviar_datos(tiempo_paro, "RUN", MAQUINA)
                    enviar_datos(tiempo_paro, "STOP", MAQUINA)
                    time.sleep(0.02)
                lastSignal = estado

            total = tiempo_trabajo + tiempo_paro
            disponibilidad = (tiempo_trabajo / total) * 100 if total > 0 else 0
            pulsos_local = pulsos

            if pantalla_encendida:
                celsius = leer_temperatura_c()
                texto_temp = "{} C".format(celsius) if celsius is not None else "N/A"

                oled_dibujar([
                    (estado, 0, 0),
                    ("P:" + str(pulsos_local), 0, 15),
                    ("D:" + str(int(disponibilidad)) + "%", 0, 40),
                    ("TEMP: " + texto_temp, 0, 50),
                ])

            time.sleep(0.02)


# Cualquier error inesperado => reinicio automático (Ctrl+C sigue funcionando
# porque KeyboardInterrupt no es subclase de Exception).
try:
    main()
except Exception as e:
    print("Error fatal, reiniciando:", e)
    time.sleep(1)
    machine.reset()