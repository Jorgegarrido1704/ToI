from machine import Pin
from time import sleep

# Configuramos el pin GPIO 23 como salida

Relay = Pin(23, Pin.OUT)

# Configuramos el pin GPIO 2 como salida

Led1 = Pin(13, Pin.OUT, value=0)  # Inicialmente apagado
Led2 = Pin(12, Pin.OUT, value=0)  # Inicialmente apagado
led3 = Pin(14, Pin.OUT, value=0)  # Inicialmente apagado
led4 = Pin(27, Pin.OUT, value=0)  # Inicialmente apagado

def control_luces(l1, l2, l3, l4):
    global Led1, Led2, led3, led4
    Led1.value(l1)
    Led2.value(l2)
    led3.value(l3)
    led4.value(l4)
    

#4 botones para encender y apagar el faro y las luces por colores son 4 colores

# Botón para solicitar calidad
def boton_req_quality_handler(pin):
    print("Botón de calidad presionado")

boton_req_quality = Pin(15, Pin.IN, Pin.PULL_UP)
boton_req_quality.irq(trigger=Pin.IRQ_FALLING, handler=boton_req_quality_handler)

def boton_attend_quality_handler(pin):
    print("Botón de calidad atendida")

boton_attend_quality = Pin(2, Pin.IN, Pin.PULL_UP)
boton_attend_quality.irq(trigger=Pin.IRQ_FALLING, handler=boton_attend_quality_handler)

# Botón para solicitar mantenimiento
def boton_req_mant_handler(pin):
    print("Botón de mantenimiento presionado")

boton_req_mant = Pin(4, Pin.IN, Pin.PULL_UP)
boton_req_mant.irq(trigger=Pin.IRQ_FALLING, handler=boton_req_mant_handler)

def boton_attend_mant_handler(pin):
    print("Botón de mantenimiento atendido")

boton_attend_mant = Pin(16, Pin.IN, Pin.PULL_UP)
boton_attend_mant.irq(trigger=Pin.IRQ_FALLING, handler=boton_attend_mant_handler)


while True:
    Relay.value(1)  # Enciende el relay (envía 3.3V)
    print("Relay Encendido")
    # encender luces por colores
    control_luces(1, 0, 0, 0)  # Enciende solo Led1
    
    sleep(5)       # Espera 5 segundos
    
    
    Relay.value(0)  # Apaga el relay (envía 0V)
    print("Relay Apagado")
    sleep(5)       # Espera 5 segundos
