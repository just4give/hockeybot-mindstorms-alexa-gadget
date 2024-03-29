# Copyright 2019 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
# 
# You may not use this file except in compliance with the terms and conditions 
# set forth in the accompanying LICENSE.TXT file.
#
# THESE MATERIALS ARE PROVIDED ON AN "AS IS" BASIS. AMAZON SPECIFICALLY DISCLAIMS, WITH 
# RESPECT TO THESE MATERIALS, ALL WARRANTIES, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING 
# THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

import time
import logging
import json
import random
import threading

from enum import Enum
from agt import AlexaGadget

from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.motor import OUTPUT_A, OUTPUT_B, OUTPUT_C, MoveTank, SpeedPercent, MediumMotor,LargeMotor
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.sensor import INPUT_4
import paho.mqtt.client as paho

# Set the logging level to INFO to see messages from AlexaGadget
logging.basicConfig(level=logging.INFO)


class Direction(Enum):
    """
    The list of directional commands and their variations.
    These variations correspond to the skill slot values.
    """
    FORWARD = ['forward', 'forwards', 'go forward']
    BACKWARD = ['back', 'backward', 'backwards', 'go backward']
    LEFT = ['left', 'go left']
    RIGHT = ['right', 'go right']
    STOP = ['stop', 'brake']


class Command(Enum):
    """
    The list of preset commands and their invocation variation.
    These variations correspond to the skill slot values.
    """
    KICK = ['kick', 'shoot','shot','hit']
    
class EventName(Enum):
    """
    The list of custom event name sent from this gadget
    """
    GAME_OVER = "GAME_OVER"
    

class MindstormsGadget(AlexaGadget):
    """
    A Mindstorms gadget that performs movement based on voice commands.
    Two types of commands are supported, directional movement and preset.
    """

    def __init__(self):
        """
        Performs Alexa Gadget initialization routines and ev3dev resource allocation.
        """
        super().__init__()

        # Gadget state
        self.in_progress = False

        # Ev3dev initialization
        self.leds = Leds()
        self.sound = Sound()
        self.drive = MoveTank(OUTPUT_B, OUTPUT_A)
        self.stick = MediumMotor(OUTPUT_C)
        self.cs = ColorSensor(INPUT_4)
        self.cs.mode = 'COL-REFLECT'
        self.floor_light = self.cs.value()
        print("floor light intensity = {}".format(self.floor_light))
        self.speed = 20
        self.kickAngle = 170
        paho.Client.connected_flag=False
        self.client=paho.Client()
        self.client.loop_start()
        self.client.on_connect=self.mqtt_connected
        self.client.connect('broker.hivemq.com',1883)
        while not self.client.connected_flag:
            time.sleep(1)

        self.client.subscribe('/hockeybot/game/over')
        self.client.on_message=self.mqtt_on_message

        # Start threads
        threading.Thread(target=self.check_for_obstacles_thread,daemon=True).start()

    def mqtt_connected(self,client,data,flags,rc):
        print("connected to mqtt broker")
        client.connected_flag=True

    def mqtt_on_message(self,client,data,message):
        print("message received from MQTT")
        print(str(message.payload.decode("utf-8")))
        
        if message.topic =='/hockeybot/game/over':
            try:
                print("game over message received")
                jsondata = json.loads(str(message.payload.decode("utf-8")))
                
                self._send_event(EventName.GAME_OVER, {'score':jsondata['score']})
                print("event posted to alexa")
            except Exception as e: 
                print(e)
                
            

    def on_connected(self, device_addr):
        """
        Gadget connected to the paired Echo device.
        :param device_addr: the address of the device we connected to
        """
        self.leds.set_color("LEFT", "GREEN")
        self.leds.set_color("RIGHT", "GREEN")
        print("{} connected to Echo device".format(self.friendly_name))
        #self.sound.speak("Connected to Echo device")

    def on_disconnected(self, device_addr):
        """
        Gadget disconnected from the paired Echo device.
        :param device_addr: the address of the device we disconnected from
        """
        self.leds.set_color("LEFT", "BLACK")
        self.leds.set_color("RIGHT", "BLACK")
        print("{} disconnected from Echo device".format(self.friendly_name))

    def on_custom_hockeybot_gadget_control(self, directive):
        """
        Handles the Custom.Mindstorms.Gadget control directive.
        :param directive: the custom directive with the matching namespace and name
        """
        try:
            payload = json.loads(directive.payload.decode("utf-8"))
            print("Control payload: {}".format(payload))
            control_type = payload["type"]
            self.in_progress = True
            if control_type == "start":
                
                #Notify scoreboard to start count down
                data={'duration':300}
                self.client.publish('/hockeybot/game/start',json.dumps(data))
                time.sleep(3)
                #self._move(payload["direction"], int(payload["duration"]), int(payload["speed"]))

            if control_type == "move":

                # Expected params: [direction, duration, speed]
                self._move(payload["direction"], int(payload["duration"]), int(payload["speed"]))

            if control_type == "command":
                # Expected params: [command]
                self._kick(payload["direction"])

        except KeyError:
            print("Missing expected parameters: {}".format(directive))

    def _move(self, direction, duration: int, speed: int, is_blocking=False):
        """
        Handles move commands from the directive.
        Right and left movement can under or over turn depending on the surface type.
        :param direction: the move direction
        :param duration: the duration in seconds
        :param speed: the speed percentage as an integer
        :param is_blocking: if set, motor run until duration expired before accepting another command
        """
        self.forwardMode = False

        print("Move command: ({}, {}, {}, {})".format(direction, speed, duration, is_blocking))
        if direction in Direction.FORWARD.value:
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in Direction.BACKWARD.value:
            self.drive.on_for_seconds(SpeedPercent(-speed), SpeedPercent(-speed), duration, block=is_blocking)

        if direction in (Direction.RIGHT.value + Direction.LEFT.value):
            self._turn(direction, speed)
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in Direction.STOP.value:
            self.drive.off()
            self.patrol_mode = False

    def _kick(self,direction):
        """
        Handles preset commands.
        :param command: the preset command
        :param speed: the speed if applicable
        """
        print("Kick command: ",str(self.kickAngle))
        self.drive.off()
        if direction in Direction.LEFT.value:
            self.stick.on_for_rotations(SpeedPercent(50),-1)

        if direction in Direction.RIGHT.value:
            self.stick.on_for_rotations(SpeedPercent(50),1)

        
        #self.kickAngle = self.kickAngle*-1
        

    def _turn(self, direction, speed):
        """
        Turns based on the specified direction and speed.
        Calibrated for hard smooth surface.
        :param direction: the turn direction
        :param speed: the turn speed
        """
        if direction in Direction.LEFT.value:
            self.drive.on_for_seconds(SpeedPercent(0), SpeedPercent(speed), 2)

        if direction in Direction.RIGHT.value:
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(0), 2)

    def check_for_obstacles_thread(self):
        while True:
            read = self.cs.value()
            #print(str(read))
            #ground boundary 
            if read < 10 :
                self.drive.off()
                self._turn('left',self.speed)
                #self.drive.on_for_seconds(SpeedPercent(self.speed), SpeedPercent(self.speed), 5)
                
            time.sleep(0.2)
    
    
    def _send_event(self, name: EventName, payload):
        """
        Sends a custom event to trigger a sentry action.
        :param name: the name of the custom event
        :param payload: the sentry JSON payload
        """
        self.send_custom_event('Custom.Hockeybot.Gadget', name.value, payload)


 
if __name__ == '__main__':

    # Startup sequence
    gadget = MindstormsGadget()
    gadget.sound.play_song((('C4', 'e'), ('D4', 'e'), ('E5', 'q')))
    gadget.leds.set_color("LEFT", "GREEN")
    gadget.leds.set_color("RIGHT", "GREEN")

    # Gadget main entry point
    gadget.main()

    # Shutdown sequence
    gadget.sound.play_song((('E5', 'e'), ('C4', 'e')))
    gadget.leds.set_color("LEFT", "BLACK")
    gadget.leds.set_color("RIGHT", "BLACK")
