from machine import Pin,I2C
import ssd1306
import time


i2c=I2C(0,scl=Pin(22),sda=Pin(21))
oled=ssd1306.SSD1306_I2C(128,64,i2c)


Start_Signal=Pin(5,Pin.IN,Pin.PULL_DOWN)
Work_Signal=Pin(18,Pin.IN,Pin.PULL_DOWN)


Encoder_A=Pin(15,Pin.IN,Pin.PULL_UP)
Encoder_B=Pin(23,Pin.IN,Pin.PULL_UP)


Led1_On=Pin(2,Pin.OUT)
Led2_Working=Pin(4,Pin.OUT)

# Variables
pulsos=0

# Encoder 360 PPR
PPR=360

# Perimetro rodillo en mm
perimetro=100

# TPM
ultimo_pulso_tiempo=time.ticks_ms()
ultimo_loop=time.ticks_ms()

tiempo_trabajo=0
tiempo_paro=0

# Antirrebote
ultimo_irq=0

def encoder_callback(pin):

    global pulsos
    global ultimo_irq
    global ultimo_pulso_tiempo

    ahora_us=time.ticks_us()

    # Filtro rebote
    if time.ticks_diff(ahora_us,ultimo_irq)<500:
        return

    ultimo_irq=ahora_us

    # Leer estados
    a=Encoder_A.value()
    b=Encoder_B.value()

    # Direccion
    if a!=b:
        pulsos+=1
    else:
        pulsos-=1

    ultimo_pulso_tiempo=time.ticks_ms()


Encoder_A.irq(trigger=Pin.IRQ_RISING,handler=encoder_callback)

def formatear_tiempo(ms):

    segundos=ms//1000
    minutos=segundos//60
    horas=minutos//60

    if horas>0:
        return "{:.1f}h".format(segundos/3600)

    elif minutos>0:
        return "{:.1f}m".format(segundos/60)

    else:
        return str(segundos)+"s"
    

while True:

    # Espera Start
    while not Start_Signal.value():

        Led1_On.value(0)
        Led2_Working.value(0)

        oled.fill(0)
        oled.text("Esperando...",0,25)
        oled.show()

        time.sleep(0.1)

    # Reset
    pulsos=0
    tiempo_trabajo=0
    tiempo_paro=0

    ultimo_loop=time.ticks_ms()

    # Maquina encendida
    while Start_Signal.value():

        ahora=time.ticks_ms()

        delta=time.ticks_diff(ahora,ultimo_loop)

        ultimo_loop=ahora

        chambeando=Work_Signal.value()

        # LEDs
        Led1_On.value(1)
        Led2_Working.value(chambeando)

        # TPM
        if chambeando and time.ticks_diff(ahora,ultimo_pulso_tiempo)<1000:

            estado="RUN"
            tiempo_trabajo+=delta

        else:

            estado="STOP"
            tiempo_paro+=delta

        # Disponibilidad
        total=tiempo_trabajo+tiempo_paro

        if total>0:
            disponibilidad=(tiempo_trabajo/total)*100
        else:
            disponibilidad=0

        
        pulsos_local=pulsos

        # Longitud
        longitud=((pulsos_local/PPR)*perimetro)

        # Formato longitud
        if longitud<1000:
            texto_longitud=str(int(longitud))+"mm"
        else:
            texto_longitud="{:.2f}m".format(longitud/1000)

        # Formato tiempo
        texto_tiempo=formatear_tiempo(tiempo_trabajo)

        # OLED
        oled.fill(0)

        oled.text(estado,0,0)

        oled.text("P:"+str(pulsos_local),0,15)

        oled.text("L:"+texto_longitud,0,30)

        oled.text("T:"+texto_tiempo,0,40)

        oled.text("D:"+str(int(disponibilidad))+"%",0,50)

        oled.show()

        time.sleep(0.05)

