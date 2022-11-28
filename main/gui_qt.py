from PyQt5 import QtWidgets, QtCore, QtGui
from ui_form import Ui_Widget
import os
import sys
import configparser
import subprocess
import signal
from ui_door_close_window import Ui_door_close_main_window
from time import sleep


def gui_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def handleVisibleChanged():
    if not QtGui.QGuiApplication.inputMethod().isVisible():
        return
    for w in QtGui.QGuiApplication.allWindows():
        if w.metaObject().className() == "QtVirtualKeyboard::InputView":
            keyboard = w.findChild(QtCore.QObject, "keyboard")
            if keyboard is not None:
                r = w.geometry()
                r.moveTop(keyboard.property("y"))
                w.setMask(QtGui.QRegion(r))
                return


class Worker(QtCore.QThread):
    update_door = QtCore.pyqtSignal(bool, bool)
    update_temperature = QtCore.pyqtSignal(int, int, bool)
    update_server = QtCore.pyqtSignal(bool, QtCore.QTime)
    update_naloxone = QtCore.pyqtSignal(bool, QtCore.QDate)
    update_time = QtCore.pyqtSignal(QtCore.QTime)

    def __init__(self, shared_array):
        super(Worker, self).__init__()
        self.shared_array = shared_array

    def run(self):
        over_temperature = False
        door = False
        disarmed = False
        temperature = 0
        pwm = 0
        naloxone_expired = False
        naloxone_overheat = False
        year = 2000
        month = 1
        day = 20
        server = False
        hour = 0
        minute = 0
        while True:
            with self.shared_array.get_lock():
                over_temperature = self.shared_array[0]
                door = self.shared_array[3]
                disarmed = self.shared_array[8]
                temperature = self.shared_array[1]
                pwm = self.shared_array[2]
                naloxone_expired = self.shared_array[9]
                naloxone_overheat = self.shared_array[10]
                year = self.shared_array[13]
                month = self.shared_array[14]
                day = self.shared_array[15]
                server = self.shared_array[6]
                hour = self.shared_array[16]
                minute = self.shared_array[17]
            self.update_door.emit(door, not disarmed)
            self.update_temperature.emit(temperature, pwm, over_temperature)
            self.update_server.emit(server, QtCore.QTime(hour, minute))
            self.update_naloxone.emit(
                not naloxone_expired and not naloxone_overheat, QtCore.QDate(year, month, day))
            self.update_time.emit(QtCore.QTime().currentTime())
            sleep(1)


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self, shared_array):
        super(ApplicationWindow, self).__init__()
        self.active_hour_start = QtCore.QTime(8, 0, 0)
        self.active_hour_end = QtCore.QTime(18, 0, 0)
        self.shared_array = shared_array
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        temperatureLimit = QtGui.QIntValidator()
        temperatureLimit.setRange(0, 99)
        self.ui.absoluteMaximumTemperatureLineEdit.setValidator(temperatureLimit)
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.ui.homePushButton.clicked.connect(self.goto_home)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        self.ui.unlockSettingsPushButton.clicked.connect(
            self.lock_unlock_settings)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        self.ui.replaceNaloxonePushButton.clicked.connect(
            self.replace_naloxone)
        self.load_settings()
        self.lock_settings()
        self.goto_home()

        self.get_shared_array_worker = Worker(self.shared_array)
        self.get_shared_array_worker.update_door.connect(self.update_door_ui)
        self.get_shared_array_worker.update_temperature.connect(
            self.update_temperature_ui)
        self.get_shared_array_worker.update_server.connect(
            self.update_server_ui)
        self.get_shared_array_worker.update_naloxone.connect(
            self.update_naloxone_ui)
        self.get_shared_array_worker.update_time.connect(self.update_time_ui)
        self.get_shared_array_worker.start()

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        self.ui.twilioSIDLineEdit.setText(config["twilio"]["twilio_sid"])
        self.ui.twilioTokenLineEdit.setText(config["twilio"]["twilio_token"])
        self.ui.twilioPhoneNumberLineEdit.setText(
            config["twilio"]["twilio_phone_number"])
        self.ui.emergencyPhoneNumberLineEdit.setText(
            config["emergency_info"]["emergency_phone_number"])
        self.ui.emergencyAddressLineEdit.setText(
            config["emergency_info"]["emergency_address"])
        self.ui.emergencyMessageLineEdit.setText(
            config["emergency_info"]["emergency_message"])
        naloxone_expiration_date = QtCore.QDate.fromString(
            config["naloxone_info"]["naloxone_expiration_date"])
        self.ui.calendarWidget.setSelectedDate(naloxone_expiration_date)
        self.ui.absoluteMaximumTemperatureLineEdit.setText(
            config["naloxone_info"]["absolute_maximum_temperature"])
        self.ui.passcodeLineEdit.setText(config["admin"]["passcode"])
        self.ui.adminPhoneNumberLineEdit.setText(
            config["admin"]["admin_phone_number"])
        self.ui.enableSMSCheckBox.setChecked(
            config["admin"]["enable_sms"] == "True")
        self.active_hour_start = QtCore.QTime.fromString(
            config["power_management"]["active_hours_start_at"], "hh:mm")
        self.ui.startTimeEdit.setTime(self.active_hour_start)
        self.active_hour_end = QtCore.QTime.fromString(
            config["power_management"]["active_hours_end_at"], "hh:mm")
        self.ui.endTimeEdit.setTime(self.active_hour_end)
        self.ui.enablePowerSavingCheckBox.setChecked(
            config["power_management"]["enable_power_saving"] == "True")

    def lock_settings(self):
        self.ui.unlockSettingsPushButton.setText("Unlock Other Settings")
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabEnabled(0, True)
        self.ui.settingsTab.setTabEnabled(1, True)
        self.ui.settingsTab.setTabEnabled(2, False)
        self.ui.settingsTab.setTabEnabled(3, False)
        self.ui.settingsTab.setTabEnabled(4, False)
        self.ui.settingsTab.setTabEnabled(5, False)

    def unlock_settings(self):
        self.ui.unlockSettingsPushButton.setText("Lock Other Settings")
        self.load_settings()
        # self.ui.saveToFilePushButton.setEnabled(True)
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabEnabled(0, True)
        self.ui.settingsTab.setTabEnabled(1, True)
        self.ui.settingsTab.setTabEnabled(2, True)
        self.ui.settingsTab.setTabEnabled(3, True)
        self.ui.settingsTab.setTabEnabled(4, True)
        self.ui.settingsTab.setTabEnabled(5, True)

    def check_passcode(self):
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        if (self.ui.passcodeEnterLineEdit.text() == config["admin"]["passcode"]):
            return True
        else:
            self.ui.passcodeEnterLabel.setText("Try Again")
            self.ui.passcodeEnterLineEdit.clear()
            return False

    def check_passcode_unlock_settings(self):
        passcode_check_result = self.check_passcode()
        if (passcode_check_result):
            self.unlock_settings()
            self.goto_settings()
        else:
            self.lock_settings()

    def lock_unlock_settings(self):
        if (self.ui.unlockSettingsPushButton.text() == "Unlock Other Settings"):
            self.ui.passcodeEnterPushButton.clicked.connect(
                self.check_passcode_unlock_settings)
            self.goto_passcode()
        elif (self.ui.unlockSettingsPushButton.text() == "Lock Other Settings"):
            self.lock_settings()

    def goto_door_open(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def goto_passcode(self):
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.passcodeEnterLabel.setText("Enter Passcode")
        self.ui.stackedWidget.setCurrentIndex(3)

    def goto_settings(self):
        self.ui.stackedWidget.setCurrentIndex(2)
        self.ui.settingsPushButton.setStyleSheet(
            "color: rgb(50,50,50); background-color: white; border-radius:3px;border-color: white;border-width: 1px;border-style: solid;")
        self.ui.dashboardPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        self.ui.homePushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")

    def goto_dashboard(self):
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(1)
        self.ui.dashboardPushButton.setStyleSheet(
            "color: rgb(50,50,50); background-color: white; border-radius:3px;border-color: white;border-width: 1px;border-style: solid;")
        self.ui.settingsPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        self.ui.homePushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")

    def goto_home(self):
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.homePushButton.setStyleSheet(
            "color: rgb(50,50,50); background-color: white; border-radius:3px;border-color: white;border-width: 1px;border-style: solid;")
        self.ui.dashboardPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        self.ui.settingsPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")

    def exit_program(self):
        os.kill(0, signal.SIGINT)  # kill all processes
        self.close()

    def replace_naloxone(self):
        if (self.ui.replaceNaloxonePushButton.text() == "Replace Naloxone"):
            with self.shared_array.get_lock():
                self.shared_array[8] = 1
            self.ui.replaceNaloxonePushButton.setText("Finish Replacement")
            self.ui.saveToFilePushButton.setEnabled(False)
            self.ui.saveToFilePushButton.setText(
                "Close the door and Click \"Finish Replacement\" to finish up.")
            self.goto_settings()
            self.ui.settingsTab.setCurrentIndex(1)
        else:
            self.save_config_file()
            self.ui.replaceNaloxonePushButton.setText("Replace Naloxone")
            self.ui.saveToFilePushButton.setText("Save Settings")
            self.ui.saveToFilePushButton.setEnabled(True)
            self.goto_home()
            with self.shared_array.get_lock():
                self.shared_array[8] = 0

    def toggle_door_arm(self):
        if (self.ui.disarmPushButton.text() == "Disarm"):
            self.ui.disarmPushButton.setText("Arm")
            with self.shared_array.get_lock():
                self.shared_array[8] = 1
        else:
            self.ui.disarmPushButton.setText("Disarm")
            with self.shared_array.get_lock():
                self.shared_array[8] = 0

    @QtCore.pyqtSlot(bool, bool)
    def update_door_ui(self, door, armed):
        if (not door):
            self.ui.doorClosedLineEdit.setText("Closed")
        else:
            self.ui.doorClosedLineEdit.setText("Open")
        if (armed):
            self.ui.doorArmedLineEdit.setText("Armed")
        else:
            self.ui.doorArmedLineEdit.setText("Disarmed")
        if (not door and armed):
            self.ui.doorStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px;background-color:#008A00;border-color:#008A00;border-width: 0.5px;border-style: solid;}")
        else:
            self.ui.doorStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px; background-color:#AC193D;border-color:#AC193D;border-width: 0.5px;border-style: solid;}")

    @QtCore.pyqtSlot(bool, QtCore.QDate)
    def update_naloxone_ui(self, naloxone_good, naloxone_expiration_date):
        self.ui.naloxoneExpirationDateLineEdit.setText(
            naloxone_expiration_date.toString("MMM dd, yy"))
        if (naloxone_good):
            self.ui.naloxoneStatusLineEdit.setText("OK")
            self.ui.naloxoneStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px;background-color:#008A00;border-color:#008A00;border-width: 0.5px;border-style: solid;}")
        else:
            self.ui.naloxoneStatusLineEdit.setText("Destroyed")
            self.ui.naloxoneStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px; background-color:#AC193D;border-color:#AC193D;border-width: 0.5px;border-style: solid;}")

    @QtCore.pyqtSlot(bool, QtCore.QTime)
    def update_server_ui(self, server, server_check_time):
        self.ui.serverCheckLineEdit.setText(
            server_check_time.toString("h:mm AP"))
        if (server):
            self.ui.serverStatusLineEdit.setText("OK")
            self.ui.serverStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px;background-color:#008A00;border-color:#008A00;border-width: 0.5px;border-style: solid;}")
        else:
            self.ui.serverStatusLineEdit.setText("Down")
            self.ui.serverStatusBarFrame.setStyleSheet(
                ".QFrame{border-radius: 5px; background-color:#AC193D;border-color:#AC193D;border-width: 0.5px;border-style: solid;}")

    @QtCore.pyqtSlot(int, int, bool)
    def update_temperature_ui(self, temperature, pwm, over_temperature):
        self.ui.temperatureLineEdit.setText(
            str(temperature) + "℃/"+str(int(temperature * 1.8 + 32)) + "℉")
        self.ui.fanSpeedLineEdit.setText(str(pwm) + " RPM")
        if(not over_temperature):
            self.ui.thermalStatusBarFrame.setStyleSheet(".QFrame{border-radius: 5px;background-color:#008A00;border-color:#008A00;border-width: 0.5px;border-style: solid;}")
        else:
            self.ui.thermalStatusBarFrame.setStyleSheet(".QFrame{border-radius: 5px; background-color:#AC193D;border-color:#AC193D;border-width: 0.5px;border-style: solid;}")

    @QtCore.pyqtSlot(QtCore.QTime)
    def update_time_ui(self, current_time):
        self.ui.currentTimeLineEdit.setText(current_time.toString("h:mm AP"))

    def save_config_file(self):
        #self.naloxone_expiration_date = self.ui.calendarWidget.selectedDate()
        self.active_hour_start = self.ui.startTimeEdit.time()
        self.active_hour_end = self.ui.endTimeEdit.time()
        config = configparser.ConfigParser()
        config["twilio"] = {
            "twilio_sid": self.ui.twilioSIDLineEdit.text(),
            "twilio_token": self.ui.twilioTokenLineEdit.text(),
            "twilio_phone_number": self.ui.twilioPhoneNumberLineEdit.text()
        }
        config["emergency_info"] = {
            "emergency_phone_number": self.ui.emergencyPhoneNumberLineEdit.text(),
            "emergency_address": self.ui.emergencyAddressLineEdit.text(),
            "emergency_message": self.ui.emergencyMessageLineEdit.text()
        }
        config["naloxone_info"] = {
            "naloxone_expiration_date": self.ui.calendarWidget.selectedDate().toString(),
            "absolute_maximum_temperature": self.ui.absoluteMaximumTemperatureLineEdit.text()
        }
        config["admin"] = {
            "passcode": self.ui.passcodeLineEdit.text(),
            "admin_phone_number": self.ui.adminPhoneNumberLineEdit.text(),
            "enable_sms": self.ui.enableSMSCheckBox.isChecked()
        }
        config["power_management"] = {
            "enable_power_saving": self.ui.enablePowerSavingCheckBox.isChecked(),
            "active_hours_start_at": self.active_hour_start.toString("hh:mm"),
            "active_hours_end_at": self.active_hour_end.toString("hh:mm")
        }
        with open("safety_kit.conf", "w") as configfile:
            config.write(configfile)
        print("INFO: save config file")


def gui_manager(shared_array):
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    app = QtWidgets.QApplication(sys.argv)
    QtGui.QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
    application = ApplicationWindow(shared_array)
    application.show()
    sys.exit(app.exec_())


def fork_gui(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: gui_pid={}".format(pid))
    else:
        gui_pid = os.getpid()
        signal.signal(signal.SIGINT, gui_signal_handler)
        gui_manager(shared_array)
    return pid
