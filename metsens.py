import time
import os
import sys
import json
import serial
import threading
from datetime import datetime, timedelta
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from metsens_design import Ui_MainWindow


class Main_Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.w = Ui_MainWindow()
        self.w.setupUi(self)
        # All necessary for settings init
        self.progset_list = ['VOICE', 'SOUND', 'SENSLOG', 'DATAWRITE']
        self.com_list = [f'COM{i}' for i in range(1, 33)]
        self.frame_list = [f'FRAME{i}' for i in range(1, 21)]
        self.w.setportBox.addItems(['None'] + self.com_list)
        self.w.baudBox.addItems(['None', '150', '300', '600', '900', '1200', '2400', '4800', '7200', '9600'])
        self.w.byteBox.addItems(['None', '5', '6', '7', '8'])
        self.w.parityBox.addItems(['None', 'NO', 'ODD', 'EVEN', 'MARK', 'SPACE'])
        self.w.stopbitBox.addItems(['None', '1', '1.5', '2'])
        self.w.senstypeBox.addItems(['None', 'LT', 'CL', 'WT', 'MAWS', 'MILOS', 'PTB'])
        self.w.applyButton.clicked.connect(self.writeSettings)
        self.w.scanButton.clicked.connect(self.initScanPort)
        self.w.resetButton.clicked.connect(self.reset)
        self.w.setportBox.activated[str].connect(self.showSettings)
        self.w.senstypeBox.activated[str].connect(lambda: self.w.topText.setText(self.w.senstypeBox.currentText()))
        self.choose_by_name = 0
        self.readSettings()
        self.show()

    def readSettings(self):
        try:
            if not os.path.exists('metsens.conf'):
                SETs = dict.fromkeys(self.progset_list)
                COMs = dict.fromkeys(self.com_list)
                FRAMEs = dict.fromkeys(self.frame_list)
                self.settings = {'PROGSET': SETs, 'PORTSET': COMs, 'FRAMESET': FRAMEs}
                self.settings['PROGSET'] = {
                    'VOICE': 0,
                    'SOUND': 0,
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
                        'NAME': f'nameBox_{i}',
                        'SEND': f'sendButton_{i}',
                        'MUTE': f'muteButton_{i}'
                    }
                    i += 1
                with open('metsens.conf', 'w')as file:
                    json.dump(self.settings, file, indent=4, ensure_ascii=False)
            self.settings = json.load(open('metsens.conf'))
            PROGSET = self.settings['PROGSET']
            PORTSET = self.settings['PORTSET']
            FRAMESET = self.settings['FRAMESET']
            # Add existing sensor's ports to port boxes
            port_list = ['None']
            name_list = ['None']
            for com in PORTSET:
                name = PORTSET[com]['NAME']
                if name != 'None':
                    port_list.append(com)
                    name_list.append(name)
            for frame in FRAMESET:
                port_box = getattr(self.w, FRAMESET[frame]['PORT'])
                name_box = getattr(self.w, FRAMESET[frame]['NAME'])
                try:
                    port_box.activated[str].disconnect()
                    name_box.activated[str].disconnect()
                except TypeError:
                    pass
                port_box.activated[str].connect(lambda: self.chooseByName(False))
                name_box.activated[str].connect(lambda: self.chooseByName(True))
                port_box.clear()
                name_box.clear()
                port_box.addItems(port_list)
                name_box.addItems(name_list)
            # Show program settings in window
            self.w.voiceCheck.setCheckState(PROGSET['VOICE'])
            self.w.soundCheck.setCheckState(PROGSET['SOUND'])
            self.w.senslogCheck.setCheckState(PROGSET['SENSLOG'])
            self.w.datawriteCheck.setCheckState(PROGSET['DATAWRITE'])
            self.w.deadtimeSpin.setValue(PROGSET['DEADTIME'])
        except Exception:
            Logs(' readSettings ' + str(sys.exc_info()), 1).progLog()

    def writeSettings(self):
        if self.w.topText.text() == '':
            name = 'None'
        else:
            name = self.w.topText.text()
        new_port = {
            'NAME': name,
            'BAUD': self.w.baudBox.currentText(),
            'BYTESIZE': self.w.byteBox.currentText(),
            'PARITY': self.w.parityBox.currentText(),
            'STOPBIT': self.w.stopbitBox.currentText(),
            'SENSTYPE': self.w.senstypeBox.currentText()
        }
        new_set = {
            'VOICE': self.w.voiceCheck.checkState(),
            'SOUND': self.w.soundCheck.checkState(),
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

    def initScanPort(self):
        PORTS = self.settings['PORTSET']
        ports_to_scan = []
        for port in PORTS:
            if PORTS[port]["NAME"] != 'None':
                ports_to_scan.append(port)
        self.port_scan = Portscan(*ports_to_scan, **self.settings)
        self.port_scan.running = True
        self.stop = False
        if self.settings['PROGSET']['DATAWRITE']:
            self.port_scan.setPorts()
        self.mainFrame()

    def mainFrame(self):
        PORTS = self.settings['PORTSET']
        FRAMES = self.settings['FRAMESET']
        clock = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        self.w.timeLabel.setText(clock)
        self.w.topText.setText(self.showNotification())
        for frame in FRAMES:
            port_box = getattr(self.w, FRAMES[frame]['PORT'])
            name_box = getattr(self.w, FRAMES[frame]['NAME'])
            current_port = port_box.currentText()
            current_name = name_box.currentText()
            if current_port != 'None' or current_name != 'None':
                if self.choose_by_name:
                    for port in PORTS:
                        if PORTS[port]['NAME'] == current_name:
                            current_port = port
                            port_box.setCurrentText(current_port)
                name_box.setCurrentText(PORTS[current_port]['NAME'])
                value_frame = getattr(self.w, FRAMES[frame]['VALUE'])
                text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
                data = self.processData(current_port)
                value_frame.setText(data['VALUE'])
                text_frame.setText(data['DATA'])
                color = data['COLOR']
                value_frame.setStyleSheet(f'background-color: {color}')
        if not self.stop:
            QTimer.singleShot(1000, self.mainFrame)

    def processData(self, port):
        PORTS = self.settings['PORTSET']
        SENS = PORTS[port]['SENSTYPE']
        try:
            with open(f"DATA/{SENS}_{port}.dat", 'r')as f:
                data = f.read()
        except FileNotFoundError:
            pass
        try:
            buf = data.split()
            if SENS == 'LT':
                value = buf[2][:-2]
                status = buf[4]
                if 'W' in status or 'A' in status or 'E' in status:
                    color = 'red'
                elif 'I' in status or 'S' in status:
                    color = 'yellow'
                else:
                    color = 'green'
            elif SENS == 'CL':
                value = buf[3]
                status = buf[6]
                color = 'green'
            elif SENS == 'WT':
                if 'WIMWV' in data:
                    buf = data.replace(',', ' ').split()
                    value = f'DD = {buf[1]} FF = {buf[3]}'
                    color = 'green'
            elif SENS =='MAWS':
                if 'PAMWV' in data:
                    buf = data.replace(',', ' ').split()
                    value = f'DD = {buf[1]} FF = {buf[3]}'
                elif 'TU' in data:
                    buf = data.split()
                    value = f'TEMP = {buf[1]}'
                color = 'green'
            processed = {
                'DATA': data,
                'VALUE': value,
                'COLOR': color
            }
        except (IndexError, UnboundLocalError):
            Logs(' processData ' + str(sys.exc_info())).progLog()
            try:
                processed = {
                    'DATA': data,
                    'VALUE': '----',
                    'COLOR': 'yellow'
                }
            except UnboundLocalError:
                Logs(' processData ' + str(sys.exc_info())).progLog()
                processed = {
                    'DATA': 'No DATA found',
                    'VALUE': 'ERROR',
                    'COLOR': 'red'
                }
        return processed

    def showNotification(self):
        try:
            now_time = datetime.now()
            log_time = datetime.fromtimestamp(os.stat('LOG/prog.log').st_mtime)
            compare_time = timedelta(minutes=1)
            if now_time - log_time <= compare_time:
                try:
                    with open('LOG/prog.log', 'r')as f:
                        log = f.readlines()[-1][27:128]
                except IndexError:
                    print('index error')
                    with open('LOG/prog.log', 'w')as f:
                        f.write('Log file is made')
            else:
                log = ''
            return log
        except FileNotFoundError:
            with open('LOG/prog.log', 'w')as f:
                f.write('Log file is made')

    def chooseByName(self, n):
        self.choose_by_name = n

    def sendMessage(self, arg):
        print(arg)

    def reset(self):
        for frame in self.settings['FRAMESET']:
            send_button = getattr(self.w, self.settings['FRAMESET'][frame]['SEND'])
            try:
                send_button.clicked.disconnect()
            except TypeError:
                pass
        self.w.timeLabel.setText('')
        try:
            self.port_scan.running = False
        except AttributeError:
            pass
        self.stop = True
        self.readSettings()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


class Portscan():
    def __init__(self, *args, **kwargs):
        self.ports_to_scan = args
        self.settings = kwargs
        if not os.path.exists('DATA'):
            os.mkdir('DATA')

    def setPorts(self):
        PORTS = self.settings['PORTSET']
        for port in self.ports_to_scan:
            try:
                if PORTS[port]['PARITY'] == 'EVEN':
                    parity = serial.PARITY_EVEN
                elif PORTS[port]['PARITY'] == 'ODD':
                    parity = serial.PARITY_ODD
                elif PORTS[port]['PARITY'] == 'NO':
                    parity = serial.PARITY_NONE
                elif PORTS[port]['PARITY'] == 'MARK':
                    parity = serial.PARITY_MARK
                elif PORTS[port]['PARITY'] == 'SPACE':
                    parity = serial.PARITY_SPACE
                else:
                    parity = 'NO'
                ser = serial.Serial(
                    port=port,
                    baudrate=int(PORTS[port]['BAUD']),
                    bytesize=int(PORTS[port]['BYTESIZE']),
                    parity=parity,
                    stopbits=int(PORTS[port]['STOPBIT']),
                    timeout=3,
                )
                sens_type = PORTS[port]['SENSTYPE']
                port_args = (ser, sens_type, port)
                scan_thread = threading.Thread(target=self.readPort, args=(*port_args,), daemon=True)
                scan_thread.start()
            except Exception:
                Logs(' scanPorts ' + str(sys.exc_info())).progLog()

    def readPort(self, *args):
        try:
            while self.running:
                ser = args[0]
                sens_type = args[1]
                port = args[2]
                if sens_type == 'CL':
                    buf = ser.read_until('\r').rstrip()
                elif sens_type == 'LT':
                    b = ser.readline()
                    buf = b + ser.read_until('\r').rstrip()
                elif sens_type == 'MILOS':
                    buf = ser.readline().strip()
                else:
                    buf = ser.readline().rstrip()
                data = buf.decode('UTF-8')
                if len(data) > 10:
                    with open(f'DATA/{sens_type}_{port}.dat', 'w')as f:
                        f.write(data)
                time.sleep(1.5)
        except Exception:
            Logs(' readPort ' + str(sys.exc_info())).progLog()


class Logs():
    def __init__(self, log, permittion=0):
        self.log = log
        self.write = permittion
        self.t = str(datetime.now())
        if not os.path.exists('LOG/'):
            os.mkdir('LOG/')

    def progLog(self):
        with open('LOG/prog.log', 'a')as f:
            f.write(self.t + self.log + '\n')

    def sensLog(self):
        if self.write:
            with open('LOG/sens.log', 'a')as f:
                f.write(self.t + self.log + '\n')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main_Window()
    sys.exit(app.exec())
