
import json
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from save_window import  Ui_Dialog
import functions as f

class SecondWindow(QtWidgets.QMainWindow, Ui_Dialog):
    second_closed = QtCore.pyqtSignal()
    def __init__(self):
        super(SecondWindow, self).__init__()
        self.setupUi(self)

    def closeEvent(self, event):
        self.second_closed.emit()
        super(SecondWindow, self).closeEvent(event)

class Ui_MainWindow(object):
    closed = QtCore.pyqtSignal()
    def setupUi(self, MainWindow):
        icon_path = self.resource_path("parserico.ico")

        plus_ico = self.resource_path("bl.png")

        icon = QIcon(icon_path)
        MainWindow.setWindowIcon(icon)
        MainWindow.setObjectName("MainWindow")
        MainWindow.setFixedSize(580, 590)
        MainWindow.setToolButtonStyle(QtCore.Qt.ToolButtonFollowStyle)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.btnStart = QtWidgets.QPushButton(self.centralwidget)
        self.btnStart.setGeometry(QtCore.QRect(200, 520, 181, 41))
        self.btnStart.setObjectName("btnStart")
        self.btnStart.clicked.connect(func.find_model_on_site)

        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(20, 20, 211, 16))
        self.label.setObjectName("label")

        self.textBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(20, 50, 541, 400))
        self.textBrowser.setObjectName("textBrowser")

        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(20, 470, 161, 16))
        self.label_2.setObjectName("label_2")

        self.label_process = QtWidgets.QLabel(self.centralwidget)
        self.label_process.setGeometry(QtCore.QRect(20, 490, 161, 16))
        self.label_process.setObjectName("label_process")

        self.btnAdd = QtWidgets.QPushButton(self.centralwidget)
        self.btnAdd.setGeometry(QtCore.QRect(180, 463, 31, 31))
        self.btnAdd.clicked.connect(self.OpenSaveWindow)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnAdd.sizePolicy().hasHeightForWidth())
        self.btnAdd.setSizePolicy(sizePolicy)
        self.btnAdd.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(plus_ico), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btnAdd.setIcon(icon)
        self.btnAdd.setIconSize(QtCore.QSize(50, 50))
        self.btnAdd.setAutoDefault(False)
        self.btnAdd.setDefault(False)
        self.btnAdd.setFlat(True)
        self.btnAdd.setObjectName("btnAdd")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.secondWindow = SecondWindow()
        self.PrintAllModel()
        self.secondWindow.second_closed.connect(self.PrintAllModel)
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Парсер Onliner"))
        self.btnStart.setText(_translate("MainWindow", "Запустить парсер"))
        self.label.setText(_translate("MainWindow", "Поиск будет по следующим моделям:"))
        self.label_2.setText(_translate("MainWindow", "Добавить модели для поиска"))
        # self.label_process.setText(_translate("MainWindow", "Добавить модели для поиска"))

    def OpenSaveWindow(self):
        self.secondWindow.show()

    def PrintAllModel(self):
        with open("search.json", 'r', encoding='utf-8') as f:
            searchlist = json.load(f)
            formatted_json = json.dumps(searchlist, indent=4, ensure_ascii=False)  # Преобразуем в читаемый формат
            # Подсвечиваем ключи и значения
            formatted_json = formatted_json.replace(' ', '&nbsp;').replace('\n', '<br>')
            formatted_json = formatted_json.replace('{', '<span style="color: blue;">{</span>')
            formatted_json = formatted_json.replace('}', '<span style="color: blue;">}</span>')
            formatted_json = formatted_json.replace('[', '<span style="color: red;">[</span>')
            formatted_json = formatted_json.replace(']', '<span style="color: red;">]</span>')

            self.textBrowser.setHtml(f'<pre style="font-family: Consolas; font-size: 12px;">{formatted_json}</pre>')
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)



if __name__ == "__main__":
    import sys
    import os




    try :
        error_list = []
        func = f.Func(error_list)
        app = QtWidgets.QApplication(sys.argv)
        MainWindow = QtWidgets.QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(MainWindow)
        MainWindow.show()
        sys.exit(app.exec_())

    except Exception as e:
        QtWidgets.QMessageBox.information(None, "Ошибка", e)
