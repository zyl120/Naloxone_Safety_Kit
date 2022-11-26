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
        #self.naloxone_expiration_date = QtCore.QDate.currentDate()
        self.active_hour_start = QtCore.QTime(8, 0, 0)
        self.active_hour_end = QtCore.QTime(18, 0, 0)
        self.shared_array = shared_array
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        self.ui.unlockSettingsPushButton.clicked.connect(
            self.lock_unlock_settings)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        # self.ui.saveToFilePushButton.setEnabled(False)
        # self.ui.settingsTab.setCurrentIndex(0)
        # self.
        self.load_settings()
        self.goto_dashboard()
        #self.goto_door_open()

        self.ui_updater_thread = QtCore.QThread()
        self.ui_worker = Worker(self.update_ui)
        self.ui_worker.moveToThread(self.ui_updater_thread)
        self.ui_updater_thread.started.connect(self.ui_worker.run)
        self.ui_updater_thread.start()

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
        self.ui.temperatureSpinBox.setValue(
            int(config["naloxone_info"]["absolute_maximum_temperature"]))
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

    def check_passcode(self):
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        #print("passcode" + self.ui.passcodeEnterLineEdit.text())
        if (self.ui.passcodeEnterLineEdit.text() == config["admin"]["passcode"]):
            #print("good passcode")
            return True
        else:
            #print("bad passcode")
            self.ui.passcodeEnterLabel.setText("Try Again")
            self.ui.passcodeEnterLineEdit.clear()
            return False

    def check_passcode_unlock_settings(self):
        passcode_check_result = self.check_passcode()
        if (passcode_check_result):
            self.ui.unlockSettingsPushButton.setText("Lock Settings")
            self.load_settings()
            # self.ui.saveToFilePushButton.setEnabled(True)
            self.ui.settingsTab.setCurrentIndex(1)
            self.ui.settingsTab.setTabEnabled(0, True)
            self.ui.settingsTab.setTabEnabled(1, True)
            self.ui.settingsTab.setTabEnabled(2, True)
            self.ui.settingsTab.setTabEnabled(3, True)
            self.ui.settingsTab.setTabEnabled(4, True)
            self.ui.settingsTab.setTabEnabled(5, True)
            self.ui.securityLabel.setText(
                "Settings are unlocked.\nClick \"Lock Settings\" to lock.")
            self.goto_settings()
        else:
            self.ui.unlockSettingsPushButton.setText("Unlock Settings")
            self.ui.settingsTab.setTabEnabled(0, True)
            self.ui.settingsTab.setTabEnabled(1, False)
            self.ui.settingsTab.setTabEnabled(2, False)
            self.ui.settingsTab.setTabEnabled(3, True)
            self.ui.settingsTab.setTabEnabled(4, False)
            self.ui.settingsTab.setTabEnabled(5, False)

    def lock_unlock_settings(self):
        if (self.ui.unlockSettingsPushButton.text() == "Unlock Settings"):
            self.ui.passcodeEnterPushButton.clicked.connect(
                self.check_passcode_unlock_settings)
            print("slot changed")
            self.goto_passcode()
        elif (self.ui.unlockSettingsPushButton.text() == "Lock Settings"):
            self.ui.unlockSettingsPushButton.setText("Unlock Settings")
            self.ui.securityLabel.setText(
                "Other settings are locked.\nClick \"Unlock Settings\" to unlock.")
            # self.ui.saveToFilePushButton.setEnabled(False)
            self.ui.settingsTab.setCurrentIndex(0)
            self.ui.settingsTab.setTabEnabled(0, True)
            self.ui.settingsTab.setTabEnabled(1, False)
            self.ui.settingsTab.setTabEnabled(2, False)
            self.ui.settingsTab.setTabEnabled(3, True)
            self.ui.settingsTab.setTabEnabled(4, False)
            self.ui.settingsTab.setTabEnabled(5, False)

    def goto_door_open(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def goto_passcode(self):
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.passcodeEnterLabel.setText("Enter Passcode")
        self.ui.stackedWidget.setCurrentIndex(2)

    def goto_settings(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def goto_dashboard(self):
        self.ui.unlockSettingsPushButton.setText("Unlock Settings")
        self.ui.securityLabel.setText(
            "Other settings are locked.\nClick \"Unlock Settings\" to unlock.")
        # self.ui.saveToFilePushButton.setEnabled(False)
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabEnabled(0, True)
        self.ui.settingsTab.setTabEnabled(1, False)
        self.ui.settingsTab.setTabEnabled(2, False)
        self.ui.settingsTab.setTabEnabled(3, True)
        self.ui.settingsTab.setTabEnabled(4, False)
        self.ui.settingsTab.setTabEnabled(5, False)
        self.ui.stackedWidget.setCurrentIndex(0)

    def exit_program(self):
        os.kill(0, signal.SIGINT)  # kill all processes
        self.close()

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
            self.ui.currentTimeLineEdit.setText(
                QtCore.QTime().currentTime().toString("h:mm AP"))
            iconString = str()
            naloxone_expiration_date = QtCore.QDate(year, month, day)
            server_check_time = QtCore.QTime(hour, minute)
            self.ui.naloxoneExpirationDateLineEdit.setText(
                naloxone_expiration_date.toString("MMM dd, yy"))
            self.ui.serverCheckLineEdit.setText(
                server_check_time.toString("h:mm AP"))
            self.ui.temperatureLineEdit.setText(
                str(temperature) + "℃/"+str(int(temperature * 1.8 + 32)) + "℉")
            self.ui.fanSpeedLineEdit.setText(str(pwm) + " RPM")
            if (server == 0):
                self.ui.serverStatusLineEdit.setText("Down")
                iconString += "📶"
            else:
                self.ui.serverStatusLineEdit.setText("OK")
            if (door == 0):
                self.ui.doorClosedLineEdit.setText("Closed")
            else:
                self.ui.doorClosedLineEdit.setText("Open")
                iconString += "🚪"
            if (armed == 0):
                self.ui.doorArmedLineEdit.setText("Armed")
            else:
                self.ui.doorArmedLineEdit.setText("Disarmed")
                iconString += "⏸️"
            if (naloxone_expired or naloxone_overheat):
                self.ui.naloxoneStatusLineEdit.setText("Destroyed")
                iconString += "💊"
            else:
                self.ui.naloxoneStatusLineEdit.setText("OK")
            self.ui.iconLabel.setText(iconString)
            sleep(1)

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
            "absolute_maximum_temperature": self.ui.temperatureSpinBox.text()
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
