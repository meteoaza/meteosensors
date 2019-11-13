import time
import os
import sys
import json
import serial
import threading
from datetime import datetime, timedelta
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, Qt
from metsens_design import Ui_MainWindow


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.w = Ui_MainWindow()
        self.w.setupUi(self)
        # All necessary for settings init
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
        self.w.setportBox.currentIndexChanged.connect(self.showSettings)
        self.w.senstypeBox.activated[str].connect(lambda: self.w.topText.setText(self.w.senstypeBox.currentText()))
        self.choose_by_name = 0
        self.readSettings()
        self.show()
        global from_port
        from_port = None

    def readSettings(self):
        try:
            if not os.path.exists('metsens.conf'):
                COMs = dict.fromkeys(self.com_list)
                FRAMEs = dict.fromkeys(self.frame_list)
                self.settings = {'PROGSET': None, 'PORTSET': COMs, 'FRAMESET': FRAMEs}
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
                        'PORTMODE': 'R',
                        'SENDMES': 'None'
                    }
                for frame in self.frame_list:
                    i = frame[5:]
                    self.settings['FRAMESET'][frame] = {
                        'PORT': f'portBox_{i}',
                        'NAME': f'nameBox_{i}',
                        'VALUE': f'valueButton_{i}',
                        'TEXT': f'portText_{i}',
                        'SEND': f'sendButton_{i}',
                        'SEND_TEXT': f'sendLine_{i}',
                        'TERMODE': False
                    }
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
                self.connectSendButton(getattr(self.w, FRAMESET[frame]['SEND']), frame)
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
                self.w.topText.setText('Settings saved')
                self.w.setportBox.setCurrentText('None')
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
        self.port_scan.port_mode = 'R'
        self.stop = False
        if self.settings['PROGSET']['DATAWRITE']:
            self.port_scan.setPorts()
        self.mainFrame()

    def mainFrame(self):
        global from_port
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
            if current_name != 'None':
                if self.choose_by_name:
                    for port in PORTS:
                        if PORTS[port]['NAME'] == current_name:
                            current_port = port
                            port_box.setCurrentText(current_port)
            if current_port != 'None':
                name_box.setCurrentText(PORTS[current_port]['NAME'])
                value_frame = getattr(self.w, FRAMES[frame]['VALUE'])
                text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
                if FRAMES[frame]['TERMODE']:
                    print('termode', from_port)
                    if from_port:
                        sens_type = self.settings['PORTSET'][current_port]['SENSTYPE']
                        with open(f'DATA/{sens_type}_{current_port}.dat', 'r')as f:
                            data = f.read()
                        if data != text_frame.toPlainText():
                            text_frame.setText(data)
                            print('text differs')
                else:
                    data = self.processData(current_port)
                    if data != text_frame.toPlainText():
                        if data['VALUE'] != 'OLD':
                            value_frame.setText(data['VALUE'])
                            text_frame.setText(data['DATA'])
                            color = data['COLOR']
                            value_frame.setStyleSheet(f'background-color: {color}')
                        else:
                            old_value = value_frame.text()
                            value_frame.setText(old_value)
                            text_frame.setText(data['DATA'])
                            color = data['COLOR']
                            value_frame.setStyleSheet(f'background-color: {color}')
            else:
                port_box.setCurrentText('None')
                name_box.setCurrentText('None')
        if not self.stop:
            QTimer.singleShot(1000, self.mainFrame)

    def processData(self, port):
        PORTS = self.settings['PORTSET']
        SENS = PORTS[port]['SENSTYPE']
        try:
            with open(f"DATA/{SENS}_{port}.dat", 'r')as f:
                data = f.read()
            if 'reconnecting'.upper() in data:
                processed = {
                    'DATA': 'reconnecting',
                    'VALUE': '-----',
                    'COLOR': 'yellow'
                }
            else:
                buf = data.split()
                e_index = 1
                if SENS == 'LT':
                    if 'VIS' in data:
                        for element in buf:
                            if 'VIS' in element:
                                e_index = buf.index(element)
                        value = buf[e_index + 1][:-2]
                        status = buf[e_index + 3]
                        if 'W' in status or 'A' in status or 'E' in status:
                            color = 'red'
                        elif 'I' in status or 'S' in status:
                            color = 'yellow'
                            if '00100000000000000000' in status:
                                color = 'orange'
                        else:
                            color = 'green'
                    else:
                        value = 'OLD'
                        color = 'lightgreen'
                elif SENS == 'CL':
                    if 'CT' in data:
                        for element in buf:
                            if 'CT' in element:
                                e_index = buf.index(element)
                        value = f'{buf[e_index + 2]}  {buf[e_index + 3]}  {buf[e_index + 4]}'
                        status = buf[e_index + 5]
                        if 'W' in buf[e_index + 1] or 'A' in buf[e_index + 1]:
                            color = 'red'
                        elif '00000040' in status:
                            color = 'orange'
                        else:
                            color = 'green'
                    else:
                        value = 'OLD'
                        color = 'lightgreen'
                elif SENS == 'WT':
                    if 'WIMWV' in data or 'TU' in data:
                        if 'WIMWV' in data:
                            buf = data.replace(',', ' ').split()
                            value = f'{buf[1]} // {buf[3]}'
                            color = 'green'
                        else:
                            value = 'OLD'
                            color = 'yellow'
                    else:
                        value = 'OLD'
                        color = 'lightgreen'
                elif SENS == 'MAWS':
                    if 'PAMWV' in data or 'TU' in data:
                        if 'PAMWV' in data:
                            buf = data.replace(',', ' ').split()
                            value = f'{buf[1]} // {buf[3]}'
                            color = 'green'
                        elif 'TU' in data:
                            buf = data.split()
                            value = f'TEMP = {buf[1]}'
                            color = 'green'
                    else:
                        value = 'OLD'
                        color = 'lightgreen'
                else:
                    data = 'No DATA found'
                    value = 'ERROR'
                    color = 'red'
                processed = {
                    'DATA': data,
                    'VALUE': value,
                    'COLOR': color
                }
        except (FileNotFoundError, IndexError, UnboundLocalError):
            Logs(' processData ' + str(sys.exc_info())).progLog()
            processed = {
                'DATA': 'FILE NOT FOUND or SOMETHING IS WRONG',
                'VALUE': 'ERROR',
                'COLOR': 'red'
            }
        return processed

    def terminalMode(self, frame):
        global from_port
        FRAMES = self.settings['FRAMESET']
        port_box = getattr(self.w, FRAMES[frame]['PORT'])
        port = port_box.currentText()
        text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
        send_text = getattr(self.w, self.settings['FRAMESET'][frame]['SEND_TEXT'])
        text = send_text.text()
        if 'open' in text:
            self.settings['FRAMESET'][frame]['TERMODE'] = True
            self.settings['PORTSET'][port]['PORTMODE'] = 'W'
            self.from_port = False
            text_frame.clear()
        elif 'close' in text:
            sens_type = self.settings['PORTSET'][port]['SENSTYPE']
            with open(f'DATA/{sens_type}_{port}.dat', 'w')as f:
                f.write('RECONNECTING...')
            self.settings['FRAMESET'][frame]['TERMODE'] = False
            text_frame.clear()
        self.settings['PORTSET'][port]['SENDMES'] = text
        self.port_scan.settings = self.settings
        send_text.clear()
        from_port = False

    def showNotification(self):
        try:
            now_time = datetime.now()
            log_time = datetime.fromtimestamp(os.stat('LOG/prog.log').st_mtime)
            compare_time = timedelta(minutes=1)
            if now_time - log_time < compare_time:
                try:
                    with open('LOG/prog.log', 'r')as f:
                        log = f.readlines()[-1]
                except (UnboundLocalError, IndexError):
                    log = 'Log file is made\n'
                    with open('LOG/prog.log', 'w')as f:
                        f.write(log)
            else:
                log = ''
            return log
        except FileNotFoundError:
            with open('LOG/prog.log', 'w')as f:
                f.write('Log file is made\n')

    def chooseByName(self, n):
        self.choose_by_name = n

    def connectSendButton(self, but, frame):
        but.clicked.connect(lambda: self.terminalMode(frame))

    def reset(self):
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

    def fromPort(self):
        global from_port
        from_port = True


class Portscan():
    def __init__(self, *ports, **settings):
        self.ports_to_scan = ports
        self.settings = settings
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
                    timeout=2,
                )
                scan_thread = threading.Thread(target=self.readWritePort, args=(ser, port,), daemon=True)
                scan_thread.start()
            except Exception:
                Logs(' scanPorts ' + str(sys.exc_info())).progLog()

    def readWritePort(self, ser, port):
        sens_type = self.settings['PORTSET'][port]['SENSTYPE']
        try:
            while self.running:
                if self.settings['PORTSET'][port]['PORTMODE'] == 'R':
                    buffer = ser.readlines()
                    if len(buffer) >= 1:
                        buffer = [item.decode() for item in buffer]
                        data = [text.replace('\r', '') for text in buffer]
                        data = ''.join(data)
                        with open(f'DATA/{sens_type}_{port}.dat', 'w')as f:
                            f.write(data)
                elif self.settings['PORTSET'][port]['PORTMODE'] == 'W':
                    if 'close' in self.settings['PORTSET'][port]['SENDMES']:
                        self.settings['PORTSET'][port]['PORTMODE'] = 'R'
                    if self.settings['PORTSET'][port]['SENDMES'] != '':
                        ser.write(f"{self.settings['PORTSET'][port]['SENDMES']}\r\n".encode())
                        self.settings['PORTSET'][port]['SENDMES'] = ''
                        time.sleep(0.2)
                    buffer = ser.readlines()
                    while buffer:
                        data = [item.decode() for item in buffer]
                        data = [text.replace('\r', '') for text in data]
                        data = ''.join(data)
                        with open(f'DATA/{sens_type}_{port}.dat', 'a')as f:
                            f.write(data)
                        buffer = ser.readlines()
                    else:
                        win = MainWindow
                        win.fromPort(MainWindow)
                        time.sleep(0.5)
            else:
                ser.close()
        except Exception:
            Logs(' readWritePort ' + str(sys.exc_info())).progLog()


class Logs(MainWindow):
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
    window = MainWindow()
    sys.exit(app.exec())
