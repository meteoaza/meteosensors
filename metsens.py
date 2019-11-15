import time
from playsound import playsound
import pyttsx3
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
        self.w.positionButton.clicked.connect(self.setPosition)
        self.w.senstypeBox.activated[str].connect(lambda: self.w.topText.setText(self.w.senstypeBox.currentText()))
        self.choose_by_name = 0
        self.alarm = 1
        self.voice = pyttsx3.init()
        self.readSettings()
        self.show()

    def readSettings(self):
        try:
            if not os.path.exists('TERMINAL'):
                os.mkdir('TERMINAL')
            if not os.path.exists('LOG/'):
                os.mkdir('LOG/')
            if not os.path.exists('DATA'):
                os.mkdir('DATA')
            if not os.path.exists('metsens.conf'):
                COMs = dict.fromkeys(self.com_list)
                FRAMEs = dict.fromkeys(self.frame_list)
                self.settings = {'PROGSET': None, 'PORTSET': COMs, 'FRAMESET': FRAMEs}
                self.settings['PROGSET'] = {
                    'VOICE': 0,
                    'SOUND': 0,
                    'BOT': 0,
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
                        'SENSTYPE': 'None'
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
                        'TERMODE': None,
                        'WARNING': True,
                        'POSITION': None
                    }
                with open('metsens.conf', 'w')as file:
                    json.dump(self.settings, file, indent=4, ensure_ascii=False)
            self.settings = json.load(open('metsens.conf'))
            PROGSET = self.settings['PROGSET']
            PORTSET = self.settings['PORTSET']
            FRAMESET = self.settings['FRAMESET']
            # Add existing sensor's ports to port boxes
            port_list = ['None']
            bot_sens = []
            name_list = ['None']
            for com in PORTSET:
                name = PORTSET[com]['NAME']
                if name != 'None':
                    port_list.append(com)
                    bot_sens.append(name)
                    name_list.append(name)
            for frame in FRAMESET:
                port_box = getattr(self.w, FRAMESET[frame]['PORT'])
                name_box = getattr(self.w, FRAMESET[frame]['NAME'])
                send_button = getattr(self.w, FRAMESET[frame]['SEND'])
                value_button = getattr(self.w, FRAMESET[frame]['VALUE'])
                try:
                    port_box.activated[str].disconnect()
                    name_box.activated[str].disconnect()
                    self.connectSendButton(send_button, frame, 'disconnect')
                    self.connectValueButton(value_button, frame, 'disconnect')
                except TypeError:
                    pass
                self.connectSendButton(send_button, frame, 'connect')
                self.connectValueButton(value_button, frame, 'connect')
                port_box.activated[str].connect(lambda: self.chooseByName(False))
                name_box.activated[str].connect(lambda: self.chooseByName(True))
                port_box.clear()
                name_box.clear()
                port_box.addItems(port_list)
                name_box.addItems(name_list)
            status = dict.fromkeys(bot_sens)
            value = dict.fromkeys(bot_sens)
            self.bot_data = {'STATUS': status, 'VALUE': value}
            # Show program settings in window
            self.w.voiceCheck.setCheckState(PROGSET['VOICE'])
            self.w.soundCheck.setCheckState(PROGSET['SOUND'])
            self.w.botCheck.setCheckState(PROGSET['BOT'])
            self.w.datawriteCheck.setCheckState(PROGSET['DATAWRITE'])
            self.w.deadtimeSpin.setValue(PROGSET['DEADTIME'])
            self.say('Hello, nice to see you')
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
            'BOT': self.w.botCheck.checkState(),
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
        FRAMES = self.settings['FRAMESET']
        for frame in FRAMES:
            port_box = getattr(self.w, FRAMES[frame]['PORT'])
            FRAMES[frame]['POSITION'] = port_box.currentText()
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
            text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
            value_frame = getattr(self.w, FRAMES[frame]['VALUE'])
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
                if FRAMES[frame]['TERMODE']:
                    # sens_type = self.settings['PORTSET'][current_port]['SENSTYPE']
                    with open(f'DATA/{current_name}_{current_port}.dat', 'r')as f:
                        data = f.read()
                    previous_data = text_frame.toPlainText()
                    if data[-10:] != previous_data[-10:]:
                        text_frame.append(data)
                        value_frame.setText('Terminal Mode')
                else:
                    data = self.processData(current_port)
                    if data != text_frame.toPlainText():
                        value_frame.setText(data['VALUE'])
                        text_frame.setText(data['DATA'])
                        color = data['COLOR']
                        value_frame.setStyleSheet(f'background-color: {color}')
                    if data['COLOR'] == 'red':
                        if FRAMES[frame]['WARNING']:
                            text_frame.setStyleSheet('background: ')
                            warning = f"{current_port} {current_name} {data['STATUS']}"
                            if self.alarm == 1:
                                alarm = threading.Thread(target=self.sensorWarning, args=(warning,), daemon=True)
                                alarm.start()
                            Logs(warning).sensLog()
                        elif not FRAMES[frame]['WARNING']:
                            text_frame.setStyleSheet('background: red')
            else:
                name_box.setCurrentText('None')
                text_frame.clear()
                value_frame.setText('VALUE')
                value_frame.setStyleSheet('background-color: ')
        if self.settings['PROGSET']['BOT']:
            self.writeBotData()
        if not self.stop:
            QTimer.singleShot(1000, self.mainFrame)

    def processData(self, port):
        PORTS = self.settings['PORTSET']
        SENS = PORTS[port]['SENSTYPE']
        sens_name = PORTS[port]['NAME']
        is_dead_time = self.ifDeadTime(f"DATA/{sens_name}_{port}.dat")
        try:
            with open(f"DATA/{sens_name}_{port}.dat", 'r')as f:
                data = f.read()
            if 'reconnecting'.lower() in data:
                processed = {
                    'DATA': 'RECONNECTING...',
                    'VALUE': '-----',
                    'COLOR': 'yellow'
                }
            else:
                buf = data.split()
                visibility = ''
                cloud = ''
                wind_dir = ''
                wind_speed = ''
                temp = ''
                pres = ''
                status = 'OK'
                value = ''
                color = 'green'
                i = 0
                for item in buf:
                    if 'VIS' in item:
                        visibility = buf[i+1]
                        status = buf[i+3]
                        if 'W' in status or 'A' in status or 'E' in status:
                            color = 'red'
                        elif 'I' in status or 'S' in status:
                            color = 'yellow'
                            if '00100000000000000000' in status:
                                color = 'orange'
                    elif 'CT' in item:
                        cloud = '{} {} {}'.format(buf[i+2], buf[i+3], buf[i+4])
                        status = buf[i+5]
                        if 'W' in buf[i+1] or 'A' in buf[i+1]:
                            color = 'red'
                        elif '00000040' in status:
                            color = 'orange'
                    elif 'WIMWV' in item or 'PAMWV' in item:
                        wind = item.replace(',', ' ').split()
                        wind_dir = int(wind[1])
                        wind_speed = wind[3]
                    elif 'TU' in item:
                        temp = buf[i + 1]
                    elif 'PTB' in item:
                        pres = buf[i+1]
                    if SENS == 'MILOS':
                        if 'A' in item[1] and 'R' not in item:
                            wind = item[-5:]
                            wind_speed = int(wind[:3]) / 10
                            wind_dir = int(int(wind[3:]) * 4.66)
                        if 'P' in item[1]:
                            pres = buf[i+1]
                        elif 'TU' in item:
                            temp = buf[i][4:]
                            if temp == '':
                                temp = buf[i + 1]
                    i += 1
                if SENS == 'LT':
                    value = visibility
                elif SENS == 'CL':
                    value = cloud
                elif SENS == 'WT' or SENS =='MAWS' or SENS == 'MILOS':
                    if pres != '':
                        pres = pres + 'hPa'
                    if temp != '':
                        temp = temp + '°'
                    value = '{} / {}  {}  {}'.format(wind_dir, wind_speed, temp, pres)
                elif SENS == 'PTB':
                    value = pres
                if is_dead_time:
                    data = 'DATA FILE IS DEAD'
                    value = 'ERROR'
                    status = 'ALARM! NO VALID DATA FOUND'
                    color = 'red'
                processed = {
                    'DATA': data,
                    'VALUE': value,
                    'STATUS': status,
                    'COLOR': color
                }
        except (FileNotFoundError, IndexError, UnboundLocalError, ValueError):
            Logs(' processData ' + str(sys.exc_info())).progLog()
            processed = {
                'DATA': 'FILE NOT FOUND or SOMETHING IS WRONG',
                'VALUE': 'ERROR',
                'STATUS': '',
                'COLOR': 'red'
            }
        return processed

    def writeBotData(self):
        for port in self.settings['PORTSET']:
            name = self.settings['PORTSET'][port]['NAME']
            if name != 'None':
                data = self.processData(port)
                self.bot_data['STATUS'][name] = data['STATUS']
                self.bot_data['VALUE'][name] = data['VALUE']
                with open('DATA/bot_data.json', 'w')as f:
                    json.dump(self.bot_data, f, indent=4, ensure_ascii=False)

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

    def terminalMode(self, frame):
        FRAMES = self.settings['FRAMESET']
        port_box = getattr(self.w, FRAMES[frame]['PORT'])
        port = port_box.currentText()
        if port != 'None':
            text_frame = getattr(self.w, FRAMES[frame]['TEXT'])
            send_text = getattr(self.w, self.settings['FRAMESET'][frame]['SEND_TEXT'])
            text_to_send = send_text.text()
            if 'open' in text_to_send:
                term_mode = True
            elif 'close' in text_to_send:
                term_mode = False
            else:
                term_mode = True
            with open(f'TERMINAL/{port}_terminal', 'w')as term_file:
                term_file.write(f'{port} {text_to_send}')
            send_text.clear()
            self.settings['FRAMESET'][frame]['TERMODE'] = term_mode
            text_frame.clear()

    def disableWarning(self, frame):
        if self.settings['FRAMESET'][frame]['WARNING']:
            self.settings['FRAMESET'][frame]['WARNING'] = False
        elif not self.settings['FRAMESET'][frame]['WARNING']:
            self.settings['FRAMESET'][frame]['WARNING'] = True

    def connectSendButton(self, but, frame, act):
        if act == 'connect':
            but.clicked.connect(lambda: self.terminalMode(frame))
        elif act == 'disconnect':
            but.clicked.disconnect()

    def connectValueButton(self, but, frame, act):
        if act == 'connect':
            but.clicked.connect(lambda: self.disableWarning(frame))
        elif act == 'disconnect':
            but.clicked.disconnect()

    def ifDeadTime(self, file):
        is_dead_time = False
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%M')
            now_time = datetime.now().strftime('%M')
            time_difference = int(now_time) - int(file_time)
            if time_difference >= self.settings['PROGSET']['DEADTIME']:
                is_dead_time = True
        except FileNotFoundError:
            pass
        return is_dead_time

    def sensorWarning(self, warning):
        self.alarm = 0
        self.say(warning)
        if self.settings['PROGSET']['SOUND']:
            playsound('alarm.wav')
        self.alarm = 1

    def setPosition(self):
        FRAMES = self.settings['FRAMESET']
        for frame in FRAMES:
            port_box = getattr(self.w, FRAMES[frame]['PORT'])
            port_box.setCurrentText(FRAMES[frame]['POSITION'])

    def say(self, text):
        if self.settings['PROGSET']['VOICE']:
            voices = self.voice.getProperty('voices')
            self.voice.setProperty('voice', voices[4].id)
            self.voice.setProperty('rate', 200)
            self.voice.say(text)
            self.voice.runAndWait()

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


class Portscan():
    def __init__(self, *ports, **settings):
        self.ports_to_scan = ports
        self.settings = settings
        self.running = True

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
        try:
            while self.running:
                try:
                    with open(f'TERMINAL/{port}_terminal', 'r')as term_file:
                        term_set = term_file.readline().split()
                    if len(term_set) == 2:
                        term_port = term_set[0]
                        if term_port == port:
                            message = term_set[1]
                            ser.write(f"{message}\r\n".encode())
                            os.remove(f'TERMINAL/{port}_terminal')
                except FileNotFoundError:
                    pass
                buffer = ser.readlines()
                if len(buffer) >= 1:
                    sens_name = self.settings['PORTSET'][port]['NAME']
                    try:
                        buffer = [item.decode() for item in buffer]
                        data = [text.replace('\r', '') for text in buffer]
                        data = ''.join(data)
                    except UnicodeDecodeError:
                        data = str(sys.exc_info())
                    with open(f'DATA/{sens_name}_{port}.dat', 'w')as f:
                        f.write(data)
            else:
                ser.close()
        except Exception:
            Logs(' readWritePort ' + str(sys.exc_info())).progLog()


class Logs(MainWindow):
    def __init__(self, log):
        self.log = log
        self.t = str(datetime.now())

    def progLog(self):
        with open('LOG/prog.log', 'a')as f:
            f.write(self.t + self.log + '\n')

    def sensLog(self):
        with open('LOG/sens.log', 'a')as f:
            f.write(self.t + self.log + '\n')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
