from PyQt5 import QtWidgets, QtCore, QtGui
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
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


class GenericWorker(QtCore.QThread):
    def __init__(self, fn):
        super(GenericWorker, self).__init__()
        self.fn = fn

    def run(self):
        self.fn()


class SharedMemoryWorker(QtCore.QThread):
    update_door = QtCore.pyqtSignal(bool, bool)
    update_temperature = QtCore.pyqtSignal(int, int, int, bool)
    update_server = QtCore.pyqtSignal(bool, QtCore.QTime)
    update_naloxone = QtCore.pyqtSignal(bool, QtCore.QDate)
    update_time = QtCore.pyqtSignal(QtCore.QTime)

    def __init__(self, shared_array):
        super(SharedMemoryWorker, self).__init__()
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
        cpu_temperature = 0
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
                cpu_temperature = self.shared_array[19]
            self.update_door.emit(door, not disarmed)
            self.update_temperature.emit(
                temperature, cpu_temperature, pwm, over_temperature)
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
        self.ui.naloxoneExpirationDateEdit.setDisplayFormat("MMM dd, yy")
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
        self.ui.temperatureSlider.valueChanged.connect(
            self.update_current_max_temperature)
        self.ui.callTestPushButton.clicked.connect(
            self.call_test_pushbutton_clicked)
        self.ui.smsTestPushButton.clicked.connect(
            self.sms_test_pushbutton_clicked)
        self.load_settings()
        self.lock_settings()
        self.goto_door_open()

        self.get_shared_array_worker = SharedMemoryWorker(self.shared_array)
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
        self.ui.naloxoneExpirationDateEdit.setDate(naloxone_expiration_date)
        self.ui.temperatureSlider.setValue(
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
        self.ui.enableActiveCoolingCheckBox.setChecked(
            config["power_management"]["enable_active_cooling"] == "True")

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
            "color: white; background-color: rgb(90,90,90); border-radius:3px;border-color: rgb(90,90,90);border-width: 1px;border-style: solid;")
        self.ui.dashboardPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        self.ui.homePushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")

    def goto_dashboard(self):
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(1)
        self.ui.dashboardPushButton.setStyleSheet(
            "color: white; background-color: rgb(90,90,90); border-radius:3px;border-color: rgb(90,90,90);border-width: 1px;border-style: solid;")
        self.ui.settingsPushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        self.ui.homePushButton.setStyleSheet(
            "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")

    def goto_home(self):
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.homePushButton.setStyleSheet(
            "color: white; background-color: rgb(90,90,90); border-radius:3px;border-color: rgb(90,90,90);border-width: 1px;border-style: solid;")
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

    def sms_test_pushbutton_clicked(self):
        self.sms_worker = GenericWorker(self.sms_test)
        self.sms_worker.start()

    def sms_test(self):
        client = Client(self.ui.twilioSIDLineEdit.text(),
                        self.ui.twilioTokenLineEdit.text())
        body = ("Internet-based Naloxone Safety Kit. " +
                "These are the words that will be heard by " + self.ui.emergencyPhoneNumberLineEdit.text() +
                " when the door is opened: Message: " + self.ui.emergencyMessageLineEdit.text() + ". Address: " +
                self.ui.emergencyAddressLineEdit.text() +
                ". If the words sound good, you can save the settings. Thank you.")
        try:
            message = client.messages.create(
                body=body,
                to=self.ui.adminPhoneNumberLineEdit.text(),
                from_=self.ui.twilioPhoneNumberLineEdit.text()
            )
        except TwilioRestException as e:
            # if not successful, return False
            print("ERROR: Twilio SMS: ERROR - {}".format(str(e)))
            return False
        else:
            # if successful, return True
            print(message.sid)
            print("INFO: Twilio SMS: SMS ID: {}".format(str(message.sid)))
            return True

    def call_test_pushbutton_clicked(self):
        self.call_worker = GenericWorker(self.call_test)
        self.call_worker.start()

    def call_test(self):
        response = VoiceResponse()
        response.say("Internet-based Naloxone Safety Kit. " +
                     "These are the words that will be heard by " + " ".join(self.ui.emergencyPhoneNumberLineEdit.text()) +
                     " when the door is opened: Message: " + self.ui.emergencyMessageLineEdit.text() + ". Address: " +
                     self.ui.emergencyAddressLineEdit.text() +
                     ". If the call sounds good, you can save the settings. Thank you.", voice="woman", loop=3)
        print("INFO: resonse: " + str(response))

        # create client
        client = Client(self.ui.twilioSIDLineEdit.text(),
                        self.ui.twilioTokenLineEdit.text())
        print(response)

        # try to place the phone call
        try:
            call = client.calls.create(
                twiml=response,
                to=self.ui.adminPhoneNumberLineEdit.text(),
                from_=self.ui.twilioPhoneNumberLineEdit.text()
            )
        except TwilioRestException as e:
            # if not successful, return False
            print("ERROR: Twilio Call: ERROR - {}".format(str(e)))
            return False
        else:
            # if successful, return True
            print(call.sid)
            print("INFO: Twilio Call: Call ID: {}".format(str(call.sid)))
            return True

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
            self.ui.doorStatusBox.setStyleSheet(
                "color:#008A00")
        else:
            self.ui.doorStatusBox.setStyleSheet(
                "color:#AC193D")

    @QtCore.pyqtSlot(bool, QtCore.QDate)
    def update_naloxone_ui(self, naloxone_good, naloxone_expiration_date):
        self.ui.naloxoneExpirationDateLineEdit.setText(
            naloxone_expiration_date.toString("MMM dd, yy"))
        if (naloxone_good):
            self.ui.naloxoneStatusLineEdit.setText("OK")
            self.ui.naloxoneStatusBox.setStyleSheet(
                "color:#008A00")
        else:
            self.ui.naloxoneStatusLineEdit.setText("Destroyed")
            self.ui.naloxoneStatusBox.setStyleSheet(
                "color:#AC193D")

    @QtCore.pyqtSlot(bool, QtCore.QTime)
    def update_server_ui(self, server, server_check_time):
        self.ui.serverCheckLineEdit.setText(
            server_check_time.toString("h:mm AP"))
        if (server):
            self.ui.serverStatusLineEdit.setText("OK")
            self.ui.serverStatusBox.setStyleSheet(
                "color:#008A00")
        else:
            self.ui.serverStatusLineEdit.setText("Down")
            self.ui.serverStatusBox.setStyleSheet(
                "color:#AC193D")

    @QtCore.pyqtSlot(int, int, int, bool)
    def update_temperature_ui(self, temperature, cpu_temperature, pwm, over_temperature):
        self.ui.temperatureLineEdit.setText(
            str(temperature) + "℉")
        self.ui.cpuTemperatureLineEdit.setText(str(cpu_temperature) + "℉")
        self.ui.fanSpeedLineEdit.setText(str(pwm) + " RPM")
        if (not over_temperature):
            self.ui.thermalStatusBox.setStyleSheet(
                "color:#008A00")
        else:
            self.ui.thermalStatusBox.setStyleSheet(
                "color:#AC193D")

    @QtCore.pyqtSlot(QtCore.QTime)
    def update_time_ui(self, current_time):
        self.ui.currentTimeLineEdit.setText(current_time.toString("h:mm AP"))

    @QtCore.pyqtSlot(int)
    def update_current_max_temperature(self, value):
        self.ui.CurrentTemperatureLabel.setText(str(value)+"℉")

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
            "naloxone_expiration_date": self.ui.naloxoneExpirationDateEdit.date().toString(),
            "absolute_maximum_temperature": self.ui.temperatureSlider.value()
        }
        config["admin"] = {
            "passcode": self.ui.passcodeLineEdit.text(),
            "admin_phone_number": self.ui.adminPhoneNumberLineEdit.text(),
            "enable_sms": self.ui.enableSMSCheckBox.isChecked()
        }
        config["power_management"] = {
            "enable_active_cooling": self.ui.enableActiveCoolingCheckBox.isChecked(),
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
        os.sched_setaffinity(gui_pid, {gui_pid % os.cpu_count()})
        print("gui" + str(gui_pid) + str(gui_pid % os.cpu_count()))
        signal.signal(signal.SIGINT, gui_signal_handler)
        # sleep(1000)
        gui_manager(shared_array)
    return pid
