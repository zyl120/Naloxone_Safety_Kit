from PyQt5 import QtWidgets, QtCore, QtGui
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
import os
import sys
import configparser
from ui_door_close_window import Ui_door_close_main_window
from time import sleep
import qrcode
import random
from gpiozero import CPUTemperature
import RPi.GPIO as GPIO
import Adafruit_DHT as dht


DOOR_PIN = 17
DHT_PIN = 27


def handleVisibleChanged():
    # control the position of the virtual keyboard
    if not QtGui.QGuiApplication.inputMethod().isVisible():
        return
    for w in QtGui.QGuiApplication.allWindows():
        if w.metaObject().className() == "QtVirtualKeyboard::InputView":
            keyboard = w.findChild(QtCore.QObject, "keyboard")
            if keyboard is not None:
                r = w.geometry()
                r.moveTop(int(keyboard.property("y")))
                w.setMask(QtGui.QRegion(r))
                return


class GenericWorker(QtCore.QThread):
    # Generic worker thread that used to run a function that may block the GUI
    # Will emit a signal to show a message box if the slot is defined
    msg_info_signal = QtCore.pyqtSignal(str, str, str)

    def __init__(self, fn):
        super(GenericWorker, self).__init__()
        self.fn = fn

    def run(self):
        icon, text, detailed_text = self.fn()
        if text:
            self.msg_info_signal.emit(icon, text, detailed_text)


class CountDownWorker(QtCore.QThread):
    # Used to record the countdown time before calling the emergency
    # signal to indicate end of countdown time.
    time_end_signal = QtCore.pyqtSignal()
    # signal to indicate the change of countdown time.
    time_changed_signal = QtCore.pyqtSignal(int)

    def __init__(self, time_in_sec):
        super(CountDownWorker, self).__init__()
        self.time_in_sec = time_in_sec

    def run(self):
        while (self.time_in_sec >= 0):
            self.time_changed_signal.emit(self.time_in_sec)
            self.time_in_sec = self.time_in_sec - 1
            sleep(1)
        self.time_end_signal.emit()

    def stop(self):
        self.terminate()


class IOWorker(QtCore.QThread):
    update_door = QtCore.pyqtSignal(bool, bool)
    update_temperature = QtCore.pyqtSignal(int, int, int, bool)
    update_naloxone = QtCore.pyqtSignal(bool, QtCore.QDate)
    go_to_door_open_signal = QtCore.pyqtSignal()

    def __init__(self, disarmed, max_temp, expiration_date):
        super(IOWorker, self).__init__()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DOOR_PIN, GPIO.IN)
        print("gpio thread go " + str(disarmed) + " " + str(max_temp))
        self.naloxone_counter = 9
        self.naloxone_temp = 25
        self.fan_pwm = 0
        self.cpu_temp = 50
        self.door_opened = False
        self.disarmed = disarmed
        self.max_temp = max_temp
        self.expiration_date = expiration_date

    def read_naloxone_sensor(self):
        _, self.temperature = dht.read_retry(dht.DHT22, DHT_PIN)
        #self.temperature = 25

    def calculate_pwm(self):
        # print("control pwm")
        list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
        self.fan_pwm = random.choice(list1)
        # return pwm

    def send_pwm(self):
        return

    def read_cpu_sensor(self):
        self.cpu_temp = int(CPUTemperature().temperature * 1.8 + 32)
        #self.cpu_temp = 100

    def read_door_sensor(self):
        #self.door_opened = False
        if GPIO.input(DOOR_PIN):
            self.door_opened = True
        else:
            self.door_opened = False

    def is_expiry(self):
        today = QtCore.QDate().currentDate()
        return today > self.expiration_date

    def is_overheat(self):
        return self.max_temp < self.naloxone_temp

    def run(self):
        while True:
            self.naloxone_counter += 1
            if (self.naloxone_counter == 10):
                self.read_naloxone_sensor()
                self.read_cpu_sensor()
                self.calculate_pwm()
                self.update_temperature.emit(
                    self.naloxone_temp, self.cpu_temp, self.fan_pwm, self.naloxone_temp > self.max_temp)
                self.naloxone_counter = 0
            self.send_pwm()
            self.read_door_sensor()
            if (self.door_opened and not self.disarmed):  # if door opened and the switch is armed
                self.go_to_door_open_signal.emit()
            self.update_door.emit(self.door_opened, not self.disarmed)
            self.update_naloxone.emit(
                not self.is_overheat() and not self.is_expiry(), self.expiration_date)
            sleep(1)
            if (self.isInterruptionRequested()):
                break


class AlarmWorker(QtCore.QThread):
    def __init__(self):
        super(AlarmWorker, self).__init__()
        print("alarm thread go.")

    def run(self):
        while (True):
            print("saying alarm now.")
            sleep(1)
            if (self.isInterruptionRequested()):
                break


class NetworkWorker(QtCore.QThread):
    update_server = QtCore.pyqtSignal(bool, float, str, QtCore.QTime)

    def __init__(self, twilio_sid, twilio_token):
        super(NetworkWorker, self).__init__()
        self.hostname = "www.twilio.com"  # ping twilio directly
        print("network thread go.")
        self.currentTime = QtCore.QTime()
        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token

    def run(self):
        while True:
            client = Client(self.twilio_sid, self.twilio_token)

            response = os.system("ping -c 1 " + self.hostname)
            if (response == 1):
                self.update_server.emit(
                    False, 0, self.currentTime.currentTime())
            else:
                balance = client.api.v2010.balance.fetch().balance
                currency = client.api.v2010.balance.fetch().currency
                self.update_server.emit(True, float(
                    balance), currency, self.currentTime.currentTime())
            sleep(600)
            if (self.isInterruptionRequested()):
                break


class CallWorker(QtCore.QThread):
    # Worker thread to make the phone call
    # The status signal can be used to determine the calling result.
    call_thread_status = QtCore.pyqtSignal(str, str, str)

    def __init__(self, number, body, t_sid, t_token, t_number):
        super(CallWorker, self).__init__()
        self.number = number
        self.body = body
        self.twilio_sid = t_sid
        self.twilio_token = t_token
        self.twilio_phone_number = t_number

    def run(self):
        client = Client(self.twilio_sid, self.twilio_token)
        try:
            call = client.calls.create(
                twiml=self.body,
                to=self.number,
                from_=self.twilio_phone_number
            )
        except TwilioRestException as e:
            # if not successful, return False
            print("ERROR: Twilio Call: ERROR - {}".format(str(e)))
            self.call_thread_status.emit(
                "Critical", "Call Request Failed.", str(e))
        else:
            # if successful, return True
            print(call.sid)
            print("INFO: Twilio Call: Call ID: %s", call.sid)
            self.call_thread_status.emit(
                "Information", "Call Request Sent Successfully.", str(call.sid))


class SMSWorker(QtCore.QThread):
    # Worker thread to send the sms
    # The status signal can be used to determine the calling result.
    sms_thread_status = QtCore.pyqtSignal(str, str, str)

    def __init__(self, number, body, t_sid, t_token, t_number):
        super(SMSWorker, self).__init__()
        self.number = number
        self.body = body
        self.twilio_sid = t_sid
        self.twilio_token = t_token
        self.twilio_phone_number = t_number

    def run(self):
        client = Client(self.twilio_sid,
                        self.twilio_token)
        try:
            sms = client.messages.create(
                body=self.body,
                to=self.number,
                from_=self.twilio_phone_number
            )
        except TwilioRestException as e:
            # if not successful, return False
            print("ERROR: Twilio SMS: ERROR - {}".format(str(e)))
            self.sms_thread_status.emit(
                "Critical", "SMS Request Failed.", str(e))
        else:
            # if successful, return True
            print(sms.sid)
            print("INFO: Twilio SMS: SMS ID: {}".format(str(sms.sid)))
            self.sms_thread_status.emit(
                "Information", "SMS Request Sent Successfully.", str(sms.sid))


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.door_opened = False
        self.disarmed = False
        self.max_temp = 0
        self.admin_passcode = str()
        self.naloxone_passcode = str()
        self.twilio_sid = str()
        self.twilio_token = str()
        self.twilio_phone_number = str()
        self.admin_phone_number = str()
        self.address = str()
        self.to_phone_number = str()
        self.message = str()
        self.naloxone_expiration_date = QtCore.QDate().currentDate()
        self.active_hour_start = QtCore.QTime(8, 0, 0)
        self.active_hour_end = QtCore.QTime(18, 0, 0)
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        # self.ui.naloxoneExpirationDateEdit.setDisplayFormat("MMM dd, yy")
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.ui.homePushButton.clicked.connect(self.goto_home)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        self.ui.unlockSettingsPushButton.clicked.connect(
            self.lock_unlock_settings)
        self.ui.lockSettingsPushButton.clicked.connect(self.lock_settings)
        self.ui.lockSettingsPushButton.setVisible(False)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        self.ui.temperatureSlider.valueChanged.connect(
            self.update_current_max_temperature)
        self.ui.callTestPushButton.clicked.connect(
            self.call_test_pushbutton_clicked)
        self.ui.smsTestPushButton.clicked.connect(
            self.sms_test_pushbutton_clicked)
        self.ui.passcodeEnterPushButton.clicked.connect(
            self.check_passcode_unlock_settings)
        self.ui.doorOpenResetPushButton.clicked.connect(
            self.reset_button_pushed)
        self.countdown_thread = CountDownWorker(10)
        self.ui.stopCountdownPushButton.clicked.connect(
            self.stop_countdown_button_pushed)
        self.ui.call911NowPushButton.clicked.connect(self.call_emergency_now)
        self.ui.forgotPasswordPushButton.clicked.connect(
            self.forgot_password_button_pushed)
        self.ui.backPushButton.clicked.connect(self.back_pushbutton_pushed)
        self.ui.getPasscodePushButton.clicked.connect(
            self.get_passcode_button_pushed)
        self.ui.alarmMutePushButton.clicked.connect(self.stop_alarm)

        self.generate_ui_qrcode()

        self.network_worker = None
        self.io_worker = None
        self.alarm_worker = None

        self.goto_home()
        self.lock_settings()
        self.load_settings()

    def create_network_worker(self):
        if (self.network_worker is not None):
            self.network_worker.quit()
            self.network_worker.requestInterruption()
        self.network_worker = NetworkWorker(self.twilio_sid, self.twilio_token)
        self.network_worker.update_server.connect(
            self.update_server_ui)
        self.network_worker.start()

    def create_io_worker(self):
        if (self.io_worker is not None):
            self.io_worker.quit()
            self.io_worker.requestInterruption()
        self.io_worker = IOWorker(
            self.disarmed, self.max_temp, self.naloxone_expiration_date)
        self.io_worker.update_door.connect(self.update_door_ui)
        self.io_worker.go_to_door_open_signal.connect(self.goto_door_open)
        self.io_worker.update_temperature.connect(
            self.update_temperature_ui)
        self.io_worker.update_naloxone.connect(self.update_naloxone_ui)
        self.io_worker.start()

    def create_alarm_worker(self):
        if (self.alarm_worker is not None):
            self.alarm_worker.quit()
            self.alarm_worker.requestInterruption()
        self.alarm_worker = AlarmWorker()
        self.alarm_worker.start()

    def generate_ui_qrcode(self):
        github_qr_code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        github_qr_code.add_data(
            "https://github.com/zyl120/Naloxone_Safety_Kit")
        github_qr_code.make(fit=True)
        img = github_qr_code.make_image(
            fill_color="white", back_color=(50, 50, 50))
        img.save("github_qrcode.png")
        github_qrcode_pixmap = QtGui.QPixmap(
            "github_qrcode.png").scaledToWidth(100).scaledToHeight(100)
        self.ui.github_qrcode.setPixmap(github_qrcode_pixmap)

        understanding_qr_code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        understanding_qr_code.add_data(
            "https://www.cdc.gov/drugoverdose/epidemic/index.html")
        understanding_qr_code.make(fit=True)
        img = understanding_qr_code.make_image(
            fill_color="white", back_color=(50, 50, 50))
        img.save("understanding_qrcode.png")
        understanding_qrcode_pixmap = QtGui.QPixmap(
            "understanding_qrcode.png").scaledToWidth(100).scaledToHeight(100)
        self.ui.understanding_qrcode.setPixmap(understanding_qrcode_pixmap)

        naloxone_qr_code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        naloxone_qr_code.add_data(
            "https://nida.nih.gov/publications/drugfacts/naloxone")
        naloxone_qr_code.make(fit=True)
        img = naloxone_qr_code.make_image(
            fill_color="white", back_color=(50, 50, 50))
        img.save("naloxone_qrcode.png")
        naloxone_qrcode_pixmap = QtGui.QPixmap(
            "naloxone_qrcode.png").scaledToWidth(100).scaledToHeight(100)
        self.ui.naloxone_qrcode.setPixmap(naloxone_qrcode_pixmap)

        twilio_75_qr_code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        twilio_75_qr_code.add_data(
            "https://www.twilio.com/docs/voice/tutorials/emergency-calling-for-programmable-voice#:~:text=When%20placing%20an%20emergency%20call,for%20a%20test%20emergency%20call.")
        twilio_75_qr_code.make(fit=True)
        img = twilio_75_qr_code.make_image(
            fill_color="white", back_color="black")
        img.save("twilio_75.png")
        twilio_75_qrcode_pixmap = QtGui.QPixmap(
            "twilio_75.png").scaledToWidth(100).scaledToHeight(100)
        self.ui.twilioAddressWarningQrCode.setPixmap(
            (twilio_75_qrcode_pixmap))

    def load_settings_ui(self):
        try:
            # Load the settings from the conf file, will not handle exceptions.
            # Should be used when it is absolutely safe to do so.
            config = configparser.ConfigParser()
            config.read("safety_kit.conf")
            self.ui.twilioSIDLineEdit.setText(config["twilio"]["twilio_sid"])
            self.ui.twilioTokenLineEdit.setText(
                config["twilio"]["twilio_token"])
            self.ui.twilioPhoneNumberLineEdit.setText(
                config["twilio"]["twilio_phone_number"])
            self.ui.emergencyPhoneNumberLineEdit.setText(
                config["emergency_info"]["emergency_phone_number"])
            self.ui.emergencyAddressLineEdit.setText(
                config["emergency_info"]["emergency_address"])
            self.ui.emergencyMessageLineEdit.setText(
                config["emergency_info"]["emergency_message"])
            self.ui.naloxoneExpirationDateEdit.setSelectedDate(
                self.naloxone_expiration_date)
            self.ui.temperatureSlider.setValue(
                int(config["naloxone_info"]["absolute_maximum_temperature"]))
            self.ui.passcodeLineEdit.setText(config["admin"]["passcode"])
            self.ui.naloxonePasscodeLineEdit.setText(
                config["admin"]["naloxone_passcode"])
            self.ui.adminPhoneNumberLineEdit.setText(
                config["admin"]["admin_phone_number"])
            self.ui.enableSMSCheckBox.setChecked(
                config["admin"]["enable_sms"] == "True")
            self.ui.reportDoorOpenedCheckBox.setChecked(
                config["admin"]["report_door_opened"] == "True")
            self.ui.reportEmergencyCalledCheckBox.setChecked(
                config["admin"]["report_emergency_called"] == "True")
            self.ui.reportNaloxoneDestroyedCheckBox.setChecked(
                config["admin"]["report_naloxone_destroyed"] == "True")
            self.ui.reportSettingsChangedCheckBox.setChecked(
                config["admin"]["report_settings_changed"] == "True")
            self.ui.allowParamedicsCheckBox.setChecked(
                config["admin"]["allow_paramedics"] == "True")
            self.ui.startTimeEdit.setTime(self.active_hour_start)
            self.ui.endTimeEdit.setTime(self.active_hour_end)
            self.ui.enablePowerSavingCheckBox.setChecked(
                config["power_management"]["enable_power_saving"] == "True")
            self.ui.enableActiveCoolingCheckBox.setChecked(
                config["power_management"]["enable_active_cooling"] == "True")
        except Exception as e:
            return
        else:
            return

    def load_settings(self):
        # load the settings from the conf file.
        print("loading settings")
        try:
            config = configparser.ConfigParser()
            config.read("safety_kit.conf")
            self.ui.twilioSIDLineEdit.setText(config["twilio"]["twilio_sid"])
            self.twilio_sid = config["twilio"]["twilio_sid"]
            self.ui.twilioTokenLineEdit.setText(
                config["twilio"]["twilio_token"])
            self.twilio_token = config["twilio"]["twilio_token"]
            self.ui.twilioPhoneNumberLineEdit.setText(
                config["twilio"]["twilio_phone_number"])
            self.twilio_phone_number = config["twilio"]["twilio_phone_number"]
            self.ui.emergencyPhoneNumberLineEdit.setText(
                config["emergency_info"]["emergency_phone_number"])
            self.to_phone_number = config["emergency_info"]["emergency_phone_number"]
            self.ui.emergencyAddressLineEdit.setText(
                config["emergency_info"]["emergency_address"])
            self.address = config["emergency_info"]["emergency_address"]
            self.ui.emergencyMessageLineEdit.setText(
                config["emergency_info"]["emergency_message"])
            self.message = config["emergency_info"]["emergency_message"]
            self.naloxone_expiration_date = QtCore.QDate.fromString(
                config["naloxone_info"]["naloxone_expiration_date"])
            self.ui.naloxoneExpirationDateEdit.setSelectedDate(
                self.naloxone_expiration_date)
            self.ui.temperatureSlider.setValue(
                int(config["naloxone_info"]["absolute_maximum_temperature"]))
            self.max_temp = int(
                config["naloxone_info"]["absolute_maximum_temperature"])
            self.ui.passcodeLineEdit.setText(config["admin"]["passcode"])
            self.admin_passcode = config["admin"]["passcode"]
            self.ui.naloxonePasscodeLineEdit.setText(
                config["admin"]["naloxone_passcode"])
            self.naloxone_passcode = config["admin"]["naloxone_passcode"]
            self.ui.adminPhoneNumberLineEdit.setText(
                config["admin"]["admin_phone_number"])
            self.admin_phone_number = config["admin"]["admin_phone_number"]
            self.ui.enableSMSCheckBox.setChecked(
                config["admin"]["enable_sms"] == "True")
            self.ui.reportDoorOpenedCheckBox.setChecked(
                config["admin"]["report_door_opened"] == "True")
            self.ui.reportEmergencyCalledCheckBox.setChecked(
                config["admin"]["report_emergency_called"] == "True")
            self.ui.reportNaloxoneDestroyedCheckBox.setChecked(
                config["admin"]["report_naloxone_destroyed"] == "True")
            self.ui.reportSettingsChangedCheckBox.setChecked(
                config["admin"]["report_settings_changed"] == "True")
            self.ui.allowParamedicsCheckBox.setChecked(
                config["admin"]["allow_paramedics"] == "True")
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

            admin_qr_code = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=0
            )
            admin_qr_code.add_data(config["admin"]["admin_phone_number"])
            admin_qr_code.make(fit=True)
            img = admin_qr_code.make_image(
                fill_color="white", back_color=(50, 50, 50))
            img.save("admin_qrcode.png")
            admin_qrcode_pixmap = QtGui.QPixmap(
                "admin_qrcode.png").scaledToWidth(100).scaledToHeight(100)
            self.ui.admin_qrcode.setPixmap(admin_qrcode_pixmap)

            self.create_io_worker()
            self.create_network_worker()

        except Exception as e:
            print("Failed to load config file")
            msg = QtWidgets.QMessageBox()
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.setDetailedText("Error starting at item " + str(e))
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Failed to read config file. Going to setup process.")
            msg.setStyleSheet(
                "QMessageBox{background-color: black}QLabel{color: white;font-size:16px}QPushButton{ color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid; height:30;width:140; font-size:16px}")
            # msg.buttonClicked.connect(msg.close)
            msg.exec_()
            self.ui.unlockSettingsPushButton.setVisible(False)
            self.ui.lockSettingsPushButton.setVisible(True)
            self.ui.saveToFilePushButton.setVisible(True)
            self.ui.settingsTab.setTabVisible(0, True)
            self.ui.settingsTab.setTabVisible(1, True)
            self.ui.settingsTab.setTabVisible(2, True)
            self.ui.settingsTab.setTabVisible(3, True)
            self.ui.settingsTab.setTabVisible(4, True)
            self.ui.settingsTab.setTabVisible(5, True)
            self.ui.settingsTab.setCurrentIndex(1)
            self.ui.homePushButton.setChecked(False)
            self.ui.dashboardPushButton.setChecked(False)
            self.ui.settingsPushButton.setChecked(True)
            self.ui.stackedWidget.setCurrentIndex(2)

        else:
            print("config file loaded")

    def lock_settings(self):
        # lock the whole setting page.
        self.ui.unlockSettingsPushButton.setVisible(True)
        self.ui.lockSettingsPushButton.setVisible(False)
        self.ui.saveToFilePushButton.setVisible(False)
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabVisible(0, True)
        self.ui.settingsTab.setTabVisible(1, False)
        self.ui.settingsTab.setTabVisible(2, False)
        self.ui.settingsTab.setTabVisible(3, False)
        self.ui.settingsTab.setTabVisible(4, False)
        self.ui.settingsTab.setTabVisible(5, False)
        print("Settings locked")

    def unlock_naloxone_settings(self):
        self.ui.unlockSettingsPushButton.setVisible(False)
        self.ui.lockSettingsPushButton.setVisible(True)
        self.ui.saveToFilePushButton.setVisible(True)
        self.load_settings_ui()
        self.ui.settingsTab.setTabVisible(0, True)
        self.ui.settingsTab.setTabVisible(1, True)
        self.ui.settingsTab.setTabVisible(2, False)
        self.ui.settingsTab.setTabVisible(3, False)
        self.ui.settingsTab.setTabVisible(4, False)
        self.ui.settingsTab.setTabVisible(5, False)
        self.ui.settingsTab.setCurrentIndex(1)
        print("Naloxone Settings unlocked")

    def unlock_all_settings(self):
        # unlock the whole setting page. Should only be called after the user enter the correct passcode.
        self.ui.unlockSettingsPushButton.setVisible(False)
        self.ui.lockSettingsPushButton.setVisible(True)
        self.ui.saveToFilePushButton.setVisible(True)
        self.load_settings_ui()
        self.ui.settingsTab.setTabVisible(0, True)
        self.ui.settingsTab.setTabVisible(1, True)
        self.ui.settingsTab.setTabVisible(2, True)
        self.ui.settingsTab.setTabVisible(3, True)
        self.ui.settingsTab.setTabVisible(4, True)
        self.ui.settingsTab.setTabVisible(5, True)
        self.ui.settingsTab.setCurrentIndex(1)
        print("All Settings unlocked")

    def check_passcode(self):
        # First read from the conf file
        # return values:
        # 0: wrong passcode
        # 1: unlock all settings
        # 2: unlock naloxone settings
        if (self.admin_passcode == str() or self.ui.passcodeEnterLineEdit.text() == self.admin_passcode):
            return 1
        elif (self.naloxone_passcode == str() or self.ui.passcodeEnterLineEdit.text() == self.naloxone_passcode):
            return 2
        else:
            sleep(3)
            self.ui.passcodeEnterLabel.setText("Sorry, try again")
            self.ui.passcodeEnterLineEdit.clear()
            return 0

    def check_passcode_unlock_settings(self):
        passcode_check_result = self.check_passcode()
        if (passcode_check_result == 1):
            # If passcode is correct, unlock the settings
            self.goto_settings()
            self.unlock_all_settings()

        elif (passcode_check_result == 2):
            self.goto_settings()
            self.unlock_naloxone_settings()

        else:
            # If passcode is wrong, lock the settings
            self.lock_settings()

    def lock_unlock_settings(self):
        if (self.admin_passcode == str()):
            self.unlock_all_settings()
        else:
            self.goto_passcode()

    @QtCore.pyqtSlot()
    def goto_door_open(self):
        if (self.ui.stackedWidget.currentIndex() == 0 or self.ui.stackedWidget.currentIndex() == 1):
            # Only go to the door open page when the user is not changing settings.
            self.ui.homePushButton.setVisible(False)
            self.ui.dashboardPushButton.setVisible(False)
            self.ui.settingsPushButton.setVisible(False)
            self.ui.backPushButton.setVisible(False)
            self.ui.stackedWidget.setCurrentIndex(4)
            self.countdown_thread = CountDownWorker(10)
            self.countdown_thread.time_changed_signal.connect(
                self.update_emergency_call_countdown)
            self.countdown_thread.time_end_signal.connect(
                self.call_emergency_now)
            self.countdown_thread.time_end_signal.connect(self.speak_now)
            self.countdown_thread.start()

    def back_pushbutton_pushed(self):
        self.ui.settingsPushButton.setChecked(False)
        self.ui.settingsPushButton.setEnabled(True)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(4)

    def goto_passcode(self):
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.passcodeEnterLabel.setText("Enter Passcode")
        self.ui.paramedicsPhoneNumberLineEdit.clear()
        self.ui.stackedWidget.setCurrentIndex(3)

    def goto_settings(self):
        self.ui.homePushButton.setChecked(False)
        self.ui.dashboardPushButton.setChecked(False)
        self.ui.settingsPushButton.setChecked(True)
        if (self.ui.stackedWidget.currentIndex() == 4):
            # When entering the setting page from the door open page,
            # show the go back pushbutton so that the user can go back to the
            # door open page.
            self.ui.backPushButton.setVisible(True)
        self.ui.stackedWidget.setCurrentIndex(2)
        if (self.admin_passcode == str()):
            self.unlock_all_settings()

    def goto_dashboard(self):
        self.ui.homePushButton.setChecked(False)
        self.ui.dashboardPushButton.setChecked(True)
        self.ui.settingsPushButton.setChecked(False)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(1)

    def goto_home(self):
        self.ui.homePushButton.setChecked(True)
        self.ui.dashboardPushButton.setChecked(False)
        self.ui.settingsPushButton.setChecked(False)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(0)

    def send_sms_using_config_file(self, msg):
        # Used to contact the admin via the info in the conf file
        self.sender = SMSWorker(self.admin_phone_number, "The naloxone safety box at " +
                                self.address + " sent the following information: " + msg, self.twilio_sid, self.twilio_token, self.twilio_phone_number)
        self.sender.start()

    def call_911_using_config_file(self):
        loop = "0"
        voice = "woman"

        # create the response
        response = VoiceResponse()
        response.say("Message: " + self.message + ". Address: " +
                     self.address + ".", voice=voice, loop=loop)
        print("INFO: resonse: " + str(response))

        self.sender = CallWorker(
            self.to_phone_number, response, self.twilio_sid, self.twilio_token, self.twilio_phone_number)
        self.sender.call_thread_status.connect(self.update_phone_call_gui)
        self.sender.start()

    def sms_test_pushbutton_clicked(self):
        # Use the info on the setting page to make sms test.
        phone_number = self.ui.adminPhoneNumberLineEdit.text()
        t_sid = self.ui.twilioSIDLineEdit.text()
        t_token = self.ui.twilioTokenLineEdit.text()
        t_number = self.ui.twilioPhoneNumberLineEdit.text()
        body = ("Internet-based Naloxone Safety Kit. " +
                "These are the words that will be heard by " + self.ui.emergencyPhoneNumberLineEdit.text() +
                " when the door is opened: Message: " + self.ui.emergencyMessageLineEdit.text() + ". Address: " +
                self.ui.emergencyAddressLineEdit.text() +
                ". If the words sound good, you can save the settings. Thank you.")
        self.sms_worker = SMSWorker(
            phone_number, body, t_sid, t_token, t_number)
        self.sms_worker.sms_thread_status.connect(self.display_messagebox)
        self.sms_worker.start()

    def call_test_pushbutton_clicked(self):
        # Use the info on the setting page to make phone call test
        phone_number = self.ui.adminPhoneNumberLineEdit.text()
        t_sid = self.ui.twilioSIDLineEdit.text()
        t_token = self.ui.twilioTokenLineEdit.text()
        t_number = self.ui.twilioPhoneNumberLineEdit.text()
        response = VoiceResponse()
        response.say("Internet-based Naloxone Safety Kit. " +
                     "These are the words that will be heard by " + " ".join(self.ui.emergencyPhoneNumberLineEdit.text()) +
                     " when the door is opened: Message: " + self.ui.emergencyMessageLineEdit.text() + ". Address: " +
                     self.ui.emergencyAddressLineEdit.text() +
                     ". If the call sounds good, you can save the settings. Thank you.", voice="woman", loop=3)

        self.call_worker = CallWorker(
            phone_number, response, t_sid, t_token, t_number)
        self.call_worker.call_thread_status.connect(self.display_messagebox)
        self.call_worker.start()

    def toggle_door_arm(self):
        # Used to disable the door switch
        self.door_arm_thread = GenericWorker(
            self.toggle_door_arm_thread)
        self.door_arm_thread.msg_info_signal.connect(self.display_messagebox)
        self.door_arm_thread.start()

    def toggle_door_arm_thread(self):
        if (self.ui.disarmPushButton.text() == "Disarm"):
            self.ui.disarmPushButton.setText("Arm")
            self.disarmed = True
            self.create_io_worker()
            return "Information", "Door Disarmed.", "The door sensor is now off."
        else:
            self.ui.disarmPushButton.setText("Disarm")
            self.disarmed = False
            self.create_io_worker()
            return "Information", "Door Armed.", "The door sensor is now on."

    def reset_button_pushed(self):
        # Create a thread to check the shared memory for door status.
        self.reset_thread = GenericWorker(
            self.reset_after_door_open)
        self.reset_thread.msg_info_signal.connect(
            self.display_messagebox)
        self.reset_thread.start()

    def auto_reset(self):
        # Used to auto reset the door if closed with the countdown time.
        self.reset_thread = GenericWorker(
            self.reset_after_door_open)
        self.reset_thread.start()

    def reset_after_door_open(self):
        # Used to check whether the door is still opened
        if (self.door_opened):
            print("door is still opened")
            return "Critical", "Please close the door first.", "The system needs some time to detect the door status change."
        else:
            self.goto_home()
            self.ui.homePushButton.setVisible(True)
            self.ui.dashboardPushButton.setVisible(True)
            self.ui.settingsPushButton.setVisible(True)
            self.ui.stopCountdownPushButton.setVisible(True)
            self.ui.countdownLabel.setVisible(True)
            self.ui.emergencyCallCountdownLabel.setVisible(True)
            self.ui.alarmStatusLabel.setText("Waiting")
            self.ui.alarmMutePushButton.setVisible(True)
            self.ui.emergencyCallStatusLabel.setText("Waiting")
            self.ui.emergencyCallLastCallLabel.setText("N/A")
            return "Information", "System Reset to Default.", "N/A"

    def stop_countdown_button_pushed(self):
        # Stop the countdown timer by stop it.
        self.ui.settingsPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        self.ui.emergencyCallStatusLabel.setText("N/A")
        self.ui.alarmStatusLabel.setText("Muted")
        self.ui.alarmMutePushButton.setVisible(False)
        self.ui.emergencyCallLastCallLabel.setText("N/A")
        self.countdown_thread.stop()

    def forgot_password_button_pushed(self):
        # when the forgot password button is pushed, use the conf file to send
        # the passcode
        self.send_sms_using_config_file("Passcode is " + self.admin_passcode)

    def get_passcode_button_pushed(self):
        print("Enter function")
        paramedic_phone_number = self.ui.paramedicsPhoneNumberLineEdit.text()
        self.send_to_paramedic = SMSWorker(paramedic_phone_number, "The passcode of the naloxone safety box at " +
                                           self.address + " is: " + self.naloxone_passcode, self.twilio_sid, self.twilio_token, self.twilio_phone_number)
        self.send_to_paramedic.start()
        print("sent to paramedics")
        self.send_sms_using_config_file(
            "Paramedics want to access the settings. The number is " + paramedic_phone_number + ".")
        print("sent to admin")

    @QtCore.pyqtSlot()
    def speak_now(self):
        print("speak now")
        self.create_alarm_worker()
        self.ui.alarmStatusLabel.setText("Speaking")

    @QtCore.pyqtSlot()
    def stop_alarm(self):
        if (self.alarm_worker is not None):
            self.alarm_worker.quit()
            self.alarm_worker.requestInterruption()
        self.ui.alarmStatusLabel.setText("Muted")
        self.ui.alarmMutePushButton.setVisible(False)

    @QtCore.pyqtSlot()
    # Used to communicate with the shm to make phone calls.
    def call_emergency_now(self):
        print("call 911 now pushed")
        self.call_911_using_config_file()
        self.ui.emergencyCallStatusLabel.setText("Requested")
        self.ui.settingsPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        if (self.ui.stopCountdownPushButton.isVisible()):
            self.ui.stopCountdownPushButton.setVisible(False)
            self.countdown_thread.stop()

    @QtCore.pyqtSlot(int)
    def update_emergency_call_countdown(self, sec):
        # Used to update the GUI for the countdown time.
        self.ui.emergencyCallCountdownLabel.setText("T-" + str(sec) + "s")
        if (not self.door_opened):
            # when the door is closed within the countdown time, auto reset it.
            self.stop_countdown_button_pushed()
            self.auto_reset()

    @QtCore.pyqtSlot(str, str, str)
    def update_phone_call_gui(self, icon, text, detailed_text):
        if (text == "Call Request Sent Successfully."):
            self.ui.emergencyCallStatusLabel.setText("Successful")
            self.ui.emergencyCallLastCallLabel.setText(
                QtCore.QTime().currentTime().toString("h:mm AP"))
        else:
            self.ui.emergencyCallStatusLabel.setText("Failed")

    @QtCore.pyqtSlot(str, str, str)
    def display_messagebox(self, icon, text, detailed_text):
        # Used to show messagebox above the main window.
        msg = QtWidgets.QMessageBox()
        msg.setText(text)
        msg.setDetailedText(detailed_text)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        if (icon == "Information"):
            msg.setIcon(QtWidgets.QMessageBox.Information)
        elif (icon == "Critical"):
            msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setStyleSheet("QMessageBox{background-color: black}QLabel{color: white;font-size:16px}QPushButton{ color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid; height:30;width:140; font-size:16px}")
        msg.exec_()

    @QtCore.pyqtSlot(bool, bool)
    def update_door_ui(self, door, armed):
        # Update the door ui of the main window.
        if (not door):
            self.ui.doorClosedLineEdit.setText("Closed")
            self.ui.doorOpenLabel.setText("Closed")
            self.door_opened = False
        else:
            self.ui.doorClosedLineEdit.setText("Open")
            self.ui.doorOpenLabel.setText("Open")
            self.door_opened = True
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
        # update the naloxone of the main window.
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

    @QtCore.pyqtSlot(bool, float, str, QtCore.QTime)
    def update_server_ui(self, server, balance, currency, server_check_time):
        # update the server of the main window
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
        self.ui.accountBalanceLineEdit.setText(
            str(round(balance, 2)) + " " + currency)

    @QtCore.pyqtSlot(int, int, int, bool)
    def update_temperature_ui(self, temperature, cpu_temperature, pwm, over_temperature):
        # update the temperature of the main window.
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

    @QtCore.pyqtSlot(int)
    def update_current_max_temperature(self, value):
        # Used to update the current temperature selection when the user uses
        # the slider on the setting page.
        self.ui.CurrentTemperatureLabel.setText(str(value)+"℉")

    def save_config_file(self):
        # save the config file
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
            "naloxone_expiration_date": self.ui.naloxoneExpirationDateEdit.selectedDate().toString(),
            "absolute_maximum_temperature": self.ui.temperatureSlider.value()
        }
        config["admin"] = {
            "passcode": self.ui.passcodeLineEdit.text(),
            "naloxone_passcode": self.ui.naloxonePasscodeLineEdit.text(),
            "admin_phone_number": self.ui.adminPhoneNumberLineEdit.text(),
            "enable_sms": self.ui.enableSMSCheckBox.isChecked(),
            "report_door_opened": self.ui.reportDoorOpenedCheckBox.isChecked(),
            "report_emergency_called": self.ui.reportEmergencyCalledCheckBox.isChecked(),
            "report_naloxone_destroyed": self.ui.reportNaloxoneDestroyedCheckBox.isChecked(),
            "report_settings_changed": self.ui.reportSettingsChangedCheckBox.isChecked(),
            "allow_paramedics": self.ui.allowParamedicsCheckBox.isChecked()
        }
        config["power_management"] = {
            "enable_active_cooling": self.ui.enableActiveCoolingCheckBox.isChecked(),
            "enable_power_saving": self.ui.enablePowerSavingCheckBox.isChecked(),
            "active_hours_start_at": self.active_hour_start.toString("hh:mm"),
            "active_hours_end_at": self.active_hour_end.toString("hh:mm")
        }
        with open("safety_kit.conf", "w") as configfile:
            config.write(configfile)
        msg = QtWidgets.QMessageBox()
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Config file saved as safety_kit.conf.")
        msg.setStyleSheet(
            "QMessageBox{background-color: black}QLabel{color: white;font-size:16px}QPushButton{ color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid; height:30;width:140; font-size:16px}")
        msg.exec_()
        if (self.ui.enableSMSCheckBox.isChecked() and self.ui.reportSettingsChangedCheckBox.isChecked()):
            self.send_sms_using_config_file("Settings Changed")
        print("INFO: save config file")
        self.load_settings()

    def exit_program(self):
        self.close()


def gui_manager():
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    app = QtWidgets.QApplication(sys.argv)
    QtGui.QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    gui_manager()
