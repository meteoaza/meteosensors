# import string
# import random
import os
import sys
import json
import serial
# import threading
from datetime import datetime
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from metsens_design import Ui_MainWindow


class Main_Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.w = Ui_MainWindow()
        self.w.setupUi(self)
        # All necessary for settings init
        self.com_list = [f'COM{i}' for i in range(1, 33)]
        self.frame_list = [f'FRAME{i}' for i in range(1, 21)]
        self.progset_list = ['VOICE', 'SOUND', 'PORTLOG', 'SENSLOG', 'DATAWRITE']
        if not os.path.exists('metsens.conf'):
            COMs = dict.fromkeys(self.com_list)
            FRAMEs = dict.fromkeys(self.frame_list)
            SETs = dict.fromkeys(self.progset_list)
            self.settings = {'PROGSET': SETs, 'PORTSET': COMs, 'FRAMESET': FRAMEs}
            self.settings['PROGSET'] = {
                'VOICE': 0,
                'SOUND': 0,
                'PORTLOG': 0,
                'SENSLOG': 0,
                'DATAWRITE': 0,
                'DEADTIME': 0
            }
            for com in self.com_list:
                self.settings['PORTSET'][com] = {
                    'NAME': 'None',
                    'BAUD': 'None',
                    'BYTESIZE': 'None',
                    'PARITY': 'None',
                    'STOPBIT': 'None',
                    'SENSTYPE': 'None',
                    'SENDMES': 'None'
                }
            i = 1
            for frame in self.frame_list:
                self.settings['FRAMESET'][frame] = {
                    'VALUE': f'valueLabel_{i}',
                    'TEXT': f'portText_{i}',
                    'PORT': f'portBox_{i}',
                    'NAME': f'nameButton_{i}',
                    'SEND': f'sendButton_{i}',
                    'MUTE': f'muteButton_{i}'
                }
                i += 1
            with open('metsens.conf', 'w')as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
        self.w.setportBox.addItems(['None'] + self.com_list)
        self.w.baudBox.addItems(['None', '150', '300', '600', '900', '1200', '2400', '4800', '7200', '9600'])
        self.w.byteBox.addItems(['None', '5', '6', '7', '8'])
        self.w.parityBox.addItems(['None', 'NO', 'ODD', 'EVEN', 'MARK', 'SPACE'])
        self.w.stopbitBox.addItems(['None', '1', '1.5', '2'])
        self.w.senstypeBox.addItems(['None', 'LT', 'CL', 'WT', 'MAWS', 'MILOS'])
        self.w.applyButton.clicked.connect(self.writeSettings)
        self.w.scanButton.clicked.connect(self.scanPorts)
        self.w.resetButton.clicked.connect(self.reset)
        self.w.setportBox.activated[str].connect(self.showSettings)
        self.readSettings()
        self.show()

    def readSettings(self):
        try:
            self.settings = json.load(open('metsens.conf'))
            # Add existing sensor's ports to port boxes
            port_list = ['None']
            for com in self.settings['PORTSET']:
                if self.settings['PORTSET'][com]['NAME'] != 'None':
                    port_list.append(com)
            for frame in self.settings['FRAMESET']:
                port_box = getattr(self.w, self.settings['FRAMESET'][frame]['PORT'])
                port_box.clear()
                port_box.addItems(port_list)
            # Show program settings in window
            self.w.voiceCheck.setCheckState(self.settings['PROGSET']['VOICE'])
            self.w.soundCheck.setCheckState(self.settings['PROGSET']['SOUND'])
            self.w.portlogCheck.setCheckState(self.settings['PROGSET']['PORTLOG'])
            self.w.senslogCheck.setCheckState(self.settings['PROGSET']['SENSLOG'])
            self.w.datawriteCheck.setCheckState(self.settings['PROGSET']['DATAWRITE'])
            self.w.deadtimeSpin.setValue(self.settings['PROGSET']['DEADTIME'])
        except Exception:
            Logs(' readSettings ' + str(sys.exc_info()), 1).progLog()

    def writeSettings(self):
        new_port = {
            'NAME': self.w.topText.toPlainText(),
            'BAUD': self.w.baudBox.currentText(),
            'BYTESIZE': self.w.byteBox.currentText(),
            'PARITY': self.w.parityBox.currentText(),
            'STOPBIT': self.w.stopbitBox.currentText(),
            'SENSTYPE': self.w.senstypeBox.currentText()
        }
        new_set = {
            'VOICE': self.w.voiceCheck.checkState(),
            'SOUND': self.w.soundCheck.checkState(),
            'PORTLOG': self.w.portlogCheck.checkState(),
            'SENSLOG': self.w.senslogCheck.checkState(),
            'DATAWRITE': self.w.datawriteCheck.checkState(),
            'DEADTIME': self.w.deadtimeSpin.value()
        }
        for com in self.com_list:
            if com == self.w.setportBox.currentText():
                try:
                    self.settings['PORTSET'][com].update(new_port)
                except (AttributeError, IndexError):
                    Logs('writeSettings' + str(sys.exc_info()), 1).progLog()
        self.settings['PROGSET'].update(new_set)
        try:
            with open('metsens.conf', 'w')as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
        except Exception:
            Logs(' writeSettings ' + str(sys.exc_info()), 1).progLog()

    def showSettings(self):
        port = self.w.setportBox.currentText()
        if port != 'None':
            self.w.topText.setText(str(self.settings['PORTSET'][port]['NAME']))
            self.w.baudBox.setCurrentText(str(self.settings['PORTSET'][port]['BAUD']))
            self.w.byteBox.setCurrentText(str(self.settings['PORTSET'][port]['BYTESIZE']))
            self.w.parityBox.setCurrentText(str(self.settings['PORTSET'][port]['PARITY']))
            self.w.stopbitBox.setCurrentText(str(self.settings['PORTSET'][port]['STOPBIT']))
            self.w.senstypeBox.setCurrentText(str(self.settings['PORTSET'][port]['SENSTYPE']))
        elif port == 'None':
            self.w.topText.setText('')
            self.w.baudBox.setCurrentText('None')
            self.w.byteBox.setCurrentText('None')
            self.w.parityBox.setCurrentText('None')
            self.w.stopbitBox.setCurrentText('None')
            self.w.senstypeBox.setCurrentText('None')

    def scanPorts(self):
        PORTS = self.settings['PORTSET']
        FRAMES = self.settings['FRAMESET']
        for frame in FRAMES:
            port_box = getattr(self.w, FRAMES[frame]['PORT'])
            current_port = port_box.currentText()
            text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
            if current_port != 'None':
                name_button = getattr(self.w, FRAMES[frame]['NAME'])
                name_button.setText(PORTS[current_port]['NAME'])
                data = Portscan(current_port, **self.settings).scanPorts()
                text_frame.setText(data)
        QTimer.singleShot(2000, self.scanPorts)

    def sendMessage(self, arg):
        print(arg)

    def reset(self):
        for frame in self.settings['FRAMESET']:
            send_button = getattr(self.w, self.settings['FRAMESET'][frame]['SEND'])
            send_button.clicked.disconnect()
        self.readSettings()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


class Portscan():
    def __init__(self, port, **kwargs):
        self.port_to_scan = port
        self.settings = kwargs
        self.log_perm = self.settings['PROGSET']['PORTLOG']

    def scanPorts(self):
        PORTSET = self.settings['PORTSET']
        try:
            if PORTSET[self.port_to_scan]['PARITY'] == 'EVEN':
                parity = serial.PARITY_EVEN
            elif PORTSET[self.port_to_scan]['PARITY'] == 'ODD':
                parity = serial.PARITY_ODD
            elif PORTSET[self.port_to_scan]['PARITY'] == 'NO':
                parity = serial.PARITY_NONE
            elif PORTSET[self.port_to_scan]['PARITY'] == 'MARK':
                parity = serial.PARITY_MARK
            elif PORTSET[self.port_to_scan]['PARITY'] == 'SPACE':
                parity = serial.PARITY_SPACE
            else:
                parity = 'NO'
            ser = serial.Serial(
                port=self.port_to_scan,
                baudrate=int(PORTSET[self.port_to_scan]['BAUD']),
                bytesize=int(PORTSET[self.port_to_scan]['BYTESIZE']),
                parity=parity,
                stopbits=int(PORTSET[self.port_to_scan]['STOPBIT']),
                timeout=3,
            )
            sensor = PORTSET[self.port_to_scan]['SENSTYPE'],
            data = ser.read().until('/r')
        except Exception as e:
            Logs(' scanPorts '+ str(sys.exc_info()), self.log_perm).portLog()
            data = str(sys.exc_info())
        return data


class Logs():
    def __init__(self, log, permittion=0):
        self.log = log
        self.write = permittion
        self.t = str(datetime.now())
        if not os.path.exists('LOG/'):
            os.mkdir('LOG/')

    def progLog(self):
        if self.write:
            with open('LOG/prog.log', 'a')as f:
                f.write(self.t + self.log + '\n')

    def portLog(self):
        if self.write:
            with open('LOG/port.log', 'a')as f:
                f.write(self.t + self.log + '\n')

    def sensLog(self):
        if self.write:
            with open('LOG/sens.log', 'a')as f:
                f.write(self.t + self.log + '\n')



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main_Window()
    sys.exit(app.exec())
