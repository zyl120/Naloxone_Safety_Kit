from PyQt5 import QtWidgets, QtCore, QtGui
from ui_form import Ui_Widget
import os
import sys
import configparser
import subprocess
import signal
from ui_door_close_window import Ui_door_close_main_window
# from ui_calendar_picker import Ui_Dialog
# from ui_time_picker import Ui_activeHoursPicker
#from qt_material import apply_stylesheet
import qdarktheme
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
        self.naloxone_expiration_date = QtCore.QDate.currentDate()
        self.active_hour_start = QtCore.QTime(8, 0, 0)
        self.active_hour_end = QtCore.QTime(18, 0, 0)
        self.shared_array = shared_array
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        # self.ui.naloxoneExpirationDateSettingsLineEdit.setText(
        #    self.naloxone_expiration_date.toString())
        #self.ui.startHourLabel.setText(self.active_hour_start.toString("h:mm AP"))
        #self.ui.endHourLabel.setText(self.active_hour_end.toString("h:mm AP"))
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        self.ui.unlockSettingsPushButton.clicked.connect(
            self.lock_unlock_settings)

        # self.ui.naloxoneExpirationDatePickerPushButton.clicked.connect(
        #     self.date_picker)
        # self.ui.activeHoursPushButton.clicked.connect(self.time_picker)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)

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

    def check_passcode(self):
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        print("passcode" + self.ui.passcodeEnterLineEdit.text())
        if (self.ui.passcodeEnterLineEdit.text() == config["admin"]["passcode"]):
            print("good passcode")
            return True
        else:
            print("bad passcode")
            self.ui.passcodeEnterLabel.setText("Try Again")
            self.ui.passcodeEnterLineEdit.clear()
            return False

    def check_passcode_unlock_settings(self):
        passcode_check_result = self.check_passcode()
        if (passcode_check_result):
            self.ui.unlockSettingsPushButton.setText("Lock Settings")
            self.ui.settingsTab.setEnabled(True)
            self.goto_settings()
        else:
            self.ui.unlockSettingsPushButton.setText("Unlock Settings")
            self.ui.settingsTab.setEnabled(False)

    def lock_unlock_settings(self):
        if (self.ui.unlockSettingsPushButton.text() == "Unlock Settings"):
            self.ui.passcodeEnterPushButton.clicked.connect(
                self.check_passcode_unlock_settings)
            print("slot changed")
            self.goto_passcode()
        elif (self.ui.unlockSettingsPushButton.text() == "Lock Settings"):
            self.ui.unlockSettingsPushButton.setText("Unlock Settings")
            self.ui.settingsTab.setEnabled(False)

    def goto_passcode(self):
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.stackedWidget.setCurrentIndex(2)

    def goto_settings(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def goto_dashboard(self):
        self.ui.unlockSettingsPushButton.setText("Unlock Settings")
        self.ui.settingsTab.setEnabled(False)
        self.ui.stackedWidget.setCurrentIndex(0)

    def exit_program(self):
        os.kill(0, signal.SIGINT)  # kill all processes
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
            self.ui.serverCheckLineEdit.setText(
                server_check_time.toString("h:mm AP"))
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

    # def date_picker(self):
    #     print("INFO: date picker go")
    #     date_picker_dialog = QtWidgets.QDialog()
    #     date_picker_dialog.ui = Ui_Dialog()
    #     date_picker_dialog.ui.setupUi(date_picker_dialog)
    #     date_picker_dialog.ui.calendarWidget.setSelectedDate(
    #         self.naloxone_expiration_date)
    #     date_picker_dialog.ui.buttonBox.accepted.connect(lambda: self.get_date(
    #         date_picker_dialog.ui.calendarWidget.selectedDate()))
    #     date_picker_dialog.exec_()

    # def get_date(self, selectedDate):
    #     self.naloxone_expiration_date = selectedDate
    #     self.ui.naloxoneExpirationDateSettingsLineEdit.setText(
    #         self.naloxone_expiration_date.toString())
    #     print(selectedDate.toString())

    # def military_clock_to_12_clock(self, military_clock):
    #     print(military_clock.toString())
    #     hour, apm = military_clock.toString("h AP").split()
    #     print(hour, apm)
    #     if (apm == "AM"):
    #         apm = 0
    #     else:
    #         apm = 1
    #     return int(hour), apm

    # def time_picker(self):
    #     print("INFO: time picker go")
    #     os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    #     time_picker_dialog = QtWidgets.QDialog()
    #     QtGui.QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
    #     time_picker_dialog.ui = Ui_activeHoursPicker()
    #     time_picker_dialog.ui.setupUi(time_picker_dialog)

    #     time_picker_dialog.ui.startTimeEdit.setTime(self.active_hour_start)
    #     time_picker_dialog.ui.endTimeEdit.setTime(self.active_hour_end)

    #     time_picker_dialog.ui.activeHoursPickerButtonBox.accepted.connect(lambda: self.get_time(time_picker_dialog.ui.startTimeEdit.time(), time_picker_dialog.ui.endTimeEdit.time()))
    #     time_picker_dialog.exec_()

    # def get_time(self, start_time, end_time):
    #     print(start_time.toString("h:mm AP"))
    #     print(end_time.toString("h:mm AP"))
    #     #print("INFO: get time" + str(startHour) +
    #     #      str(startAPM) + str(endHour) + str(endAPM))
    #     # start_hour_calculate = 0
    #     # if (startHour == 12 and startAPM == 0):
    #     #     start_hour_calculate = 0
    #     # elif (startHour == 12 and startAPM == 1):
    #     #     start_hour_calculate = 12
    #     # else:
    #     #     start_hour_calculate = startHour + startAPM * 12

    #     # end_hour_calculate = 0
    #     # if (endHour == 12 and endAPM == 0):
    #     #     end_hour_calculate = 0
    #     # elif (endHour == 12 and endAPM == 1):
    #     #     end_hour_calculate = 12
    #     # else:
    #     #     end_hour_calculate = endHour + endAPM * 12

    #     self.active_hour_start = start_time
    #     self.actibe_hour_end = end_time

    #     #self.active_hour_start.setHMS(start_hour_calculate, 0,0)
    #     #self.active_hour_end.setHMS(end_hour_calculate, 0, 0)
    #     self.ui.startHourLabel.setText(self.active_hour_start.toString("h:mm AP"))
    #     self.ui.endHourLabel.setText(self.active_hour_end.toString("h:mm AP"))

    def save_config_file(self):
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
            "naloxone_expiration_date": self.naloxone_expiration_date.toString(),
            "absolute_maximum_temperature": self.ui.temperatureSpinBox.text()
        }
        config["admin"] = {
            "passcode": self.ui.passcodeLineEdit.text(),
            "admin_phone_number": self.ui.adminPhoneNumberLineEdit.text(),
            "enable_sms": self.ui.enableSMSCheckBox.isChecked()
        }
        config["power_management"] = {
            "enable_power_saving": self.ui.enablePowerSavingCheckBox.isChecked(),
            "active_hours_start_at": self.active_hour_start.toString("hh"),
            "active_hours_end_at": self.active_hour_end.toString("hh")
        }
        with open("safety_kit.conf", "w") as configfile:
            config.write(configfile)
        print("INFO: save config file")


def door_closed_window(shared_array):
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    app = QtWidgets.QApplication(sys.argv)
    QtGui.QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
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
