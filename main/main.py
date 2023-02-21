from PyQt5.QtWidgets import QMainWindow, QScroller, QApplication
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QDate, QFile, QTime, QDateTime, QTimer, QTextStream, QIODevice, Qt
from PyQt5.QtGui import QPixmap, QGuiApplication, QRegion
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
import os
import sys
from queue import Queue, PriorityQueue
from configparser import ConfigParser
from ui_main_window import Ui_door_close_main_window
from time import sleep
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_M
from random import choice
from gtts import gTTS
from phonenumbers import parse, is_valid_number
from dataclasses import dataclass, field
from typing import Any

DOOR_PIN = 17
DHT_PIN = 27
FAN_PIN = 12
RESET_PIN = 22
RASPBERRY = True


@dataclass(order=True)
class RequestItem:
    priority: int
    request_type: str = field(compare=False)
    destination_number: str = field(compare=False)
    message: str = field(compare=False)
    twilio_sid: str = field(compare=False)
    twilio_token: str = field(compare=False)
    twilio_number: str = field(compare=False)


@dataclass(order=True)
class NotificationItem:
    priority: int
    message: str = field(compare=False)


@dataclass
class IOItem:
    disarmed: bool
    max_temp: int
    fan_threshold_temp: int
    expiration_date: QDate


def handleVisibleChanged():
    # control the position of the virtual keyboard
    if not QGuiApplication.inputMethod().isVisible():
        return
    for w in QGuiApplication.allWindows():
        if w.metaObject().className() == "QtVirtualKeyboard::InputView":
            keyboard = w.findChild(QObject, "keyboard")
            if keyboard is not None:
                r = w.geometry()
                r.moveTop(int(keyboard.property("y")))
                w.setMask(QRegion(r))
                return


class CountDownWorker(QThread):
    # Used to record the countdown time before calling the emergency
    # signal to indicate end of countdown time.
    time_end_signal = pyqtSignal()
    # signal to indicate the change of countdown time.
    time_changed_signal = pyqtSignal(int)

    def __init__(self, time_in_sec):
        super(CountDownWorker, self).__init__()
        self.countdown_time_in_sec = time_in_sec
        self.time_in_sec = time_in_sec

    def run(self):
        while (self.time_in_sec >= 0):
            if (self.isInterruptionRequested()):
                print("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            self.time_changed_signal.emit(self.time_in_sec)
            self.time_in_sec = self.time_in_sec - 1
            if (self.isInterruptionRequested()):
                print("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            sleep(1)

        if (self.time_in_sec == -1):
            self.time_end_signal.emit()

    def stop(self):
        print("countdown timer terminated")
        self.terminate()


class IOWorker(QThread):
    update_door = pyqtSignal(bool, bool)
    update_temperature = pyqtSignal(int, int, int, bool)
    update_naloxone = pyqtSignal(bool, QDate)
    go_to_door_open_signal = pyqtSignal()

    def __init__(self, in_queue):
        super(IOWorker, self).__init__()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DOOR_PIN, GPIO.IN)

        self.naloxone_counter = 9
        self.in_queue = in_queue
        self.initialized = False

    def read_naloxone_sensor(self):
        _, self.naloxone_temp = dht.read_retry(dht.DHT22, DHT_PIN)
        self.naloxone_temp = int(self.naloxone_temp * 1.8 + 32)
        # self.temperature = 77

    def calculate_pwm(self):
        # print("control pwm")
        list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
        if (self.cpu_temp < self.fan_threshold_temp):
            self.fan_pwm = 0
        else:
            self.fan_pwm = choice(list1)

    def send_pwm(self):
        return

    def read_cpu_sensor(self):
        self.cpu_temp = int(CPUTemperature().temperature * 1.8 + 32)
        # self.cpu_temp = 100

    def read_door_sensor(self):
        # self.door_opened = False
        # return
        if GPIO.input(DOOR_PIN):
            self.door_opened = True
        else:
            self.door_opened = False

    def is_expiry(self):
        today = QDate().currentDate()
        return today > self.expiration_date

    def is_overheat(self):
        return self.max_temp < self.naloxone_temp

    def run(self):
        while True:
            if (self.isInterruptionRequested()):
                break
            if (not self.initialized or not self.in_queue.empty()):
                config = self.in_queue.get()
                self.disarmed = config.disarmed
                self.max_temp = config.max_temp
                self.fan_threshold_temp = config.fan_threshold_temp
                self.expiration_date = config.expiration_date
                self.naloxone_counter = 9
                self.initialized = True
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

            if (self.isInterruptionRequested()):
                break
            sleep(1)


class AlarmWorker(QThread):
    def __init__(self, alarm_message, voice_volume, loop):
        super(AlarmWorker, self).__init__()
        self.alarm_message = alarm_message
        self.voice_volume = voice_volume
        self.loop = loop
        self.tts = gTTS(self.alarm_message, lang="en")
        self.tts.save("res/alarm.mp3")
        os.system("pactl set-sink-volume 0 {}%".format(self.voice_volume))
        print("alarm thread go.")

    def run(self):
        if (self.loop):
            # loop until stopped by interruption
            while (True):
                if (self.isInterruptionRequested()):
                    break
                print("playing")
                os.system("mpg123 -q res/alarm.mp3")
                if (self.isInterruptionRequested()):
                    break
                sleep(1)
        else:
            print("saying alarm now.")
            os.system("mpg123 -q res/alarm.mp3")
            print("finish")


class NetworkWorker(QThread):
    update_server = pyqtSignal(bool, float, str, QTime)

    def __init__(self, twilio_sid, twilio_token):
        super(NetworkWorker, self).__init__()
        self.hostname = "www.twilio.com"  # ping twilio directly
        print("network thread go.")
        self.currentTime = QTime()
        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token

    def run(self):
        try:
            client = Client(self.twilio_sid, self.twilio_token)
            response = os.system(" ".join(["ping -c 1", self.hostname]))
            if (response == 1):
                self.update_server.emit(
                    False, 0, "USD", self.currentTime.currentTime())
            else:
                balance = client.api.v2010.balance.fetch().balance
                currency = client.api.v2010.balance.fetch().currency
                self.update_server.emit(True, float(
                    balance), currency, self.currentTime.currentTime())
        except Exception as e:
            self.update_server.emit(
                False, 0, "USD", self.currentTime.currentTime())


class TwilioWorker(QThread):
    twilio_thread_status = pyqtSignal(int, str)
    emergency_call_status = pyqtSignal(int, str)

    def __init__(self, in_queue, out_queue):
        super(TwilioWorker, self).__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue

    def run(self):
        while True:
            request = self.in_queue.get()  # blocking
            if (request.request_type == "exit"):
                # used to exit the thread
                break
            if (request.request_type == "call"):
                try:
                    client = Client(request.twilio_sid, request.twilio_token)
                    call = client.calls.create(
                        twiml=request.message, to=request.destination_number, from_=request.twilio_number)
                except Exception as e:
                    print("ERROR: {}".format(str(e)))
                    self.out_queue.put(NotificationItem(
                        request.priority, "Call Failed"))
                    if (request.priority == 0):
                        self.emergency_call_status.emit(0, "Call Failed")
                else:
                    print(call.sid)
                    self.out_queue.put(NotificationItem(
                        request.priority, "Call Delivered"))
                    if (request.priority == 0):
                        self.emergency_call_status.emit(0, "Call Delivered")
            else:
                try:
                    client = Client(request.twilio_sid, request.twilio_token)
                    sms = client.messages.create(
                        body=request.message,
                        to=request.destination_number,
                        from_=request.twilio_number
                    )
                except Exception as e:
                    # if not successful, return False
                    print("ERROR: Twilio SMS: ERROR - {}".format(str(e)))
                    self.out_queue.put(NotificationItem(
                        request.priority, "SMS Failed"))
                else:
                    # if successful, return True
                    print(sms.sid)
                    self.out_queue.put(NotificationItem(
                        request.priority, "SMS Delivered"))


class ApplicationWindow(QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.door_opened = False
        self.disarmed = False
        self.max_temp = 0
        self.fan_threshold_temp = 0
        self.admin_passcode = str()
        self.naloxone_passcode = str()
        self.twilio_sid = str()
        self.twilio_token = str()
        self.twilio_phone_number = str()
        self.admin_phone_number = str()
        self.address = str()
        self.to_phone_number = str()
        self.message = str()
        self.naloxone_expiration_date = QDate().currentDate()
        self.active_hour_start = QTime(8, 0, 0)
        self.active_hour_end = QTime(18, 0, 0)
        self.alarm_message = str()
        self.voice_volume = 20
        self.status_queue = PriorityQueue()
        self.request_queue = PriorityQueue()
        self.io_queue = Queue()
        self.message_to_display = str()
        self.message_level = 0
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        self.ui.disarmPushButton.clicked.connect(self.disarm_door_sensor)
        self.ui.armPushButton.clicked.connect(self.arm_door_sensor)
        self.ui.homePushButton.clicked.connect(self.goto_home)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.replace_naloxone_button_2.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        self.ui.unlockSettingsPushButton.clicked.connect(
            self.lock_unlock_settings)
        self.ui.lockSettingsPushButton.clicked.connect(self.lock_settings)
        self.ui.lockSettingsPushButton.setVisible(False)
        self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        self.ui.temperatureSlider.valueChanged.connect(
            self.update_current_max_temperature)
        self.ui.fan_temperature_slider.valueChanged.connect(
            self.update_current_threshold_temperature)
        self.ui.voice_volume_slider.valueChanged.connect(
            self.update_voice_volume)
        self.ui.callTestPushButton.clicked.connect(
            self.call_test_pushbutton_clicked)
        self.ui.smsTestPushButton.clicked.connect(
            self.sms_test_pushbutton_clicked)
        self.ui.passcodeEnterPushButton.clicked.connect(
            self.check_passcode_unlock_settings)
        self.ui.doorOpenResetPushButton.clicked.connect(
            self.reset_to_default)
        self.ui.stopCountdownPushButton.clicked.connect(
            self.stop_countdown_button_pushed)
        self.ui.call911NowPushButton.clicked.connect(self.call_emergency_now)
        self.ui.forgotPasswordPushButton.clicked.connect(
            self.forgot_password_button_pushed)
        self.ui.backPushButton.clicked.connect(self.back_pushbutton_pushed)
        self.ui.alarmMutePushButton.clicked.connect(self.stop_alarm)
        self.ui.test_alarm_pushbutton.clicked.connect(self.test_tts_engine)
        self.ui.notify_admin_button.clicked.connect(self.notify_admin)
        self.ui.notify_admin_button_2.clicked.connect(self.notify_admin)
        self.ui.notify_admin_button_3.clicked.connect(self.notify_admin)
        self.ui.get_passcode_button.clicked.connect(
            self.get_passcode_button_pressed)
        self.ui.paramedic_phone_number_lineedit.textChanged.connect(
            self.phone_number_validator)
        self.ui.twilioPhoneNumberLineEdit.textChanged.connect(
            self.phone_number_validator)
        self.ui.emergencyPhoneNumberLineEdit.textChanged.connect(
            self.phone_number_validator)
        self.ui.adminPhoneNumberLineEdit.textChanged.connect(
            self.phone_number_validator)
        self.ui.twilioSIDLineEdit.textChanged.connect(
            self.twilio_sid_validator)
        self.ui.home_frame.setStyleSheet(
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/background.jpg) 0 0 0 0 stretch stretch}")

        QScroller.grabGesture(
            self.ui.manual_textedit.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.ui.naloxone_scroll_area.viewport(
        ), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(
            self.ui.twilio_scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(
            self.ui.call_scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(
            self.ui.alarm_scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(
            self.ui.power_scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(
            self.ui.admin_scroll_area.viewport(), QScroller.LeftMouseButtonGesture)

        self.load_manual()

        self.generate_ui_qrcode()

        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.create_network_worker)

        self.twilio_worker = None
        self.network_worker = None
        self.io_worker = None
        self.alarm_worker = None
        self.countdown_worker = None
        self.create_io_worker()
        self.create_twilio_worker()
        self.twilio_worker.emergency_call_status.connect(
            self.update_phone_call_gui)

        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.create_network_worker)

        self.status_bar_timer = QTimer()
        self.status_bar_timer.timeout.connect(self.update_time_status)
        self.update_time_status()
        self.status_bar_timer.start(2000)

        self.dashboard_timer = QTimer()
        self.dashboard_timer.timeout.connect(self.goto_home)
        self.dashboard_timer.setSingleShot(True)

        self.goto_home()
        self.lock_settings()
        self.load_settings()
        self.door_opened = True
        self.goto_door_open()

    def destroy_twilio_worker(self):
        if (self.twilio_worker is not None):
            self.twilio_worker.quit()
            self.twilio_worker.requestInterruption()
            self.twilio_worker.wait()

    def create_twilio_worker(self):
        self.destroy_twilio_worker()
        self.twilio_worker = TwilioWorker(
            self.request_queue, self.status_queue)
        self.twilio_worker.start()

    def destroy_io_worker(self):
        if (self.io_worker is not None):
            self.io_worker.quit()
            self.io_worker.requestInterruption()
            self.io_worker.wait()

    def create_io_worker(self):
        if(not RASPBERRY):
            return
        self.destroy_io_worker()
        self.io_worker = IOWorker(self.io_queue)
        self.io_worker.update_door.connect(self.update_door_ui)
        self.io_worker.go_to_door_open_signal.connect(self.goto_door_open)
        self.io_worker.update_temperature.connect(
            self.update_temperature_ui)
        self.io_worker.update_naloxone.connect(self.update_naloxone_ui)
        self.io_worker.start()  # will be blocked when no config is sent

    def destroy_call_worker(self):
        if (self.call_worker is not None):
            # wait for the call worker to stop. Do not terminate
            self.call_worker.wait()

    def create_call_request(self, number, body, t_sid, t_token, t_number, priority=4):
        request = RequestItem(priority, "call", number, body,
                              t_sid, t_token, t_number)
        self.request_queue.put(request)  # blocking

    def destroy_sms_worker(self):
        if (self.sms_worker is not None):
            self.sms_worker.wait()

    def create_sms_request(self, number, body, t_sid, t_token, t_number, priority=4):
        request = RequestItem(priority, "SMS", number,
                              body, t_sid, t_token, t_number)
        self.request_queue.put(request)  # blocking

    def destroy_network_worker(self):
        if (self.network_worker is not None):
            self.network_worker.quit()
            self.network_worker.requestInterruption()
            self.network_worker.wait()

    def create_network_worker(self):
        self.destroy_network_worker()
        self.network_worker = NetworkWorker(self.twilio_sid, self.twilio_token)
        self.network_worker.update_server.connect(
            self.update_server_ui)
        self.network_worker.start()

    def destroy_alarm_worker(self):
        if (self.alarm_worker is not None):
            self.alarm_worker.quit()
            self.alarm_worker.requestInterruption()
            self.alarm_worker.wait()

    def create_alarm_worker(self, alarm_message, voice_volume, loop):
        self.destroy_alarm_worker()
        self.alarm_worker = AlarmWorker(
            alarm_message, voice_volume, loop)
        self.alarm_worker.start()

    def destroy_countdown_worker(self):
        if (self.countdown_worker is not None):
            self.countdown_worker.quit()
            self.countdown_worker.requestInterruption()
            self.countdown_worker.wait()

    def create_countdown_worker(self, time):
        print("creating countdown worker...")
        self.destroy_countdown_worker()
        self.countdown_worker = CountDownWorker(time)
        self.countdown_worker.time_changed_signal.connect(
            self.update_emergency_call_countdown)
        self.countdown_worker.time_end_signal.connect(
            self.call_emergency_now)
        self.countdown_worker.start()

    def send_notification(self, priority, message):
        self.status_queue.put(NotificationItem(priority, message))  # blocking

    def load_manual(self):
        file = QFile('../user_manual/gui_manual/settings_manual.md')
        if not file.open(QIODevice.ReadOnly):
            self.send_notification(0, "Manual File Missing")
        stream = QTextStream(file)
        self.ui.manual_textedit.setMarkdown(stream.readAll())

    def generate_ui_qrcode(self):
        github_qr_code = QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        github_qr_code.add_data(
            "https://github.com/zyl120/Naloxone_Safety_Kit")
        github_qr_code.make(fit=True)
        img = github_qr_code.make_image(
            fill_color="white", back_color="black")
        img.save("res/github_qrcode.png")
        github_qrcode_pixmap = QPixmap(
            "res/github_qrcode.png").scaledToWidth(100).scaledToHeight(100)
        self.ui.github_qrcode.setPixmap(github_qrcode_pixmap)

    def load_settings_ui(self):
        try:
            # Load the settings from the conf file, will not handle exceptions.
            # Should be used when it is absolutely safe to do so.
            config = ConfigParser()
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
            self.ui.fan_temperature_slider.setValue(
                int(config["power_management"]["threshold_temperature"]))
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
            self.ui.alarm_message_lineedit.setText(
                config["alarm"]["alarm_message"])
            self.ui.voice_volume_slider.setValue(
                int(config["alarm"]["voice_volume"]))
        except Exception as e:
            return
        else:
            return

    def load_settings(self):
        # load the settings from the conf file.
        try:
            config = ConfigParser()
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
            self.naloxone_expiration_date = QDate.fromString(
                config["naloxone_info"]["naloxone_expiration_date"])
            self.ui.naloxoneExpirationDateEdit.setSelectedDate(
                self.naloxone_expiration_date)
            self.ui.temperatureSlider.setValue(
                int(config["naloxone_info"]["absolute_maximum_temperature"]))
            self.ui.fan_temperature_slider.setValue(
                int(config["power_management"]["threshold_temperature"]))
            self.max_temp = int(
                config["naloxone_info"]["absolute_maximum_temperature"])
            self.fan_threshold_temp = int(
                config["power_management"]["threshold_temperature"])
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
            if (config["admin"]["allow_paramedics"] == "False"):
                self.ui.paramedic_frame.setVisible(False)
                self.ui.admin_only_frame.setVisible(True)
            else:
                self.ui.paramedic_frame.setVisible(True)
                self.ui.admin_only_frame.setVisible(False)
            self.active_hour_start = QTime.fromString(
                config["power_management"]["active_hours_start_at"], "hh:mm")
            self.ui.startTimeEdit.setTime(self.active_hour_start)
            self.active_hour_end = QTime.fromString(
                config["power_management"]["active_hours_end_at"], "hh:mm")
            self.ui.endTimeEdit.setTime(self.active_hour_end)
            self.ui.enablePowerSavingCheckBox.setChecked(
                config["power_management"]["enable_power_saving"] == "True")
            self.ui.enableActiveCoolingCheckBox.setChecked(
                config["power_management"]["enable_active_cooling"] == "True")
            self.ui.alarm_message_lineedit.setText(
                config["alarm"]["alarm_message"])
            self.alarm_message = config["alarm"]["alarm_message"]
            self.ui.voice_volume_slider.setValue(
                int(config["alarm"]["voice_volume"]))
            self.voice_volume = int(config["alarm"]["voice_volume"])

            admin_qr_code = QRCode(
                version=None,
                error_correction=ERROR_CORRECT_M,
                box_size=10,
                border=0
            )
            admin_qr_code.add_data(config["admin"]["admin_phone_number"])
            admin_qr_code.make(fit=True)
            img = admin_qr_code.make_image(
                fill_color="white", back_color="black")
            img.save("res/admin_qrcode.png")
            admin_qrcode_pixmap = QPixmap(
                "res/admin_qrcode.png").scaledToWidth(100).scaledToHeight(100)
            self.ui.admin_qrcode.setPixmap(admin_qrcode_pixmap)

            self.io_queue.put(IOItem(
                False, self.max_temp, self.fan_threshold_temp, self.naloxone_expiration_date))
            self.create_network_worker()  # initialize the network checker.
            self.network_timer.start(600000)

        except Exception as e:
            self.send_notification(0, "Failed to load config file")
            self.send_notification(4, "Enter OOBE Mode")
            self.ui.unlock_icon.setVisible(True)
            self.ui.unlockSettingsPushButton.setVisible(False)
            self.ui.lockSettingsPushButton.setVisible(True)
            self.ui.saveToFilePushButton.setVisible(True)
            self.ui.settingsTab.setTabVisible(0, True)
            self.ui.settingsTab.setTabVisible(1, True)
            self.ui.settingsTab.setTabVisible(2, True)
            self.ui.settingsTab.setTabVisible(3, True)
            self.ui.settingsTab.setTabVisible(4, True)
            self.ui.settingsTab.setTabVisible(5, True)
            self.ui.settingsTab.setTabVisible(6, True)
            self.ui.settingsTab.setCurrentIndex(1)
            self.ui.homePushButton.setChecked(False)
            self.ui.dashboardPushButton.setChecked(False)
            self.ui.settingsPushButton.setChecked(True)
            self.ui.stackedWidget.setCurrentIndex(2)
            self.disarm_door_sensor()
            self.ui.homePushButton.setVisible(False)
            self.ui.dashboardPushButton.setVisible(False)

        else:
            self.send_notification(4, "Config Reloaded")
            self.ui.homePushButton.setVisible(True)
            self.ui.dashboardPushButton.setVisible(True)
            self.arm_door_sensor()

    def lock_settings(self):
        # lock the whole setting page.
        self.ui.unlock_icon.setVisible(False)
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
        self.ui.settingsTab.setTabVisible(6, False)

    def unlock_naloxone_settings(self):
        self.ui.unlock_icon.setVisible(True)
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
        self.ui.settingsTab.setTabVisible(6, False)
        self.ui.settingsTab.setCurrentIndex(1)

    def unlock_all_settings(self):
        # unlock the whole setting page. Should only be called after the user enter the correct passcode.
        self.ui.unlock_icon.setVisible(True)
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
        self.ui.settingsTab.setTabVisible(6, True)
        self.ui.settingsTab.setCurrentIndex(1)

    def check_passcode(self):
        # First read from the conf file
        # return values:
        # 0: wrong passcode
        # 1: unlock all settings
        # 2: unlock naloxone settings
        if (self.admin_passcode == str() or self.ui.passcodeEnterLineEdit.text() == self.admin_passcode):
            return 1
        if (self.ui.passcodeEnterLineEdit.text() == self.naloxone_passcode):
            return 2
        else:
            self.send_notification(0, "Wrong Passcode")
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

    @pyqtSlot()
    def goto_door_open(self):
        self.dashboard_timer.stop()
        if (self.ui.stackedWidget.currentIndex() == 0 or self.ui.stackedWidget.currentIndex() == 1):
            # Only go to the door open page when the user is not changing settings.
            self.ui.doorOpenResetPushButton.setVisible(False)
            self.ui.homePushButton.setVisible(False)
            self.ui.replace_naloxone_button_2.setVisible(False)
            self.ui.dashboardPushButton.setVisible(False)
            self.ui.settingsPushButton.setVisible(False)
            self.ui.backPushButton.setVisible(False)
            self.ui.alarmMutePushButton.setVisible(False)
            self.ui.stackedWidget.setCurrentIndex(4)
            self.create_countdown_worker(10)

    def back_pushbutton_pushed(self):
        self.ui.settingsPushButton.setChecked(False)
        self.ui.settingsPushButton.setEnabled(True)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(4)

    def goto_passcode(self):
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.paramedic_phone_number_lineedit.clear()
        self.ui.passcodeEnterLabel.setText("Enter Passcode")
        self.ui.stackedWidget.setCurrentIndex(3)

    def goto_settings(self):
        self.dashboard_timer.stop()
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
        # wait for 1 min before going back to home
        self.dashboard_timer.start(60000)

    def goto_home(self):
        self.dashboard_timer.stop()
        self.ui.homePushButton.setChecked(True)
        self.ui.dashboardPushButton.setChecked(False)
        self.ui.settingsPushButton.setChecked(False)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(0)

    def send_sms_using_config_file(self, msg):
        # Used to contact the admin via the info in the conf file
        self.create_sms_request(self.admin_phone_number, " ".join(
            ["The naloxone safety box at", self.address, "sent the following information:", msg]), self.twilio_sid, self.twilio_token, self.twilio_phone_number)
        self.send_notification(4, "SMS Requested")

    def call_911_using_config_file(self):
        loop = "0"
        voice = "woman"

        # create the response
        response = VoiceResponse()
        response.say("".join(["Someone has overdosed at ",
                     self.address, ". ", self.message]), voice=voice, loop=loop)
        print(str(response))

        self.create_call_request(self.to_phone_number, response, self.twilio_sid,
                                 self.twilio_token, self.twilio_phone_number, 0)
        self.send_notification(0, "911 Requested")

    def sms_test_pushbutton_clicked(self):
        # Use the info on the setting page to make sms test.
        phone_number = self.ui.adminPhoneNumberLineEdit.text()
        t_sid = self.ui.twilioSIDLineEdit.text()
        t_token = self.ui.twilioTokenLineEdit.text()
        t_number = self.ui.twilioPhoneNumberLineEdit.text()
        body = "".join(["Internet-based Naloxone Safety Kit. These are the words that will be heard by ", self.ui.emergencyPhoneNumberLineEdit.text(), " when the door is opened: Someone has overdosed at ",
                       self.ui.emergencyAddressLineEdit.text(), ". ", self.ui.emergencyMessageLineEdit.text(), " If the message sounds good, you can save the settings. Thank you."])
        self.create_sms_request(phone_number, body, t_sid, t_token, t_number)
        self.send_notification(4, "SMS Requested")

    def call_test_pushbutton_clicked(self):
        # Use the info on the setting page to make phone call test
        phone_number = self.ui.adminPhoneNumberLineEdit.text()
        t_sid = self.ui.twilioSIDLineEdit.text()
        t_token = self.ui.twilioTokenLineEdit.text()
        t_number = self.ui.twilioPhoneNumberLineEdit.text()
        response = VoiceResponse()
        response.say("".join(["Internet-based Naloxone Safety Kit. These are the words that will be heard by ", self.ui.emergencyPhoneNumberLineEdit.text(), " when the door is opened: Someone has overdosed at ",
                     self.ui.emergencyAddressLineEdit.text(), ". ", self.ui.emergencyMessageLineEdit.text(), " If the message sounds good, you can save the settings. Thank you."]), voice="woman", loop=3)
        self.create_call_request(phone_number, response,
                                 t_sid, t_token, t_number)
        self.send_notification(4, "Call Requested")

    def disarm_door_sensor(self):
        self.ui.disarmPushButton.setVisible(False)
        self.ui.armPushButton.setVisible(True)
        self.send_notification(1, "Door Sensor OFF")
        self.disarmed = True
        self.io_queue.put(IOItem(
            True, self.max_temp, self.fan_threshold_temp, self.naloxone_expiration_date))

    def arm_door_sensor(self):
        self.ui.armPushButton.setVisible(False)
        self.ui.disarmPushButton.setVisible(True)
        self.send_notification(4, "Door Sensor ON")
        self.disarmed = False
        self.io_queue.put(IOItem(
            False, self.max_temp, self.fan_threshold_temp, self.naloxone_expiration_date))

    def reset_to_default(self):
        # Used to check whether the door is still opened
        if (self.door_opened and not self.disarmed):
            self.send_notification(1, "Close Door First")
        else:
            self.goto_home()
            self.ui.replace_naloxone_button_2.setVisible(False)
            self.ui.homePushButton.setVisible(True)
            self.ui.dashboardPushButton.setVisible(True)
            self.ui.settingsPushButton.setVisible(True)
            self.ui.stopCountdownPushButton.setVisible(True)
            self.ui.countdownLabel.setVisible(True)
            self.ui.emergencyCallCountdownLabel.setVisible(True)
            self.ui.alarmStatusLabel.setText("Waiting")
            self.ui.alarmMutePushButton.setVisible(False)
            self.ui.doorOpenResetPushButton.setVisible(False)
            self.ui.emergencyCallStatusLabel.setText("Waiting")
            self.ui.emergencyCallLastCallLabel.setText("N/A")
            self.ui.emergencyCallCountdownLabel.setText("T-10s")
            self.destroy_countdown_worker()
            self.destroy_alarm_worker()
            self.send_notification(4, "System Reset")

    def stop_countdown_button_pushed(self):
        # Stop the countdown timer by stop it.
        self.ui.settingsPushButton.setVisible(True)
        self.ui.doorOpenResetPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        self.ui.replace_naloxone_button_2.setVisible(True)
        self.ui.emergencyCallStatusLabel.setText("N/A")
        self.ui.alarmStatusLabel.setText("Muted")
        self.ui.alarmMutePushButton.setVisible(False)
        self.ui.emergencyCallLastCallLabel.setText("N/A")
        self.destroy_countdown_worker()

    def forgot_password_button_pushed(self):
        # when the forgot password button is pushed, use the conf file to send
        # the passcode
        self.send_sms_using_config_file(
            " ".join(["Passcode is ", self.admin_passcode]))

    @pyqtSlot()
    def update_time_status(self):
        time = QDateTime()
        self.ui.time_label.setText(
            time.currentDateTime().toString("h:mm AP"))
        if (self.request_queue.qsize() != 0):
            self.ui.wait_icon.setVisible(True)
        else:
            self.ui.wait_icon.setVisible(False)
        if (self.status_queue.empty()):
            self.ui.time_label.setVisible(True)
            self.ui.status_bar.setVisible(False)
        else:
            self.ui.time_label.setVisible(False)
            msg = self.status_queue.get()
            self.message_level = msg.priority
            self.message_to_display = msg.message
            self.ui.status_bar.setText(self.message_to_display)
            if (self.message_level == 0):
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: red; border-radius:25px;border-color: red;border-width: 1px;border-style: solid;")
            elif (self.message_level == 1):
                self.ui.status_bar.setStyleSheet(
                    "color: black; background-color: yellow; border-radius:25px;border-color: yellow;border-width: 1px;border-style: solid;")
            else:
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
            self.ui.status_bar.setVisible(True)

    @pyqtSlot()
    def twilio_sid_validator(self):
        result = False
        if (self.sender().text() == str()):
            self.sender().setStyleSheet(
                "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
        elif (len(self.sender().text()) == 34 and self.sender().text().startswith("AC")):
            self.sender().setStyleSheet(
                "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: green;border-width: 1px;border-style: solid;")
        else:
            self.sender().setStyleSheet(
                "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: red;border-width: 1px;border-style: solid;")

    @pyqtSlot()
    def phone_number_validator(self):
        result = False
        if (self.sender().text() == str()):
            self.sender().setStyleSheet(
                "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
            return
        try:
            z = parse(self.sender().text(), None)
        except Exception as e:
            if (self.sender().text() == "911"):
                result = True
            else:
                result = False
        else:
            result = is_valid_number(z)
        finally:
            if (result):
                self.sender().setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: green;border-width: 1px;border-style: solid;")
            else:
                self.sender().setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: red;border-width: 1px;border-style: solid;")

    @pyqtSlot()
    def get_passcode_button_pressed(self):
        self.create_sms_request(self.ui.paramedic_phone_number_lineedit.text(), " ".join(
            ["The passcode is", self.naloxone_passcode]), self.twilio_sid, self.twilio_token, self.twilio_phone_number)
        self.send_sms_using_config_file("Passcode retrieved. The phone number is {}".format(
            self.ui.paramedic_phone_number_lineedit.text()))

    @pyqtSlot()
    def notify_admin(self):
        self.send_sms_using_config_file("Paramedics arrived!")

    @pyqtSlot()
    def test_tts_engine(self):
        self.create_alarm_worker(self.ui.alarm_message_lineedit.text(
        ), self.ui.voice_volume_slider.value(), False)

    @pyqtSlot()
    def speak_now(self):
        self.create_alarm_worker(self.alarm_message, self.voice_volume, True)
        self.ui.alarmStatusLabel.setText("Speaking")
        self.ui.alarmMutePushButton.setVisible(True)

    @pyqtSlot()
    def stop_alarm(self):
        self.destroy_alarm_worker()
        self.ui.alarmStatusLabel.setText("Muted")
        self.ui.alarmMutePushButton.setVisible(False)

    @pyqtSlot()
    def call_emergency_now(self):
        if (self.ui.stopCountdownPushButton.isVisible()):
            self.ui.stopCountdownPushButton.setVisible(False)
            self.destroy_countdown_worker()
        self.call_911_using_config_file()
        self.ui.emergencyCallStatusLabel.setText("Requested")
        self.ui.settingsPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        self.ui.doorOpenResetPushButton.setVisible(True)
        self.ui.replace_naloxone_button_2.setVisible(True)

    @pyqtSlot(int)
    def update_emergency_call_countdown(self, sec):
        # Used to update the GUI for the countdown time.
        self.ui.emergencyCallCountdownLabel.setText(
            "".join(["T-", str(sec), "s"]))
        if (not self.door_opened):
            # when the door is closed within the countdown time, auto reset it.
            self.stop_countdown_button_pushed()
            self.reset_to_default()

    @pyqtSlot(int, str)
    def update_phone_call_gui(self, priority, message):
        if (priority == 0 and message == "Call Delivered"):
            self.ui.emergencyCallStatusLabel.setText("Successful")
            self.ui.emergencyCallLastCallLabel.setText(
                QTime().currentTime().toString("h:mm AP"))
        else:
            self.ui.emergencyCallStatusLabel.setText("Failed")
            self.speak_now()

    @pyqtSlot(bool, bool)
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
            self.ui.door_sensor_icon.setVisible(False)
            self.ui.doorArmedLineEdit.setText("Armed")
        else:
            self.ui.door_sensor_icon.setVisible(True)
            self.ui.doorArmedLineEdit.setText("Disarmed")

    @pyqtSlot(bool, QDate)
    def update_naloxone_ui(self, naloxone_good, naloxone_expiration_date):
        # update the naloxone of the main window.
        self.ui.naloxoneExpirationDateLineEdit.setText(
            naloxone_expiration_date.toString("MMM dd, yy"))
        if (naloxone_good):
            self.ui.naloxone_destroyed_icon.setVisible(False)
            self.ui.naloxoneStatusLineEdit.setText("OK")
        else:
            self.ui.naloxone_destroyed_icon.setVisible(True)
            self.ui.naloxoneStatusLineEdit.setText("Destroyed")

    @pyqtSlot(bool, float, str, QTime)
    def update_server_ui(self, server, balance, currency, server_check_time):
        # update the server of the main window
        self.ui.serverCheckLineEdit.setText(
            server_check_time.toString("h:mm AP"))
        if (server):
            self.ui.no_connection_icon.setVisible(False)
            self.ui.serverStatusLineEdit.setText("ONLINE")
        else:
            self.ui.no_connection_icon.setVisible(True)
            self.ui.serverStatusLineEdit.setText("OFFLINE")
        self.ui.accountBalanceLineEdit.setText(
            " ".join([str(round(balance, 2)), currency]))
        if (balance < 5):
            self.ui.low_charge_icon.setVisible(True)
        else:
            self.ui.low_charge_icon.setVisible(False)

    @pyqtSlot(int, int, int, bool)
    def update_temperature_ui(self, temperature, cpu_temperature, pwm, over_temperature):
        # update the temperature of the main window.
        self.ui.temperatureLineEdit.setText(
            "".join([str(temperature), "℉"]))
        self.ui.cpuTemperatureLineEdit.setText(
            "".join([str(cpu_temperature), "℉"]))
        if (pwm == 0):
            self.ui.fan_icon.setVisible(False)
            self.ui.fanSpeedLineEdit.setText("OFF")
        else:
            self.ui.fan_icon.setVisible(True)
            self.ui.fanSpeedLineEdit.setText(" ".join([str(pwm), "RPM"]))

    @pyqtSlot(int)
    def update_voice_volume(self, value):
        self.ui.voice_volume_label.setText("".join([str(value), "%"]))

    @pyqtSlot(int)
    def update_current_max_temperature(self, value):
        # Used to update the current temperature selection when the user uses
        # the slider on the setting page.
        self.ui.CurrentTemperatureLabel.setText("".join([str(value), "℉"]))

    @pyqtSlot(int)
    def update_current_threshold_temperature(self, value):
        self.ui.current_fan_temperature.setText("".join([str(value), "℉"]))

    def save_config_file(self):
        # save the config file
        self.active_hour_start = self.ui.startTimeEdit.time()
        self.active_hour_end = self.ui.endTimeEdit.time()
        config = ConfigParser()
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
            "threshold_temperature": self.ui.fan_temperature_slider.value(),
            "enable_power_saving": self.ui.enablePowerSavingCheckBox.isChecked(),
            "active_hours_start_at": self.active_hour_start.toString("hh:mm"),
            "active_hours_end_at": self.active_hour_end.toString("hh:mm")
        }
        config["alarm"] = {
            "alarm_message": self.ui.alarm_message_lineedit.text(),
            "voice_volume": self.ui.voice_volume_slider.value()
        }
        with open("safety_kit.conf", "w") as configfile:
            config.write(configfile)
        if (self.ui.enableSMSCheckBox.isChecked() and self.ui.reportSettingsChangedCheckBox.isChecked()):
            self.send_sms_using_config_file("Settings Changed")
        self.send_notification(4, "Settings Saved")
        self.load_settings()

    def exit_program(self):
        self.network_timer.stop()
        self.status_bar_timer.stop()
        self.request_queue.put(RequestItem(
            0, "exit", str(), str(), str(), str(), str()))
        self.destroy_twilio_worker()
        self.destroy_network_worker()
        self.destroy_io_worker()
        self.destroy_alarm_worker()
        self.destroy_countdown_worker()
        self.close()


def gui_manager():
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    # enable highdpi scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,
                              True)  # use highdpi icons
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)

    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    if(len(sys.argv) == 1):
        print(sys.argv[0])
        RASPBERRY = True
    elif(len(sys.argv) >= 2):
        if(sys.argv[1] == 'D'):
            RASPBERRY = False
        else:
            RASPBERRY = True
    print("DEBUG MODE: " + str(not RASPBERRY))
    if(RASPBERRY):
        from gpiozero import CPUTemperature
        import RPi.GPIO as GPIO
        import Adafruit_DHT as dht

    gui_manager()
