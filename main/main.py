from PyQt5.QtWidgets import QMainWindow, QScroller, QApplication, QMessageBox, QDialog, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QDate, QTime, QDateTime, QTimer, Qt, QFile, QTextStream, QIODevice
from PyQt5.QtGui import QPixmap, QGuiApplication, QRegion
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
import sys
from queue import Queue, PriorityQueue
from configparser import ConfigParser
from ui_main_window import Ui_door_close_main_window
from time import sleep
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_M
from gtts import gTTS
from phonenumbers import parse, is_valid_number
from dataclasses import dataclass, field
from rpi_backlight import Backlight
from gpiozero import CPUTemperature
import RPi.GPIO as GPIO
import adafruit_dht
import board
import digitalio
import logging

DOOR_PIN = 17
DHT_PIN = 27
FAN_PIN = 12
RESET_PIN = 22


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
    fan_enabled: bool
    fan_threshold_temp: int
    expiration_date: QDate


@dataclass
class EventItem:
    # [0] report_door_opened
    # [1] report_emergency_called
    # [2] report_naloxone_destroyed
    # [3] report_settings_changed
    # [4] report_low_balance
    cat: int
    message: str


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


class helpDialog(QDialog):
    def __init__(self, path):
        super().__init__()

        self.text_edit = QTextEdit(self)
        self.text_edit.setStyleSheet("QTextEdit{color:white;}QScrollBar{background: rgb(50,50,50);border-radius: 5px;border-color:rgb(50,50,50);width:10}QScrollBar::handle:vertical{background-color: rgb(65,65,65);border-radius: 5px;}QScrollBar::add-line:vertical {border: none;background: none;}QScrollBar::sub-line:vertical {border: none;background: none;}QPushButton{color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;}")
        self.text_edit.setDisabled(True)
        help_file = QFile(path)
        if not help_file.open(QIODevice.ReadOnly):
            return
        stream = QTextStream(help_file)
        self.text_edit.setMarkdown(stream.readAll())
        self.text_edit.setReadOnly(True)
        QScroller.grabGesture(
            self.text_edit.viewport(), QScroller.LeftMouseButtonGesture)

        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("QPushButton{color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;width: 100px;height: 50px;}QPushButton:pressed{color: white; background-color: rgb(25,25,25); border-radius:25px;border-color: rgb(25,25,25);border-width: 1px;border-style: solid;}")

        layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)

        self.setWindowTitle("Help!")
        self.setStyleSheet("background-color:black;")
        self.showFullScreen()


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
                logging.debug("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            self.time_changed_signal.emit(self.time_in_sec)
            self.time_in_sec = self.time_in_sec - 1
            if (self.isInterruptionRequested()):
                logging.debug("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            sleep(1)

        if (self.time_in_sec == -1):
            self.time_end_signal.emit()

    def stop(self):
        logging.debug("countdown timer terminated")
        self.terminate()


class IOWorker(QThread):
    update_door = pyqtSignal(bool, bool)
    update_temperature = pyqtSignal(int, int, int, bool)
    update_naloxone = pyqtSignal(bool, QDate)
    go_to_door_open_signal = pyqtSignal()

    def __init__(self, in_queue):
        super(IOWorker, self).__init__()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        GPIO.setup(DOOR_PIN, GPIO.IN)
        GPIO.setup(RESET_PIN, GPIO.IN)
        self.dhtDevice = adafruit_dht.DHT22(board.D27)
        self.naloxone_counter = 9
        self.in_queue = in_queue
        self.worker_initialized = False
        self.fan_gpio = GPIO.PWM(FAN_PIN, 10000)
        self.fan_gpio.start(0)
        self.naloxone_temp_c = 0
        self.naloxone_temp_f = 32
        logging.info("IO init.")

    def read_naloxone_sensor(self):
        self.old_naloxone_temp_c = self.naloxone_temp_c
        try:
            self.naloxone_temp_c = self.dhtDevice.temperature
        except Exception:
            self.naloxone_temp_c = self.old_naloxone_temp_c
        else:
            if (self.naloxone_temp_c is None):
                self.naloxone_temp_c = self.old_naloxone_temp_c
        finally:
            self.naloxone_temp_f =  int(self.naloxone_temp_c * 1.8 + 32)

    def calculate_pwm(self):
        if (self.cpu_temp < self.fan_threshold_temp):
            self.fan_pwm = 0
        elif (self.cpu_temp >= 212):
            self.fan_pwm = 100
        else:
            self.fan_pwm = int((100.0 / (212 - self.fan_threshold_temp))
                               * (self.cpu_temp - self.fan_threshold_temp))

    def send_pwm(self):
        self.fan_gpio.ChangeDutyCycle(self.fan_pwm)

    def read_cpu_sensor(self):
        self.cpu_temp = int(CPUTemperature().temperature * 1.8 + 32)

    def read_door_sensor(self):
        if GPIO.input(DOOR_PIN):
            self.door_opened = True
        else:
            self.door_opened = False

    def is_expiry(self):
        today = QDate().currentDate()
        return today > self.expiration_date

    def is_overheat(self):
        return self.max_temp < self.naloxone_temp_f

    def run(self):
        while True:
            if (self.isInterruptionRequested()):
                break
            if (not self.worker_initialized or not self.in_queue.empty()):
                config = self.in_queue.get()
                self.disarmed = config.disarmed
                self.max_temp = config.max_temp
                self.fan_enabled = config.fan_enabled
                self.fan_threshold_temp = config.fan_threshold_temp
                self.expiration_date = config.expiration_date
                self.naloxone_counter = 9
                self.worker_initialized = True
            self.naloxone_counter += 1
            if (self.naloxone_counter == 10):
                self.read_naloxone_sensor()
                self.read_cpu_sensor()
                if (self.fan_enabled):
                    self.calculate_pwm()
                else:
                    self.fan_pwm = 0
                self.update_temperature.emit(
                    self.naloxone_temp_f, self.cpu_temp, self.fan_pwm, self.naloxone_temp_f > self.max_temp)
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


class MediaCreator(QThread):
    media_created = pyqtSignal()

    def __init__(self, alarm_message):
        super(MediaCreator, self).__init__()
        self.alarm_message = alarm_message

    def run(self):
        self.tts = gTTS(self.alarm_message, lang="en")
        self.tts.save("res/alarm.mp3")
        self.media_created.emit()


class AlarmWorker(QThread):
    def __init__(self, voice_volume, loop):
        super(AlarmWorker, self).__init__()
        self.voice_volume = voice_volume
        self.loop = loop
        os.system("pactl set-sink-volume 0 {}%".format(self.voice_volume))
        logging.debug("alarm thread go.")

    def run(self):
        if (self.loop):
            # loop until stopped by interruption
            while (True):
                if (self.isInterruptionRequested()):
                    break
                logging.debug("playing")
                os.system("mpg123 -q res/alarm.mp3")
                if (self.isInterruptionRequested()):
                    break
                sleep(1)
        else:
            logging.debug("saying alarm now.")
            os.system("mpg123 -q res/alarm.mp3")
            logging.debug("finish")


class NetworkWorker(QThread):
    update_server = pyqtSignal(bool, float, str, QTime)

    def __init__(self, twilio_sid, twilio_token):
        super(NetworkWorker, self).__init__()
        self.hostname = "www.twilio.com"  # ping twilio directly
        logging.debug("network thread go.")
        self.currentTime = QTime()
        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token

    def run(self):
        try:
            client = Client(self.twilio_sid, self.twilio_token)
            response = os.system(" ".join(["ping -c 1", self.hostname]))
            if (response == 1):
                logging.error("Internet failed.")
                self.update_server.emit(
                    False, 0, "USD", self.currentTime.currentTime())
            else:
                balance = client.api.v2010.balance.fetch().balance
                currency = client.api.v2010.balance.fetch().currency
                self.update_server.emit(True, float(
                    balance), currency, self.currentTime.currentTime())
                logging.info("Twilio account balance updated.")
        except Exception as e:
            self.update_server.emit(
                False, 0, "USD", self.currentTime.currentTime())
            logging.error("Failed to retrieve Twilio account balance.")


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
                    logging.error("ERROR: {}".format(str(e)))
                    self.out_queue.put(NotificationItem(
                        request.priority, "Call Failed"))
                    if (request.priority == 0):
                        self.emergency_call_status.emit(0, "Call Failed")
                else:
                    logging.debug(call.sid)
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
                    logging.error(
                        "ERROR: Twilio SMS: ERROR - {}".format(str(e)))
                    self.out_queue.put(NotificationItem(
                        request.priority, "SMS Failed"))
                else:
                    # if successful, return True
                    logging.debug(sms.sid)
                    self.out_queue.put(NotificationItem(
                        request.priority, "SMS Delivered"))


class ApplicationWindow(QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.image_index = 0
        self.initialized = False
        self.naloxone_destroyed = False
        self.low_account_balance = False
        self.door_opened = False
        self.emergency_mode = False
        self.disarmed = False
        self.sms_reporting = False
        self.report_door_opened = False
        self.report_emergency_called = False
        self.report_naloxone_destroyed = False
        self.report_settings_changed = False
        self.report_low_balance = False
        self.reporting_cat = 0
        self.reporting_message = str()
        self.reporting_item = None
        self.max_temp = 0
        self.fan_enabled = True
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
        self.alarm_message = str()
        self.voice_volume = 20
        self.status_queue = PriorityQueue()
        self.request_queue = PriorityQueue()
        self.reporting_queue = Queue()
        self.io_queue = Queue()
        self.message_to_display = str()
        self.message_level = 0
        self.help_dialog = None
        self.backlight = Backlight()
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        self.showFullScreen()
        # self.setCursor(Qt.BlankCursor)
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
        self.ui.help_pushbutton.clicked.connect(self.show_help)
        self.ui.temperatureSlider.valueChanged.connect(
            self.update_current_max_temperature)
        self.ui.fan_temperature_slider.valueChanged.connect(
            self.update_current_threshold_temperature)
        self.ui.voice_volume_slider.valueChanged.connect(
            self.update_voice_volume)
        self.ui.brightness_slider.valueChanged.connect(self.update_brightness)
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
        self.ui.generate_pushbutton.clicked.connect(self.generate_alarm_file)
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
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_1.jpg) 0 0 0 0 stretch stretch}")

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

        self.ui.brightness_slider.setValue(self.backlight.brightness)

        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.create_network_worker)

        self.twilio_worker = None
        self.network_worker = None
        self.io_worker = None
        self.alarm_worker = None
        self.countdown_worker = None
        self.media_creator = None
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

        self.reporting_timer = QTimer()
        self.reporting_timer.timeout.connect(self.reporting_handling)
        self.reporting_handling()
        self.reporting_timer.start(10000)

        self.daily_reporting_timer = QTimer()
        self.daily_reporting_timer.timeout.connect(self.daily_reporting)
        self.daily_reporting_timer.start(86400000)

        self.image_change_timer = QTimer()
        self.image_change_timer.timeout.connect(self.change_image)
        self.image_change_timer.start(10000)

        self.goto_home()
        self.lock_settings()
        self.load_settings()

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

    def destroy_media_creator(self):
        if (self.media_creator is not None):
            self.media_creator.quit()
            self.media_creator.requestInterruption()
            self.media_creator.wait()

    def create_media_creator(self, alarm_message):
        self.destroy_media_creator()
        self.media_creator = MediaCreator(alarm_message)
        self.media_creator.media_created.connect(self.alarm_file_generated)
        self.media_creator.start()

    def destroy_alarm_worker(self):
        if (self.alarm_worker is not None):
            self.alarm_worker.quit()
            self.alarm_worker.requestInterruption()
            self.alarm_worker.wait()

    def create_alarm_worker(self, voice_volume, loop):
        self.destroy_alarm_worker()
        self.alarm_worker = AlarmWorker(voice_volume, loop)
        self.alarm_worker.start()

    def destroy_countdown_worker(self):
        if (self.countdown_worker is not None):
            self.countdown_worker.quit()
            self.countdown_worker.requestInterruption()
            self.countdown_worker.wait()

    def create_countdown_worker(self, time):
        logging.debug("creating countdown worker...")
        self.destroy_countdown_worker()
        self.countdown_worker = CountDownWorker(time)
        self.countdown_worker.time_changed_signal.connect(
            self.update_emergency_call_countdown)
        self.countdown_worker.time_end_signal.connect(
            self.call_emergency_now)
        self.countdown_worker.start()

    def send_notification(self, priority, message):
        self.status_queue.put(NotificationItem(priority, message))  # blocking

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
            self.ui.brightness_slider.setValue(
                int(config["power_management"]["brightness"]))
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
            self.ui.reportLowAccountBalanceCheckBox.setChecked(
                config["admin"]["report_low_account_balance"] == "True")
            self.ui.allowParamedicsCheckBox.setChecked(
                config["admin"]["allow_paramedics"] == "True")
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
            self.naloxone_destroyed = False
            self.ui.fan_temperature_slider.setValue(
                int(config["power_management"]["threshold_temperature"]))
            self.max_temp = int(
                config["naloxone_info"]["absolute_maximum_temperature"])
            self.fan_threshold_temp = int(
                config["power_management"]["threshold_temperature"])
            self.ui.brightness_slider.setValue(
                int(config["power_management"]["brightness"]))
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
            self.sms_reporting = (
                config["admin"]["enable_sms"] == "True")
            self.ui.reportDoorOpenedCheckBox.setChecked(
                config["admin"]["report_door_opened"] == "True")
            self.report_door_opened = (
                config["admin"]["report_door_opened"] == "True")
            self.ui.reportEmergencyCalledCheckBox.setChecked(
                config["admin"]["report_emergency_called"] == "True")
            self.report_emergency_called = (
                config["admin"]["report_emergency_called"] == "True")
            self.ui.reportNaloxoneDestroyedCheckBox.setChecked(
                config["admin"]["report_naloxone_destroyed"] == "True")
            self.report_naloxone_destroyed = (
                config["admin"]["report_naloxone_destroyed"] == "True"
            )
            self.ui.reportSettingsChangedCheckBox.setChecked(
                config["admin"]["report_settings_changed"] == "True")
            self.report_settings_changed = (
                config["admin"]["report_settings_changed"] == "True"
            )
            self.ui.reportLowAccountBalanceCheckBox.setChecked(
                config["admin"]["report_low_account_balance"] == "True"
            )
            self.report_low_balance = (
                config["admin"]["report_low_account_balance"] == "True")
            self.ui.allowParamedicsCheckBox.setChecked(
                config["admin"]["allow_paramedics"] == "True")
            if (config["admin"]["allow_paramedics"] == "False"):
                self.ui.paramedic_frame.setVisible(False)
                self.ui.admin_only_frame.setVisible(True)
            else:
                self.ui.paramedic_frame.setVisible(True)
                self.ui.admin_only_frame.setVisible(False)
            self.fan_enabled = (
                config["power_management"]["enable_active_cooling"] == "True"
            )
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
                self.disarmed, self.max_temp, self.fan_enabled, self.fan_threshold_temp, self.naloxone_expiration_date))
            self.create_network_worker()  # initialize the network checker.
            self.network_timer.start(600000)

        except Exception as e:
            logging.error(e)
            self.initialized = False
            self.send_notification(0, "Config File Missing")
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
            self.ui.homePushButton.setVisible(False)
            self.ui.dashboardPushButton.setVisible(False)
            self.disarm_door_sensor()

        else:
            logging.debug("self.initialized: " + str(self.initialized))
            if (not self.emergency_mode):
                self.ui.homePushButton.setVisible(True)
                self.ui.dashboardPushButton.setVisible(True)
            if (not self.initialized):
                logging.debug("sensor armed")
                self.arm_door_sensor()
            self.initialized = True

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
            logging.debug("admin passcode detected.")
            return 1
        if (self.ui.passcodeEnterLineEdit.text() == self.naloxone_passcode):
            logging.debug("naloxone passcode detected.")
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
        logging.debug("door opened.")
        self.dashboard_timer.stop()
        if ((self.ui.stackedWidget.currentIndex() == 0 or self.ui.stackedWidget.currentIndex() == 1) and not self.disarmed):
            # Only go to the door open page when the user is not changing settings.
            if(self.help_dialog is not None):
                self.help_dialog.close()
            self.emergency_mode = True
            self.reporting_queue.put(EventItem(0, "Door Opened"))
            self.ui.doorOpenResetPushButton.setVisible(False)
            self.ui.homePushButton.setVisible(False)
            self.ui.replace_naloxone_button_2.setVisible(False)
            self.ui.dashboardPushButton.setVisible(False)
            self.ui.settingsPushButton.setVisible(False)
            self.ui.backPushButton.setVisible(False)
            self.ui.alarmMutePushButton.setVisible(False)
            self.ui.notify_admin_button_2.setVisible(False)
            self.ui.alarmFrame.setVisible(False)
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
        logging.debug(str(response))

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
            True, self.max_temp, self.fan_enabled, self.fan_threshold_temp, self.naloxone_expiration_date))
        logging.info("door sensor disarmed.")

    def arm_door_sensor(self):
        self.ui.armPushButton.setVisible(False)
        self.ui.disarmPushButton.setVisible(True)
        self.disarmed = False
        self.io_queue.put(IOItem(
            False, self.max_temp, self.fan_enabled, self.fan_threshold_temp, self.naloxone_expiration_date))
        logging.info("door sensor armed.")

    def reset_to_default(self):
        # Used to check whether the door is still opened
        if (self.door_opened and not self.disarmed):
            self.send_notification(1, "Close Door First")
        else:
            self.goto_home()
            self.emergency_mode = False
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
            self.ui.notify_admin_button_2.setVisible(False)
            self.ui.alarmFrame.setVisible(False)
            self.ui.emergencyCallStatusLabel.setText("Waiting")
            self.ui.emergencyCallLastCallLabel.setText("N/A")
            self.ui.emergencyCallCountdownLabel.setText("T-10s")
            self.destroy_countdown_worker()
            self.destroy_alarm_worker()
            self.send_notification(4, "System Reset")

    def stop_countdown_button_pushed(self):
        # Stop the countdown timer by stop it.
        self.ui.settingsPushButton.setVisible(True)
        self.ui.alarmFrame.setVisible(True)
        self.ui.doorOpenResetPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        self.ui.replace_naloxone_button_2.setVisible(True)
        self.ui.notify_admin_button_2.setVisible(True)
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
            if (not self.initialized):
                self.ui.status_bar.setVisible(True)
                self.ui.status_bar.setText("Initial Setup")
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
            elif (self.naloxone_destroyed):
                # only show when status queue is empty
                self.ui.status_bar.setVisible(True)
                self.ui.status_bar.setText("Naloxone Destroyed")
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: red; border-radius:25px;border-color: red;border-width: 1px;border-style: solid;")
            else:
                self.ui.status_bar.setVisible(False)
        else:
            msg = self.status_queue.get()
            self.message_level = msg.priority
            self.message_to_display = msg.message
            self.ui.status_bar.setText(self.message_to_display)
            if (self.message_level == 0):
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: red; border-radius:25px;border-color: red;border-width: 1px;border-style: solid;")
                logging.error(self.message_to_display)
            elif (self.message_level == 1):
                self.ui.status_bar.setStyleSheet(
                    "color: black; background-color: yellow; border-radius:25px;border-color: yellow;border-width: 1px;border-style: solid;")
                logging.warning(self.message_to_display)
            else:
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
                logging.info(self.message_to_display)
            self.ui.status_bar.setVisible(True)

    @pyqtSlot()
    def reporting_handling(self):
        if (not self.reporting_queue.empty()):
            self.reporting_event = self.reporting_queue.get()
            self.reporting_cat = self.reporting_event.cat
            self.reporting_message = self.reporting_event.message
            if (self.sms_reporting and self.report_door_opened and self.reporting_cat == 0):
                self.send_sms_using_config_file(self.reporting_message)
            elif (self.sms_reporting and self.report_emergency_called and self.reporting_cat == 1):
                self.send_sms_using_config_file(self.reporting_message)
            elif (self.sms_reporting and self.report_naloxone_destroyed and self.reporting_cat == 2):
                self.send_sms_using_config_file(self.reporting_message)
            elif (self.sms_reporting and self.report_settings_changed and self.reporting_cat == 3):
                self.send_sms_using_config_file(self.reporting_message)
            elif (self.sms_reporting and self.report_low_balance and self.reporting_cat == 4):
                self.send_sms_using_config_file(self.reporting_message)
            logging.info(self.reporting_message)

    @pyqtSlot()
    def daily_reporting(self):
        if (self.naloxone_destroyed):
            self.reporting_queue.put(EventItem(2, "Naloxone Destroyed"))
        if (self.low_account_balance):
            self.reporting_queue.put(
                EventItem(4, "Low Twilio Account Balance"))

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
        self.create_alarm_worker(self.ui.voice_volume_slider.value(), False)

    @pyqtSlot()
    def generate_alarm_file(self):
        self.create_media_creator(self.ui.alarm_message_lineedit.text())
        self.ui.generate_pushbutton.setEnabled(False)

    @pyqtSlot()
    def alarm_file_generated(self):
        self.ui.generate_pushbutton.setEnabled(True)
        self.send_notification(4, "Alarm Generated")

    @pyqtSlot()
    def speak_now(self):
        self.create_alarm_worker(self.voice_volume, True)
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
        self.ui.alarmFrame.setVisible(True)
        self.ui.doorOpenResetPushButton.setVisible(True)
        self.ui.replace_naloxone_button_2.setVisible(True)
        self.ui.notify_admin_button_2.setVisible(True)

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
            self.reporting_queue.put(
                EventItem(1, "Emergency Call Placed Successfully"))
            self.stop_alarm()
        else:
            self.ui.emergencyCallStatusLabel.setText("Failed")
            self.reporting_queue.put(EventItem(1, "Emergency Call Failed"))
            self.speak_now()

    @pyqtSlot(bool, bool)
    def update_door_ui(self, door, armed):
        # Update the door ui of the main window.
        logging.debug("{} {}".format(str(door), str(armed)))
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
        if (naloxone_good and not self.naloxone_destroyed):
            self.naloxone_destroyed = False
            self.ui.naloxone_destroyed_icon.setVisible(False)
            self.ui.naloxoneStatusLineEdit.setText("OK")
        else:
            self.naloxone_destroyed = True
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
            self.low_account_balance = True
            self.ui.low_charge_icon.setVisible(True)
        else:
            self.low_account_balance = False
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
            self.ui.fanSpeedLineEdit.setText(
                " ".join([str(int(pwm / 100.0 * 7000)), "RPM"]))

    @pyqtSlot(int)
    def update_brightness(self, value):
        self.ui.brightness_label.setText("".join([str(value), "%"]))
        self.backlight.brightness = value

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
            "report_low_account_balance": self.ui.reportLowAccountBalanceCheckBox.isChecked(),
            "allow_paramedics": self.ui.allowParamedicsCheckBox.isChecked()
        }
        config["power_management"] = {
            "enable_active_cooling": self.ui.enableActiveCoolingCheckBox.isChecked(),
            "threshold_temperature": self.ui.fan_temperature_slider.value(),
            "brightness": self.ui.brightness_slider.value()
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

    def show_help(self):
        if (self.ui.stackedWidget.currentIndex() == 0):
            logging.debug("home page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/HomePage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 1):
            logging.debug("dashboard page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/DashboardPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 0):
            logging.debug("security page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/SecurityPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 1):
            logging.debug("naloxone page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/NaloxonePage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 2):
            logging.debug("twilio page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/TwilioPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 3):
            logging.debug("emergency page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/EmergencyPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 4):
            logging.debug("alarm page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/AlarmPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 5):
            logging.debug("power page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/PowerPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 6):
            logging.debug("admin page")
            self.help_dialog = helpDialog("../user_manual/gui_manual/AdminPage.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 3):
            logging.debug("lock screen page")
            self.help_dialog = helpDialog(
                "../user_manual/gui_manual/lock_screen_manual.md")
            self.help_dialog.exec_()
        elif (self.ui.stackedWidget.currentIndex() == 4):
            logging.debug("door open page")
            self.help_dialog = helpDialog(
                "../user_manual/gui_manual/DoorOpenPage.md")
            self.help_dialog.exec_()

    def change_image(self):
        if(self.image_index == 1):
            self.ui.home_frame.setStyleSheet(
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_1.jpg) 0 0 0 0 stretch stretch}")
            self.image_index = 2
        elif (self.image_index == 2):
            self.ui.home_frame.setStyleSheet(
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_2.jpg) 0 0 0 0 stretch stretch}")
            self.image_index = 3
        else:
            self.ui.home_frame.setStyleSheet(
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_3.jpg) 0 0 0 0 stretch stretch}")
            self.image_index = 1

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
        logging.info("exit program.")
        logging.shutdown()
        self.close()


def gui_manager():
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    # enable highdpi scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)

    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    logging.disable(logging.CRITICAL) # turn off all loggings
    #logging.basicConfig(format='%(levelname)s:%(message)s',
    #                    level=logging.DEBUG)
    gui_manager()
