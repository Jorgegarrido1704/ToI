# =====================================================================
# IMPORTACIÓN DE LIBERÍAS
# =====================================================================
import network
import urequests
from machine import Pin, I2C
import esp32
import machine
import ssd1306
import time
import gc

# =====================================================================
# CONFIGURACIÓN DE HARDWARE
# =====================================================================
PIN_VENTILADOR = 5
Ventilador = Pin(PIN_VENTILADOR, Pin.OUT)
Ventilador.value(0)

ultimo_pulso_tiempo = time.ticks_ms()
pulsos = 0
cortes = 0
estado_inductivo_anterior = 1
ultimo_corte_tiempo = 0
ultima_actividad_tiempo = time.ticks_ms()

# MANTENIMIENTO DEL SISTEMA
inicio_sistema = time.ticks_ms()
ultima_limpieza_memoria = time.ticks_ms()

SSID = "BITS Portable"
PASSWORD = "ccex3HamAqY9cgk50uZx"
URL_DB = "http://mxloficina.corp.internal.bergstrominc.com/ToI/Corte/Encoder/cuentaPulsos.php"
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# =====================================================================
# ROTACION DE PANTALLA 180° (DISPLAY DE CABEZA)
# =====================================================================
oled.write_cmd(0xC8)  # COM Scan Direction Remapped
oled.write_cmd(0xA1)  # Segment Remap

def mostrar_log(texto):
    print(texto)
    oled.fill(0)
    oled.text("SISTEMA LOG:", 0, 0)

    if len(texto) > 16:
        oled.text(texto[:16], 0, 24)
        oled.text(texto[16:32], 0, 40)
    else:
        oled.text(texto, 0, 24)

    oled.show()
    time.sleep(1)

Sensor_Inductivo = Pin(18, Pin.IN, Pin.PULL_UP)
Boton_Pantalla = Pin(13, Pin.IN)
Encoder_Signal_A = Pin(15, Pin.IN, Pin.PULL_UP)
Encoder_Signal_B = Pin(23, Pin.IN, Pin.PULL_UP)

Led1_On = Pin(2, Pin.OUT)
Led2_Working = Pin(4, Pin.OUT)

Led1_On.value(0)
Led2_Working.value(0)

Status = True
PPR = 360

tiempo_pantalla_encendida = time.ticks_ms()
pantalla_activa = True

def encoder_callback(pin):
    global pulsos, ultimo_pulso_tiempo, ultima_actividad_tiempo

    if Encoder_Signal_B.value():
        pulsos += 1
    else:
        pulsos -= 1

    ultimo_pulso_tiempo = time.ticks_ms()
    ultima_actividad_tiempo = time.ticks_ms()

Encoder_Signal_A.irq(trigger=Pin.IRQ_RISING, handler=encoder_callback)

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        mostrar_log("Conectando WiFi...")

        intentos = 0
        while not wlan.isconnected() and intentos < 20:
            time.sleep(0.5)
            intentos += 1

    if wlan.isconnected():
        mostrar_log("WiFi OK")
    else:
        mostrar_log("Error WiFi")

def enviar_datos(valor, estado):
    try:
        data = f"valor={valor}&estado={estado}&maquina=M6"
        headers = {'Content-Type':'application/x-www-form-urlencoded'}
        res = urequests.post(URL_DB, data=data, headers=headers)
        res.close()
    except Exception as e:
        print(e)
    finally:
        gc.collect()

def controlar_temperatura():
    try:
        tf = esp32.raw_temperature()
        tc = (tf - 32) * 5 / 9 if tf > 100 else tf

        if tc >= 48:
            Ventilador.value(1)
        elif tc <= 40:
            Ventilador.value(0)

        return tc
    except Exception:
        return 0

def mantenimiento_memoria():
    gc.collect()
    print('RAM Libre:', gc.mem_free())
    print('RAM Usada:', gc.mem_alloc())

oled.poweron()
mostrar_log('Sistema Iniciado')

conectar_wifi()

tiempo_trabajo = 0
tiempo_paro = 0
ultimo_loop = time.ticks_ms()

while Status:
    ahora = time.ticks_ms()
    temp_actual = controlar_temperatura()

    estado_inductivo = Sensor_Inductivo.value()

    if estado_inductivo == 0 and estado_inductivo_anterior == 1:
        if time.ticks_diff(ahora, ultimo_corte_tiempo) > 150:
            cortes += 1
            enviar_datos(cortes,"Corte")
            ultimo_corte_tiempo = ahora
            ultima_actividad_tiempo = ahora

    estado_inductivo_anterior = estado_inductivo

    if Boton_Pantalla.value() == 0:
        if not pantalla_activa:
            oled.poweron()
            pantalla_activa = True

        tiempo_pantalla_encendida = ahora
        ultima_actividad_tiempo = ahora

    if pantalla_activa and time.ticks_diff(ahora, tiempo_pantalla_encendida) > 30*1000:
        oled.poweroff()
        pantalla_activa = False

    delta = time.ticks_diff(ahora, ultimo_loop)
    ultimo_loop = ahora

    if time.ticks_diff(ahora, ultimo_pulso_tiempo) < 500:
        tiempo_trabajo += delta
        estado = 'RUN'
        Led1_On.value(1)
        Led2_Working.value(1)
    else:
        tiempo_paro += delta
        estado = 'STOP'
        Led2_Working.value(0)

    if pantalla_activa:
        total = tiempo_trabajo + tiempo_paro
        disponibilidad = (tiempo_trabajo / total) * 100 if total > 0 else 0
        oled.rotate(90)
        oled.fill(0)
        oled.text(f'ESTADO: {estado}', 0, 0)
        oled.text(f'Cortes: {cortes}', 0, 12)
        oled.text(f'TEMP: {int(temp_actual)} C', 0, 24)
        oled.text(f'D:{int(disponibilidad)}%', 0, 36)
        oled.text(f'Trab:{int(tiempo_trabajo/1000/60)}m', 0, 48)
        oled.text(f'Paro:{int(tiempo_paro/1000/60)}m', 0, 58)
        oled.show()

    # Limpieza cada hora
    if time.ticks_diff(ahora, ultima_limpieza_memoria) > 3600000:
        mostrar_log('Limpieza RAM')
        mantenimiento_memoria()
        ultima_limpieza_memoria = ahora

    # Reinicio preventivo cada 24 horas
    if time.ticks_diff(ahora, inicio_sistema) > 86400000:
        mostrar_log('Reinicio 24H')
        Ventilador.value(0)
        Led2_Working.value(0)
        oled.poweroff()
        gc.collect()
        machine.reset()

    time.sleep(0.1)

