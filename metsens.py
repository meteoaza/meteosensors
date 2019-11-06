import sys
import json
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from metsens_design import Ui_MainWindow


class Main_Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.w = Ui_MainWindow()
        self.w.setupUi(self)
        self.com_list = [
            'COM01', 'COM02', 'COM03', 'COM04', 'COM05', 'COM06', 'COM07', 'COM08',
            'COM09', 'COM10', 'COM11', 'COM12', 'COM13', 'COM14', 'COM15', 'COM16',
            'COM17', 'COM18', 'COM19', 'COM20', 'COM21', 'COM22', 'COM23', 'COM24',
            'COM25', 'COM26', 'COM27', 'COM28', 'COM29', 'COM30', 'COM31', 'COM32'
        ]
        self.w.baudBox.addItems(['None', '150', '300', '600', '900', '1200', '2400', '4800', '7200', '9600'])
        self.w.byteBox.addItems(['None', '5', '6', '7', '8'])
        self.w.parityBox.addItems(['None', 'NO', 'ODD', 'EVEN', 'MARK', 'SPACE'])
        self.w.stopbitBox.addItems(['None', '1', '1.5', '2'])
        self.w.senstypeBox.addItems(['None', 'LT', 'CL', 'WT', 'MAWS', 'MILOS'])
        self.w.setportBox.addItems(['None'] + self.com_list)
        self.w.applyButton.clicked.connect(self.writeSettings)
        self.show()
        self.readSettings()


    def readSettings(self):
        try:
            self.settings = json.load(open('metsens.conf'))
        except Exception:
            Logs(sys.exc_info()).progLog()

    def writeSettings(self):
       new = {
        'NAME': self.w.topText.toPlainText(), 'BAUD': self.w.baudBox.currentText(),
        'BYTESIZE': self.w.byteBox.currentText(), 'PARITY': self.w.parityBox.currentText(),
        'STOPBIT': self.w.stopbitBox.currentText(), 'SENSTYPE': self.w.senstypeBox.currentText()
       }
       for com in self.com_list:
            if com == self.w.setportBox.currentText():
                try:
                    self.settings[1]['PORTSET'][com].update(new)
                except (AttributeError, IndexError):
                    COMs = dict.fromkeys(self.com_list)
                    self.settings = [{'PROGSET': {}}, {'PORTSET': COMs}]
                    for com in self.com_list:
                        self.settings[1]['PORTSET'][com] = {
                            'NAME': 0, 'BAUD': 0, 'BYTESIZE': 0,
                            'PARITY': 0, 'STOPBIT': 0, 'SENSTYPE': 0}
       try:
            with open('metsens.conf', 'w')as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
       except Exception:
            Logs(sys.exc_info()).progLog()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


class Logs():
    def __init__(self, log, permittion = 0):
        self.log = log
        self.write = permittion

    def progLog(self):
        pass

    def portLog(self):
        print(self.log)
        pass

    def sensLog(self):
        pass

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main_Window()
    sys.exit(app.exec())
