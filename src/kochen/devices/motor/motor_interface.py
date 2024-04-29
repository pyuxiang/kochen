#!/usr/bin/env python3
# Justin, 2022-10-17
# Wrapper to different motor controllers

# Controller variety 1 using a RS232-USB serial adapter
import kochen.devices.motor.motorcontroller as mc1
dev1 = "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0"
mot1 = mc1.MotorController(dev1)

# Monkey patching to match with MotorController interface
mc1.RotatingAxes.set_on = mc1.RotatingAxes.on
mc1.RotatingAxes.set_off = mc1.RotatingAxes.off
mc1.RotatingAxes.set_position = mc1.RotatingAxes.go
mc1.RotatingAxes.set_position_blocking = mc1.RotatingAxes.go_wait
mc1.RotatingAxes.set_position_degree = mc1.RotatingAxes.go_deg
mc1.RotatingAxes.get_position_degree = mc1.RotatingAxes.get_angle

# Controls QWPs
qwp586 = mc1.RotatingAxes(mot1, 8, 2000)
qwp1310 = mc1.RotatingAxes(mot1, 6, 2000)

# Controller variety 2 using direct motor driver
import kochen.devices.motor.motordriver as mc2
dev2 = "/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Stepper_Motor_Driver_SMD-QO06-if00"
mot2 = mc2.MotorDriver(dev2)

# Controls HWPs
hwp586 = mot2.get_controller(0)
hwp1310 = mot2.get_controller(1)
hwp586.initialize()
hwp1310.initialize()
