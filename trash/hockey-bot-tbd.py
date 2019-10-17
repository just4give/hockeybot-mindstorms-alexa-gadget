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
from ev3dev2.sensor.lego import UltrasonicSensor,ColorSensor
from ev3dev2.sensor import INPUT_1,INPUT_2

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

class MindstormsGadget:

    def __init__(self):
        print("Hockey Bot initialized")
        self.bat = MediumMotor(OUTPUT_C)
        self.cs = ColorSensor(INPUT_2)
        self.cs.mode = 'COL-REFLECT' 
        self.us = UltrasonicSensor(INPUT_1)
        self.drive = MoveTank(OUTPUT_A, OUTPUT_B)
        self.stop = False
        self.kickAngle = 180

    def kick(self):
        self.bat.on_for_degrees(SpeedPercent(100), self.kickAngle)
        self.kickAngle = self.kickAngle*-1

    def kickRight(self):
        self.bat.on_for_degrees(SpeedPercent(100), 180)
        time.sleep(0.5)
        self.bat.on_for_degrees(SpeedPercent(100), -180)

    def kickLeft(self):
        self.bat.on_for_degrees(SpeedPercent(100), -90)
        time.sleep(0.5)
        self.bat.on_for_degrees(SpeedPercent(100), 90)
    
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
            self.forwardMode = True
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in Direction.BACKWARD.value:
            self.drive.on_for_seconds(SpeedPercent(-speed), SpeedPercent(-speed), duration, block=is_blocking)

        if direction in (Direction.RIGHT.value + Direction.LEFT.value):
            self._turn(direction, speed)
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in Direction.STOP.value:
            self.drive.off()
            self.patrol_mode = False


    
 
if __name__ == '__main__':
    gadget = MindstormsGadget()
    
    # Gadget main entry point
    
    while True:
        gadget._move('forward', 5, 50)
        gadget.kick()
        #time.sleep(5)
        
    