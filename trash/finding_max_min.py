#!/usr/bin/python
# coding: utf-8

from time   import time, sleep

from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.motor import OUTPUT_A, OUTPUT_B, OUTPUT_C, MoveTank, SpeedPercent, MediumMotor,LargeMotor
from ev3dev2.sensor.lego import UltrasonicSensor,ColorSensor
from ev3dev2.sensor import INPUT_1,INPUT_2

left_motor = LargeMotor(OUTPUT_B) 
right_motor = LargeMotor(OUTPUT_A)
col= ColorSensor(INPUT_2)	 
col.mode = 'COL-REFLECT'

def run():
  left_motor.run_direct(duty_cycle_sp=30)
  right_motor.run_direct(duty_cycle_sp=30)
  max_ref = 0
  min_ref = 100
  end_time = time() + 5
  while time() < end_time:
    read = col.value()
    if max_ref < read:
      max_ref = read
    if min_ref > read:
      min_ref = read
  left_motor.stop()
  right_motor.stop()
  print ('Max: ' + str(max_ref))
  print ('Min: ' + str(min_ref))
  sleep(1)

run()