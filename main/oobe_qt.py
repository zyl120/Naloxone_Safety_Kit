from PyQt5 import QtWidgets, QtCore
from ui_form import Ui_Widget
from ui_calendar_picker import Ui_Dialog
from ui_time_picker import Ui_activeHoursPicker
import os
import sys
import configparser
import subprocess


class ApplicationWindow(QtWidgets.QMainWindow):
    naloxone_expiration_date = QtCore.QDate.currentDate()
    active_hour_start = QtCore.QTime(8, 0, 0)
    active_hour_end = QtCore.QTime(18, 0, 0)
    print(naloxone_expiration_date)
    #touch_keyboard = subprocess.Popen(['matchbox-keyboard'])

    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.ui.naloxoneExpirationDatePickerPushButton.clicked.connect(
            self.date_picker)
        self.ui.activeHoursPushButton.clicked.connect(self.time_picker)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        self.ui.saveAndExitPushButton.clicked.connect(self.save_and_exit)
        self.ui.discardAndExitPushButton.clicked.connect(self.close)
        self.ui.naloxoneExpirationDateLineEdit.setText(
            self.naloxone_expiration_date.toString())
        self.ui.startHourLabel.setText(self.active_hour_start.toString("h AP"))
        self.ui.endHourLabel.setText(self.active_hour_end.toString("h AP"))

    def date_picker(self):
        print("INFO: date picker go")
        date_picker_dialog = QtWidgets.QDialog()
        date_picker_dialog.ui = Ui_Dialog()
        date_picker_dialog.ui.setupUi(date_picker_dialog)
        date_picker_dialog.ui.calendarWidget.setSelectedDate(
            self.naloxone_expiration_date)
        date_picker_dialog.ui.buttonBox.accepted.connect(lambda: self.get_date(
            date_picker_dialog.ui.calendarWidget.selectedDate()))
        date_picker_dialog.exec_()

    def get_date(self, selectedDate):
        self.naloxone_expiration_date = selectedDate
        self.ui.naloxoneExpirationDateLineEdit.setText(
            self.naloxone_expiration_date.toString())
        print(selectedDate.toString())

    def military_clock_to_12_clock(self, military_clock):
        print(military_clock.toString())
        hour, apm = military_clock.toString("h AP").split()
        print(hour, apm)
        if (apm == "AM"):
            apm = 0
        else:
            apm = 1
        return int(hour), apm

    def time_picker(self):
        print("INFO: time picker go")
        time_picker_dialog = QtWidgets.QDialog()
        time_picker_dialog.ui = Ui_activeHoursPicker()
        time_picker_dialog.ui.setupUi(time_picker_dialog)
        start_hour, start_apm = self.military_clock_to_12_clock(
            self.active_hour_start)
        end_hour, end_apm = self.military_clock_to_12_clock(
            self.active_hour_end)

        time_picker_dialog.ui.startTimeHour.setValue(start_hour)
        time_picker_dialog.ui.startTimeAPM.setCurrentIndex(start_apm)
        time_picker_dialog.ui.endTimeHour.setValue(end_hour)
        time_picker_dialog.ui.endTimeAPM.setCurrentIndex(end_apm)

        time_picker_dialog.ui.activeHoursPickerButtonBox.accepted.connect(lambda: self.get_time(time_picker_dialog.ui.startTimeHour.value(
        ), time_picker_dialog.ui.startTimeAPM.currentIndex(), time_picker_dialog.ui.endTimeHour.value(), time_picker_dialog.ui.endTimeAPM.currentIndex()))
        time_picker_dialog.exec_()

    def get_time(self, startHour, startAPM, endHour, endAPM):
        print("INFO: get time" + str(startHour) +
              str(startAPM) + str(endHour) + str(endAPM))
        start_hour_calculate = 0
        if (startHour == 12 and startAPM == 0):
            start_hour_calculate = 0
        elif (startHour == 12 and startAPM == 1):
            start_hour_calculate = 12
        else:
            start_hour_calculate = startHour + startAPM * 12

        end_hour_calculate = 0
        if (endHour == 12 and endAPM == 0):
            end_hour_calculate = 0
        elif (endHour == 12 and endAPM == 1):
            end_hour_calculate = 12
        else:
            end_hour_calculate = endHour + endAPM * 12

        self.active_hour_start.setHMS(start_hour_calculate, 0, 0)
        self.active_hour_end.setHMS(end_hour_calculate, 0, 0)
        self.ui.startHourLabel.setText(self.active_hour_start.toString("h AP"))
        self.ui.endHourLabel.setText(self.active_hour_end.toString("h AP"))

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

    def save_and_exit(self):
        print("INFO: save and exit...")
        self.save_config_file()
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
