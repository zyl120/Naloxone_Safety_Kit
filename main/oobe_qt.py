from PyQt5 import QtWidgets, QtCore
from ui_form import Ui_Widget
from ui_calendar_picker import Ui_Dialog
from ui_time_picker import Ui_activeHoursPicker
import os, sys


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.ui.datePickerPushButton.clicked.connect(self.date_picker)
        self.ui.activeHoursPushButton.clicked.connect(self.time_picker)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        self.ui.saveAndExitPushButton.clicked.connect(self.save_and_exit)

    def date_picker(self):
        print("INFO: date picker go")
        date_picker_dialog = QtWidgets.QDialog()
        date_picker_dialog.ui = Ui_Dialog()
        date_picker_dialog.ui.setupUi(date_picker_dialog)
        date_picker_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        date_picker_dialog.exec_()
    
    def time_picker(self):
        print("INFO: time picker go")
        time_picker_dialog = QtWidgets.QDialog()
        time_picker_dialog.ui = Ui_activeHoursPicker()
        time_picker_dialog.ui.setupUi(time_picker_dialog)
        time_picker_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        time_picker_dialog.exec_()

    def save_config_file(self):
        print("INFO: save config file")


    def save_and_exit(self):
        print("INFO: save and exit...")
        self.close()


def enter_info_window():
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())


def oobe_manager():
    # the process to first read the twilio config file
    try:
        file = open("/home/pi/Naloxone_Safety_Kit/main/twilio.txt", "r")
    except OSError:
        print("Missing file, enter OOBE")
        enter_info_window()
    with file:
        lines = file.read().splitlines()
        print("read {} lines".format(len(lines)))
        if (len(lines) != 8):
            enter_info_window()
        else:
            for line in lines:
                print(line)
    sys.exit(0)


def fork_oobe():
    pid = os.fork()
    if (pid > 0):
        os.waitpid(pid, 0)
    else:
        oobe_manager()


if __name__ == "__main__":
    enter_info_window()
