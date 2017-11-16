# -*- coding: utf-8 -*-

import subprocess


power_on_pc = 'PowerOn.bat'
power_off_pc = 'PowerOff.bat'

# def power_on():
    # if 0 != subprocess.call("power_control.exe open 2", shell=True):
        # return False
    # if 0 != subprocess.call("ping -n 2 127.0.0.1>nul", shell=True):
        # return False
    # if 0 != subprocess.call("power_control.exe close 2", shell=True):
        # return False
    # return True   

# def power_off():
    # if 0 != subprocess.call("power_control.exe open 1", shell=True):
        # return False
    # if 0 != subprocess.call("ping -n 2 127.0.0.1>nul", shell=True):
        # return False
    # if 0 != subprocess.call("power_control.exe close 1", shell=True):
        # return False
    # return True

def power_on():
    res_on = subprocess.call(power_on_pc, shell=True)
    if res_on == 0:
        return True
    else:
        return False

def power_off():
    res_off = subprocess.call(power_off_pc, shell=True)
    if res_off == 0:
        return True
    else:
        return False
