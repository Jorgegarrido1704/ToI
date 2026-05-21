import network
import urequests
from machine import Pin, I2C
import ssd1306
import time


# --- Configuración ---
SSID = "BITS Portable"
PASSWORD = "ccex3HamAqY9cgk50uZx"
URL_DB = "http://10.53.22.72/ToI/Corte/Encoder/cuentaPulsos.php"

# Entradas y salidas
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

Start_Signal = Pin(5, Pin.IN, Pin.PULL_DOWN)
Work_Signal = Pin(18, Pin.IN, Pin.PULL_DOWN)

Encoder_Signal_A = Pin(15, Pin.IN, Pin.PULL_UP)
Encoder_Signal_B = Pin(23, Pin.IN, Pin.PULL_UP)
#Usar leds para alarmas, encender maquina parpadear led 1,
#led1 fijo cuando prendan maquina (encendido)
#parpadear led 2 cuando haya un paro pequeño
#parpadear led2 cuando haya paro mayor a 5 min
Led1_On = Pin(2, Pin.OUT)
Led2_Working = Pin(4, Pin.OUT)

# Variables
Led1_On.value(0)
Led2_Working.value(0)

Status = True
perimetro = 100
PPR = 600

pulsos = 0

#TPM
ultimo_pulso_tiempo = time.ticks_ms()
tiempo_trabajo = 0
tiempo_paro = 0
ultimo_loop = time.ticks_ms()
pendiente_envio = False

#Encoder 
def encoder_callback(pin):
    global pulsos, ultimo_pulso_tiempo

    if Encoder_Signal_B.value():
        pulsos += 1
    else:
        pulsos -= 1

    ultimo_pulso_tiempo = time.ticks_ms()

Encoder_Signal_A.irq(trigger=Pin.IRQ_RISING, handler=encoder_callback)


# Conectar a WiFi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi", end="")
    print("\nConectado! IP:", wlan.ifconfig()[0])
    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.5)
    print("\nConectado! IP:", wlan.ifconfig()[0])

# Manejador de la interrupción (Encoder)
def enviar_datos(valor, estado):
    print(f"Enviando a DB: {valor} ({estado})")
    try:
        data = f"valor={valor}&estado={estado}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = urequests.post(URL_DB, data=data, headers=headers)
        print("Respuesta servidor:", res.status_code)
        res.close()
    except Exception as e:
        print("Error enviando datos:", e)

# --- Ejecución Principal ---
conectar_wifi()



# Programa
while Status:

    while not Start_Signal.value():
        oled.fill(0)
        oled.text("Esperando...", 0, 20)
        oled.show()
        time.sleep(0.5)

    # Reset
    pulsos = 0
    tiempo_trabajo = 0
    tiempo_paro = 0
    ultimo_loop = time.ticks_ms()

    while Start_Signal.value() and not Work_Signal.value():
        oled.fill(0)
        oled.text("Encendida", 0, 10)
        oled.text("Sin trabajo", 0, 30)
        oled.show()
        time.sleep(0.1)

    while Start_Signal.value() and Work_Signal.value():

        ahora = time.ticks_ms()
        delta = time.ticks_diff(ahora, ultimo_loop)
        ultimo_loop = ahora

        # TPM
        if time.ticks_diff(ahora, ultimo_pulso_tiempo) < 500:#tiempo de paro
            tiempo_trabajo += delta
            print(tiempo_trabajo)
            estado = "RUN"
            enviar_datos(tiempo_trabajo, "RUN")
            time.sleep_ms(500)
           
        else:
            tiempo_paro += delta
            print(tiempo_paro)
            estado = "STOP"
            enviar_datos(tiempo_trabajo, "STOP")
            time.sleep_ms(500)

        total = tiempo_trabajo + tiempo_paro
        if total > 0:
            disponibilidad = tiempo_trabajo / total
        else:
            disponibilidad = 0

        Longitud_de_corte = (pulsos / PPR) * perimetro

        oled.fill(0)
        oled.text(estado, 0, 0)
        oled.text(f"P:{pulsos}", 0, 10)
        oled.text(f"L:{int(Longitud_de_corte)}mm", 0, 20)
        oled.text(f"D:{int(disponibilidad*100)}%", 0, 30)
        oled.text(f"T.Trab:{int(tiempo_trabajo/1000/60)}m", 0, 40)
        oled.text(f"T.Muer:{int(tiempo_paro/1000/60)}m", 0, 50)
        oled.show()

        time.sleep(0.2)
