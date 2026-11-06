import network
import urequests
from machine import Pin, I2C, RTC
import machine
import ssd1306
import time
import esp32

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
Status = True

# Variables
pulsos = 0
ultimo_pulso_contado = 0  # Para validar inactividad del encoder

# Encoder 360 PPR
PPR = 360

# Perimetro rodillo en mm
perimetro = 100

# Tiempos y Watchdogs
ultimo_pulso_tiempo = time.ticks_ms()
ultimo_loop = time.ticks_ms()
ultimo_cambio_encoder = time.ticks_ms() # Watchdog de 20 minutos

tiempo_trabajo = 0
tiempo_paro = 0
pendiente_envio = False

# Antirrebote
ultimo_irq = 0

rtc = RTC()

def encoder_callback(pin):
    global pulsos, ultimo_irq, ultimo_pulso_tiempo
    ahora_us = time.ticks_us()

    # Filtro rebote
    if time.ticks_diff(ahora_us, ultimo_irq) < 50:
        return

    ultimo_irq = ahor_us

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

# Conectar a WiFi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi", end="")
    
    intentos = 0
    while not wlan.isconnected() and intentos < 20:
        print(".", end="")
        time.sleep(0.5)
        intentos += 1
        
    if wlan.isconnected():
        print("\nConectado! IP:", wlan.ifconfig()[0])
        sincronizar_hora()
    else:
        print("\nNo se pudo conectar a WiFi. Continuando en modo offline...")

# Sincronizar hora del sistema (Simulado vía API o HTTP)
def sincronizar_hora():
    try:
        # Nota: Puedes usar un servidor NTP estándar. Aquí usamos una petición rápida para obtener hora.
        # Si tu servidor local devuelve la hora en los headers, se puede extraer de ahí.
        # Por ahora seteamos una hora base aproximada si no hay internet, o puedes configurar NTP.
        print("Sincronizando reloj interno...")
        # rtc.datetime((year, month, day, weekday, hours, minutes, seconds, subseconds))
        # Ejemplo por defecto si requieres hardcode o sincronización exacta:
        pass 
    except Exception as e:
        print("Error al sincronizar hora:", e)

# Manejador de envío a DB
def enviar_datos(valor, estado, maquina):
    print(f"Enviando a DB: {valor} ({estado}) maquina={maquina}")
    try:
        data = f"valor={valor}&estado={estado}&maquina={maquina}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = urequests.post(URL_DB, data=data, headers=headers)
        print("Respuesta servidor:", res.status_code)
        res.close()
    except Exception as e:
        print("Error enviando datos:", e)

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

# --- Ejecución Principal ---
conectar_wifi()

while True:
    # --- VERIFICACIÓN DE HORA (DEEP SLEEP A LAS 4:00 AM) ---
    # rtc.datetime() devuelve: (año, mes, dia, el_dia_de_la_semana, hora, minuto, segundo, subsegundo)
    hora_actual = rtc.datetime()[4]
    if hora_actual == 4: 
        print("Es la hora de mantenimiento (4:00 AM). Entrando en Deep Sleep por 3 horas...")
        oled.fill(0)
        oled.text("Modo Dormido...", 0, 25)
        oled.show()
        time.sleep(2)
        # 3 horas = 3 * 60 * 60 * 1000 milisegundos
        machine.deepsleep(3 * 60 * 60 * 1000) 

    # Espera Start
    while not Start_Signal.value():
        Led1_On.value(0)
        Led2_Working.value(0)

        oled.fill(0)
        oled.text("Esperando...", 0, 25)
        oled.show()
        time.sleep(0.1)

    # Reset de variables de operación al arrancar la máquina
    pulsos = 0
    ultimo_pulso_contado = 0
    tiempo_trabajo = 0
    tiempo_paro = 0
    lastSignal = ""

    ultimo_loop = time.ticks_ms()
    ultimo_cambio_encoder = time.ticks_ms()

    # Maquina encendida
    while Start_Signal.value():
        ahora = time.ticks_ms()
        delta = time.ticks_diff(ahora, ultimo_loop)
        ultimo_loop = ahora

        chambeando = Work_Signal.value()

        # LEDs
        Led1_On.value(1)
        Led2_Working.value(chambeando)

        # --- REBOOT POR INACTIVIDAD DE ENCODER (20 MIN) ---
        if pulsos != ultimo_pulso_contado:
            ultimo_cambio_encoder = ahora  # El encoder se está moviendo, reiniciamos el timer
            ultimo_pulso_contado = pulsos
        else:
            # Si pasaron más de 20 minutos (20 * 60 * 1000 ms) sin cambios en 'pulsos'
            if time.ticks_diff(ahora, ultimo_cambio_encoder) > (20 * 60 * 1000):
                print("Inactividad detectada por más de 20 min. Reiniciando sistema...")
                machine.reset() # Soft reboot del ESP32

        # Lógica de estados TPM
        if chambeando and time.ticks_diff(ahora, ultimo_pulso_tiempo) < 300:
            estado = "RUN"
            tiempo_trabajo += delta
            if estado != lastSignal:
                enviar_datos(tiempo_trabajo, "STOP", "M4")
                enviar_datos(tiempo_trabajo, "RUN", "M4")
                time.sleep(0.03)
            lastSignal = estado
        else:
            estado = "STOP"
            tiempo_paro += delta
            if estado != lastSignal:
                enviar_datos(tiempo_paro, "RUN", "M4")
                enviar_datos(tiempo_paro, "STOP", "M4")
                time.sleep(0.03)
            lastSignal = estado

        # Calcular disponibilidad
        total = tiempo_trabajo + tiempo_paro
        disponibilidad = (tiempo_trabajo / total) * 100 if total > 0 else 0
        
        pulsos_local = pulsos
        longitud = ((pulsos_local / PPR) * perimetro)

        # Formato longitud
        if longitud < 1000:
            texto_longitud = str(int(longitud)) + "mm"
        else:
            texto_longitud = "{:.2f}m".format(longitud / 1000)

        texto_tiempo = formatear_tiempo(tiempo_trabajo)
        
        # Temperatura interna ESP32
        temperature = esp32.raw_temperature()
        celsius = round((temperature - 32) / 1.8, 1)
        
        # Actualizar OLED
        oled.fill(0)
        oled.text(estado, 0, 0)
        oled.text("P:" + str(pulsos_local), 0, 10)
        oled.text("L:" + texto_longitud, 0, 20)
        oled.text("T:" + texto_tiempo, 0, 30)
        oled.text("D:" + str(int(disponibilidad)) + "%", 0, 40)
        oled.text("TEMP: " + str(celsius) + " C", 0, 50)
        oled.show()

        time.sleep(0.05)
