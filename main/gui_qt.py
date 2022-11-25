from PyQt5 import QtWidgets, QtCore
from ui_form import Ui_Widget
import os
import sys
import configparser
import subprocess
import signal
from ui_door_close_window import Ui_door_close_main_window
#from qt_material import apply_stylesheet
import qdarktheme
from time import sleep


def gui_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


class Worker(QtCore.QObject):
    def __init__(self, function):
        super(Worker, self).__init__()
        self.function = function

    # @pyqtSlot()
    def run(self):
        print("thread go")
        #self.ui.currentTimeLineEdit.setText(QtCore.QTime().currentTime().toString("h:mm:ss AP"))
        self.function()


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self, shared_array):
        super(ApplicationWindow, self).__init__()
        self.shared_array = shared_array
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        self.ui.temperatureGroupBox.setStyleSheet(
            "QGroupBox:title {color: violet}")
        self.ui.temperatureLineEdit.setStyleSheet("color: violet")
        self.ui.fanSpeedLineEdit.setStyleSheet("color: violet")
        self.ui.naloxoneGroupBox.setStyleSheet("QGroupBox:title {color: blue}")
        self.ui.naloxoneStatusLineEdit.setStyleSheet("color:blue")
        self.ui.naloxoneExpirationDateLineEdit.setStyleSheet("color:blue")
        self.ui.serverGroupBox.setStyleSheet("QGroupBox:title {color: green}")
        self.ui.serverStatusLineEdit.setStyleSheet("color:green")
        self.ui.serverCheckLineEdit.setStyleSheet("color:green")
        self.ui.doorGroupBox.setStyleSheet("QGroupBox:title {color: red}")
        self.ui.doorArmedLineEdit.setStyleSheet("color:red")
        self.ui.doorClosedLineEdit.setStyleSheet("color:red")
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.time_updater_thread = QtCore.QThread()
        self.time_worker = Worker(self.update_time)
        self.time_worker.moveToThread(self.time_updater_thread)
        self.time_updater_thread.started.connect(self.time_worker.run)
        self.time_updater_thread.start()

        self.ui_updater_thread = QtCore.QThread()
        self.ui_worker = Worker(self.update_ui)
        self.ui_worker.moveToThread(self.ui_updater_thread)
        self.ui_updater_thread.started.connect(self.ui_worker.run)
        self.ui_updater_thread.start()

    def exit_program(self):
        os.kill(0, signal.SIGINT) # kill all processes
        self.close()

    def update_time(self):
        while True:
            self.ui.currentTimeLineEdit.setText(
                QtCore.QTime().currentTime().toString("h:mm AP"))
            sleep(1)

    def toggle_door_arm(self):
        if (self.ui.disarmPushButton.text() == "Disarm"):
            self.ui.disarmPushButton.setText("Arm")
            with self.shared_array.get_lock():
                self.shared_array[8] = 1
        else:
            self.ui.disarmPushButton.setText("Disarm")
            with self.shared_array.get_lock():
                self.shared_array[8] = 0

    def update_ui(self):
        temperature = 0
        pwm = 0
        server = 0
        naloxone_expired = 0
        naloxone_expired = 0
        door = 0
        phone = 0
        armed = 0
        year = 2000
        month = 1
        day = 20
        while True:
            with self.shared_array.get_lock():
                temperature = self.shared_array[1]
                pwm = self.shared_array[2]
                server = self.shared_array[6]
                armed = self.shared_array[8]
                naloxone_expired = self.shared_array[9]
                naloxone_overheat = self.shared_array[10]
                door = self.shared_array[3]
                phone = self.shared_array[5]
                year = self.shared_array[13]
                month = self.shared_array[14]
                day = self.shared_array[15]
                hour = self.shared_array[16]
                minute = self.shared_array[17]
            naloxone_expiration_date = QtCore.QDate(year, month, day)
            server_check_time = QtCore.QTime(hour, minute)
            self.ui.naloxoneExpirationDateLineEdit.setText(
                naloxone_expiration_date.toString("MMM dd, yy"))
            self.ui.serverCheckLineEdit.setText(server_check_time.toString("h:mm AP"))
            self.ui.temperatureLineEdit.setText(str(temperature) + " C")
            self.ui.fanSpeedLineEdit.setText(str(pwm) + " RPM")
            if (server == 0):
                self.ui.serverStatusLineEdit.setText("Down")
            else:
                self.ui.serverStatusLineEdit.setText("Connected")
            if (door == 0):
                self.ui.doorClosedLineEdit.setText("Closed")
            else:
                self.ui.doorClosedLineEdit.setText("Open")
            if (armed == 0):
                self.ui.doorArmedLineEdit.setText("Armed")
            else:
                self.ui.doorArmedLineEdit.setText("Disarmed")
            if (naloxone_expired or naloxone_overheat):
                self.ui.naloxoneStatusLineEdit.setText("Destroyed")
            else:
                self.ui.naloxoneStatusLineEdit.setText("OK")
            sleep(1)


def door_closed_window(shared_array):
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet())
    #apply_stylesheet(app, theme='dark_teal.xml')
    application = ApplicationWindow(shared_array)
    application.show()
    sys.exit(app.exec_())


def gui_manager(shared_array):
    while True:
        with shared_array.get_lock():
            door_opened = shared_array[3]
            status_code = shared_array[12]
        if (not door_opened):
            door_closed_window(shared_array)
            # door_closed_window(shared_array)
        # elif (status_code != 100):
        #     count_down_window(shared_array)
        # else:
        #     door_open_window(shared_array)


def fork_gui(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: gui_pid={}".format(pid))
    else:
        gui_pid = os.getpid()
        signal.signal(signal.SIGINT, gui_signal_handler)
        gui_manager(shared_array)
    return pid


if __name__ == "__main__":
    door_closed_window(1)
