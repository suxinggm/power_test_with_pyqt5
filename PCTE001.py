# -*- coding: utf-8 -*-

"""
Module implementing MainWindow.
"""
import os
import time
import datetime
import subprocess
import re
import logging
from PyQt5.QtCore import pyqtSlot,  QThread,  pyqtSignal
from PyQt5.QtWidgets import *

from Ui_PCTE001 import Ui_MainWindow
from power_control import power_on,  power_off




class RunThread(QThread):
    _log_signal = pyqtSignal(str,  str)
    _count_signal = pyqtSignal(int,  int)
    
    def __init__(self):
        super(RunThread,  self).__init__()
        self.stop_flag = False
    
    def init_params(self, host,  loops,  power_on_wtime,  power_off_wtime,  io_time,  log_path,  issue_keywords_list,  check_log_enabled,  safe_flag):
        self.host = host
        self.loops = loops
        self.power_on_wtime = power_on_wtime
        self.power_off_wtime = power_off_wtime
        self.io_time = io_time
        self.log_path = log_path
        self.issue_keywords_list = issue_keywords_list
        self.check_log_enabled = check_log_enabled
        self.safe_flag = safe_flag
    
    def check_machine(self):
        cmd = 'ping -n 2 %s' % self.host
        for i in range(20):
            if self.stop_flag:
                return False

            p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = p.stdout.read().decode('utf-8')
            regex1 = re.compile('100% loss')
            regex2 = re.compile('Destination host unreachable')
            if not regex1.findall(out) and not regex2.findall(out):
                return True
        return False

    def check_log(self):
        with open(self.log_path, 'r',  encoding='utf-8') as f:
            for line in f:
                for key_word in self.issue_keywords_list: 
                    key_word = key_word.strip()
                    if self.stop_flag:
                        return False
                    if key_word in line:
                        self._log_signal.emit("'%s' found in the log, test aborted!!!" % key_word,  'error')
                        self._log_signal.emit(line,  'error')
                        return False
        return True

    def wait_seconds(self, seconds):
        for second in range(seconds):
            if self.stop_flag:
                return False
            time.sleep(1)
        return True

    def power_cycle_test(self):
        succeed_times = 0
        for loop in range(1,  self.loops + 1):
            if self.stop_flag:
                break

            if self.safe_flag:
                self._log_signal.emit("Safe_Power_Cycle_Test: Begin # %d" % loop,  'flag')
                self._log_signal.emit("Shutdown host %s" % self.host,  'info')
                if 0 != subprocess.call("shutdown -s -m \\%s" % self.host, shell=True):
                    self._log_signal.emit("Remote shutdown failed.",  'error')
                    break
                self._log_signal.emit("Wait host %s shutdown" % self.host,  'info')
                self.wait_seconds(30)
                self._log_signal.emit("Power off",  'info')
                if not power_off():
                    self._log_signal.emit("Safe Power off failed.",  'error')
                    break
            else:
                self._log_signal.emit("Unsafe_Power_Cycle_Test: Begin # %d" % loop,  'flag')
                self._log_signal.emit("Power off",  'info')
                if not power_off():
                    self._log_signal.emit("Unsafe Power off failed.",  'error')
                    break
            
            self._log_signal.emit("Power off finished.",  'info')
            
            self._log_signal.emit("Start waiting %d seconds" % self.power_off_wtime,  'info')
            if not self.wait_seconds(self.power_off_wtime):
                break
            
            self._log_signal.emit("Power on",  'info')
            if not power_on():
                self._log_signal.emit("Power on failed.",  'error')
                break
            
            self._log_signal.emit("Power on finished.",  'info')
            
            self._log_signal.emit("Start waiting %d seconds" % self.power_on_wtime,  'info')
            if not self.wait_seconds(self.power_on_wtime):
                break
            
            self._log_signal.emit("====>Check host online or not after power on",  'info')
            if not self.check_machine():
                self._log_signal.emit("Host is offline.",  'error')
                if not self.check_log_enabled:
                    self._log_signal.emit("Do not need to check serial log.",  'info')
                else:    
                    if not self.check_log():
                        break
                    else:
                        self._log_signal.emit("No significant keyword found, force shutdown and continue the test!!!",  'warning')
                break
            else:
                self._log_signal.emit("Host is online now.",  'info')
                succeed_times += 1
                self._log_signal.emit("Start to run IO about %d seconds" % self.io_time,  'info')
                if not self.wait_seconds(self.io_time):
                    break
                self._log_signal.emit("IO done.",  'info')
                
                self._log_signal.emit("====>Check host status again after IO is done",  'info')
                if not self.check_machine():
                    self._log_signal.emit("Host is offline after IO.",  'error')
                    break
                else:
                    self._log_signal.emit("host is still online after IO.",  'info')
                    if not self.check_log_enabled:
                        self._log_signal.emit("Do not need to check serial log.",  'info')
                    else:
                        if not self.check_log():
                            break
                
                self._log_signal.emit("Test loop end",  'info')

            self._count_signal.emit(loop,  succeed_times)
            
        self._log_signal.emit("Test exit!",  'info')
        return True

    def run(self):
        self.stop_flag = False
        self.power_cycle_test()
    
    def stop(self):
        self.stop_flag = True
        

class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Class documentation goes here.
    """
    def __init__(self, parent=None):
        """
        Constructor
        
        @param parent reference to the parent widget
        @type QWidget
        """
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.init_default_value()
        self.run_thread = RunThread()
        self.run_thread._log_signal.connect(self.logger)
        self.run_thread._count_signal.connect(self.count)
        self.run_thread.finished.connect(self.thread_finished)
        self.log_information_init()
    
    def init_default_value(self):
        self.lineEdit.setPlaceholderText("Host IP address")
        self.lineEdit.setText("192.168.1.100")
        self.lineEdit_2.setPlaceholderText("Power cycle loops")
        self.lineEdit_2.setText("100")
        self.lineEdit_3.setPlaceholderText("Run IO time")
        self.lineEdit_3.setText("60")
        self.lineEdit_4.setPlaceholderText("Power off wait time")
        self.lineEdit_4.setText("10")
        self.lineEdit_5.setPlaceholderText("Power on wait time")
        self.lineEdit_5.setText("60")
        self.lineEdit_6.setPlaceholderText("Click 'Select File' button and select one")
        self.lineEdit_7.setPlaceholderText("should split key words with ','")
        self.radioButton.setChecked(True)
        self.textBrowser.setPlaceholderText("Unsafe Power Cycle Test")

    @pyqtSlot()
    def on_radioButton_clicked(self):
        self.textBrowser.clear()
        self.textBrowser.setPlaceholderText("Unsafe Power Cycle Test")
    
    def on_radioButton_2_clicked(self):
        self.textBrowser.clear()
        self.textBrowser.setPlaceholderText("Safe Power Cycle Test")
        
    def closeEvent(self,  event):
        # self.run_thread.stop()
        self.run_thread.terminate()

    def thread_finished(self):
        self.enable_widget()
        
    def enable_widget(self):
        self.lineEdit.setDisabled(False)
        self.lineEdit_2.setDisabled(False)
        self.lineEdit_3.setDisabled(False)
        self.lineEdit_4.setDisabled(False)
        self.lineEdit_5.setDisabled(False)
        self.lineEdit_6.setDisabled(False)
        self.lineEdit_7.setDisabled(False)
        self.pushButton_2.setDisabled(False)
        self.pushButton_3.setDisabled(False)
        self.pushButton_5.setDisabled(False)
        self.pushButton_6.setDisabled(False)
        self.checkBox.setDisabled(False)
        self.radioButton.setDisabled(False)
        self.radioButton_2.setDisabled(False)
        
    def disable_widget(self):
        self.lineEdit.setDisabled(True)
        self.lineEdit_2.setDisabled(True)
        self.lineEdit_3.setDisabled(True)
        self.lineEdit_4.setDisabled(True)
        self.lineEdit_5.setDisabled(True)
        self.lineEdit_6.setDisabled(True)
        self.lineEdit_7.setDisabled(True)
        self.pushButton_2.setDisabled(True)
        self.pushButton_3.setDisabled(True)
        self.pushButton_5.setDisabled(True)
        self.pushButton_6.setDisabled(True)
        self.checkBox.setDisabled(True)
        self.radioButton.setDisabled(True)
        self.radioButton_2.setDisabled(True) 
    
    def validate_host(self,  host):
        a = host.split('.')
        if len(a) != 4:
            return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True
        
    @pyqtSlot()
    def on_lineEdit_editingFinished(self):
        if not self.validate_host(self.lineEdit.text()):
            QMessageBox.critical(self,  "Error",  "Host is invalid")
            self.lineEdit.clear()
    
    @pyqtSlot()
    def on_lineEdit_2_editingFinished(self):
        if not self.lineEdit_2.text().isdigit():
            QMessageBox.critical(self,  "Error",  "Loops should be an integer")
            self.lineEdit_2.clear()

    @pyqtSlot()
    def on_lineEdit_3_editingFinished(self):
        if not self.lineEdit_3.text().isdigit():
            QMessageBox.critical(self,  "Error",  "time should be an integer")
            self.lineEdit_3.clear()

    @pyqtSlot()
    def on_lineEdit_4_editingFinished(self):
        if not self.lineEdit_4.text().isdigit():
            QMessageBox.critical(self,  "Error",  "time should be an integer")
            self.lineEdit_4.clear()
    
    @pyqtSlot()
    def on_lineEdit_5_editingFinished(self):
        if not self.lineEdit_5.text().isdigit():
            QMessageBox.critical(self,  "Error",  "time should be an integer")
            self.lineEdit_5.clear()


    @pyqtSlot()
    def on_pushButton_4_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        # self.run_thread.quit()
        self.run_thread.stop()
        # self.enable_widget()
        
    @pyqtSlot()
    def on_pushButton_3_clicked(self):
        """
        Slot documentation goes here.
        """
        # Initial UI
        if (not os.path.exists("power_control.exe")) or (not os.path.exists("usb_relay_device.dll")):
            QMessageBox.critical(self,  "Error",  "power control lib is not exsit.")
            # return False

        self.disable_widget()
        self.count_clear()
        self.textBrowser.clear()
        
        host = self.lineEdit.text()
        loops = int(self.lineEdit_2.text())
        io_time = int(self.lineEdit_3.text())
        power_off_wtime = int(self.lineEdit_4.text())
        power_on_wtime = int(self.lineEdit_5.text())
        log_path = self.lineEdit_6.text()
        issue_keywords_list = self.lineEdit_7.text().split(',')
        check_log_enabled = self.checkBox.isChecked()
        if self.radioButton.isChecked():
            safe_flag = False
        else:
            safe_flag = True
        
        self.run_thread.init_params(host,  loops,  power_on_wtime,  power_off_wtime,  io_time,  log_path,  issue_keywords_list,  check_log_enabled,  safe_flag)
        self.run_thread.start()
        
    @pyqtSlot()
    def on_pushButton_2_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        if (not os.path.exists("power_control.exe")) or (not os.path.exists("usb_relay_device.dll")):
            QMessageBox.critical(self,  "Error",  "power control lib is not exsit.")
            return False
            # self.logger("power control lib is not exsit.",  'error')
            
        if power_on():
            self.logger("Power on successfully",  'info')
        else:
            self.logger("Power on failed",  'error')
    
    @pyqtSlot()
    def on_pushButton_5_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        if (not os.path.exists("power_control.exe")) or (not os.path.exists("usb_relay_device.dll")):
            QMessageBox.critical(self,  "Error",  "power control lib is not exsit.")
            return False
            
        if power_off():
            self.logger("Power off successfully",  'info')
        else:
            self.logger("Power off failed",  'error')
    
    @pyqtSlot(bool)
    def on_checkBox_clicked(self, checked):
        """
        Slot documentation goes here.
        
        @param checked DESCRIPTION
        @type bool
        """
        # TODO: not implemented yet
        self.serial_log_filename = self.lineEdit_6.text()
        if checked:
            if not os.path.isfile(self.serial_log_filename):
                QMessageBox.warning(self,  "Warning",  "Please select a valid serial log")
                self.checkBox.setCheckState(0)
    
    @pyqtSlot()
    def on_pushButton_6_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        self.serial_log_filename = QFileDialog.getOpenFileName()[0]
        self.lineEdit_6.setText(self.serial_log_filename)

    def log_information_init(self):
        logfile_name = ".\debug.log"
        logging.basicConfig(filename=logfile_name, filemode='w', level=logging.INFO)

    def logger(self,  information,  level):
        log_information = "[%s] %s" % (datetime.datetime.now(),  information)
        if level == 'flag':
            self.textBrowser.append("<span style='background: blue'><font color=white>%s</font></span>" % log_information)
        elif level == 'error':
            self.textBrowser.append("<font color=red>%s</font>" % log_information)
        elif level == 'warning':
            self.textBrowser.append("<font color=orange>%s</font>" % log_information)
        else:
            self.textBrowser.append("%s" % log_information)
        logging.info(log_information)
    
    def count(self,  total_run_times,  succeed_times):
        self.lcdNumber.display(total_run_times)
        self.lcdNumber_2.display(succeed_times)
    
    def count_clear(self):
        self.lcdNumber.display(0)
        self.lcdNumber_2.display(0)
        

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
