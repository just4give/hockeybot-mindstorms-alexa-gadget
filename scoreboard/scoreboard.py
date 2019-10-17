from time import sleep
import RPi.GPIO as GPIO
import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image,ImageDraw,ImageFont
import paho.mqtt.client as paho
import time
import threading
import json
#sudo pip3 install phao-mqtt


SCORE=0
TIME_COUNTER=180
GAME_IN_PROGRESS=False
PRINTING_GOAL=False

RST = None
GPIO.setmode(GPIO.BCM)
GPIO_TRIGGER = 18
GPIO_ECHO = 24 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)



def on_connect(client,data,flags,rc):
 print("connected to mqtt broker")
 client.connected_flag=True

def on_message(client,data,message):
 global SCORE
 global TIME_COUNTER
 global GAME_IN_PROGRESS

 print("message received")
 print(str(message.payload.decode("utf-8")))
 if message.topic =='/hockeybot/game/start':
     SCORE=0
     TIME_COUNTER=120
     GAME_IN_PROGRESS=True
     print_score()

paho.Client.connected_flag=False
client=paho.Client()
client.loop_start()
client.on_connect=on_connect
client.connect('broker.hivemq.com',1883)
while not client.connected_flag:
 time.sleep(1)

client.subscribe('/hockeybot/game/start')
client.on_message=on_message


def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance
def print_goal():
    global SCORE
    global PRINTING_GOAL
    PRINTING_GOAL=True
    SCORE = SCORE+1
    draw.rectangle((0,0,disp.width,disp.height), outline=0, fill=0)
    font = ImageFont.truetype('Minecraftia.ttf', 40)
    disp.clear()
    disp.display()
    draw.text((10, 10),    'GOAL',  font=font, fill=255)
    disp.image(image)
    disp.display()
    time.sleep(3)
    PRINTING_GOAL=False

def print_score():
    global TIME_COUNTER
    draw.rectangle((0,0,disp.width,disp.height), outline=0, fill=0)
    font = ImageFont.truetype('Minecraftia.ttf', 40)
    disp.clear()
    disp.display()
    draw.text((10, 10),    str(SCORE),  font=font, fill=255)
    disp.image(image)
    disp.display()

def print_timer():
    global TIME_COUNTER
    m, s = divmod(TIME_COUNTER, 60)
    draw.rectangle((65,0,128,40), outline=0, fill=0)
    font2 = ImageFont.truetype('Minecraftia.ttf', 16)
    disp.clear()
    draw.text((65, 10),    "{:02d}:{:02d}".format(m,s),  font=font2, fill=255)
    disp.image(image)
    disp.display()

def game_timer_thread():
    global TIME_COUNTER
    global PRINTING_GOAL
    global GAME_IN_PROGRESS

    while True:
        if GAME_IN_PROGRESS:
            if not PRINTING_GOAL:
                print_timer()
                TIME_COUNTER=TIME_COUNTER-1
        
        time.sleep(1)
        if TIME_COUNTER<0 and GAME_IN_PROGRESS:
            GAME_IN_PROGRESS=False
            data ={'score': SCORE}
            client.publish('/hockeybot/game/over',json.dumps(data))


if __name__ == '__main__':
    disp.begin()
    disp.clear()
    disp.display()
    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    font = ImageFont.truetype('Minecraftia.ttf', 14)

    # Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.truetype('Minecraftia.ttf', 8)

    # Write two lines of text.
    draw.text((10, 10),    'Hockey',  font=font, fill=255)
    draw.text((10, 30), 'Championship!', font=font, fill=255)
    disp.image(image)
    disp.display()
    # Start threads
    threading.Thread(target=game_timer_thread,daemon=True).start()
    try:
        while True:
            
            dist = distance()
            print ("Measured Distance = %.1f cm" % dist)
            if GAME_IN_PROGRESS and (dist > 10 or dist < 7):
                print("GOAL!!!")
                print ("Measured Distance = %.1f cm" % dist)
                print_goal()
                print_score()
            
            time.sleep(0.1)
    finally:
        GPIO.cleanup()