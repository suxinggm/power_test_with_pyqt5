@echo off
power_control.exe open 1
ping -n 2 127.0.0.1>nul
power_control.exe close 1