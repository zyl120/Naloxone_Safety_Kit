import os
import sys
import subprocess
from configparser import ConfigParser
from queue import Queue, PriorityQueue
from time import sleep
import logging

from PyQt5.QtWidgets import QMainWindow, QScroller, QApplication, QMessageBox, QDialog, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QDate, QTime, QDateTime, QTimer, Qt, QFile, QTextStream, QIODevice
from PyQt5.QtGui import QPixmap, QGuiApplication, QRegion
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_M
from gtts import gTTS
from phonenumbers import parse, is_valid_number
from dataclasses import dataclass, field

from ui_main_window import Ui_door_close_main_window

if __debug__:
    from rpi_backlight import Backlight
    from gpiozero import CPUTemperature
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    import digitalio


# Define the gpio pins for the raspberry pi.
DOOR_PIN = 17
DHT_PIN = 6
FAN_PIN = 18
RESET_PIN = 22


@dataclass(order=True)
class RequestItem:
    """
    Used for twilio queue to send requests
    """
    priority: int
    request_type: str = field(compare=False)
    destination_number: str = field(compare=False)
    message: str = field(compare=False)
    twilio_sid: str = field(compare=False)
    twilio_token: str = field(compare=False)
    twilio_number: str = field(compare=False)


@dataclass(order=True)
class NotificationItem:
    """
    Used for notification queue to show notifications on taskbar
    """
    priority: int
    message: str = field(compare=False)


@dataclass
class IOItem:
    """
    Used for io queue to change settings on runtime
    """
    disarmed: bool
    max_temp: int
    fan_enabled: bool
    fan_threshold_temp: int
    expiration_date: QDate


@dataclass
class EventItem:
    """
    Used for sending sms message to admin
    [0] report_door_opened
    [1] report_emergency_called
    [2] report_naloxone_destroyed
    [3] report_settings_changed
    [4] report_low_balance
    """
    cat: int
    message: str


@dataclass
class RuntimeState:
    """
    Used to record all settings and states in the memory for access
    """
    image_index: int = 1
    initialized: bool = False
    naloxone_destroyed: bool = False
    low_account_balance: bool = False
    door_opened: bool = False
    emergency_mode: bool = False
    reporting_cat: int = 0
    reporting_message: str = str()
    message_to_display: str = str()
    message_level: int = 0
    help_dialog: QDialog = None


@dataclass
class ActiveSettings:
    """
    Used as a copy of settings in ram
    """
    disarmed: bool = False
    sms_reporting: bool = False
    report_door_opened: bool = False
    report_emergency_called: bool = False
    report_naloxone_destroyed: bool = False
    report_settings_changed: bool = False
    report_low_balance: bool = False
    max_temp: int = 0
    fan_enabled: bool = True
    fan_threshold_temp: int = 0
    admin_passcode: str = str()
    naloxone_passcode: str = str()
    twilio_sid: str = str()
    twilio_token: str = str()
    twilio_phone_number: str = str()
    admin_phone_number: str = str()
    address: str = str()
    to_phone_number: str = str()
    message: str = str()
    naloxone_expiration_date: QDate = QDate().currentDate()
    voice_volume: int = 20
    use_default_alarm: bool = True


class helpDialog(QDialog):
    """
    Used as the full screen window when the user tapping the help button
    """

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
        if __debug__:
            self.showFullScreen()


class CountDownWorker(QThread):
    """
    Used to do countdown when the user open the door
    """
    # Used to record the countdown time before calling the emergency
    # signal to indicate end of countdown time.
    time_end_signal = pyqtSignal()
    # signal to indicate the change of countdown time. Also send the current
    # countdown as well.
    time_changed_signal = pyqtSignal(int)

    def __init__(self, time_in_sec):
        """
        initializing the thread.

        :param time_in_sec: the time length for the countdown.
        """
        super(CountDownWorker, self).__init__()
        self.countdown_time_in_sec = time_in_sec
        self.time_in_sec = time_in_sec

    def run(self):
        while (self.time_in_sec >= 0):
            # Checks whether the thread is asked to be interrupted.
            if (self.isInterruptionRequested()):
                logging.debug("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            self.time_changed_signal.emit(self.time_in_sec)
            self.time_in_sec = self.time_in_sec - 1  # decrement the time
            if (self.isInterruptionRequested()):
                logging.debug("countdown timer terminated")
                self.time_changed_signal.emit(self.countdown_time_in_sec)
                break
            sleep(1)

        # when countdown expired, send another signal
        if (self.time_in_sec == -1):
            self.time_end_signal.emit()

    def stop(self):
        logging.debug("countdown timer terminated")
        self.terminate()


class IOWorker(QThread):
    """
    The thread used to monitor the readings of all sensors
    """
    update_door = pyqtSignal(bool, bool)  # update door signal
    update_temperature = pyqtSignal(
        int, int, int, bool)  # update temperature signal
    update_naloxone = pyqtSignal(bool, QDate)  # update naloxone signal
    go_to_door_open_signal = pyqtSignal()  # send to change to door open window

    def __init__(self, in_queue):
        """
        initialization for the io thread

        :param in_queue: the io queue used to change the io settings on runtime.
        """
        super(IOWorker, self).__init__()
        # Change the GPIO settings
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        GPIO.setup(DOOR_PIN, GPIO.IN)
        GPIO.setup(RESET_PIN, GPIO.IN)
        self.dhtDevice = adafruit_dht.DHT22(board.D6)
        self.naloxone_counter = 9
        self.in_queue = in_queue
        self.worker_initialized = False
        self.fan_gpio = GPIO.PWM(FAN_PIN, 10000)
        self.fan_gpio.start(0)
        self.naloxone_temp_c = 0
        self.naloxone_temp_f = 32
        logging.info("IO init.")

    def read_naloxone_sensor(self):
        """
        Read the temperature sensor to determine the naloxone temperature.
        """
        self.old_naloxone_temp_c = self.naloxone_temp_c
        try:
            self.naloxone_temp_c = self.dhtDevice.temperature
        except Exception as e:
            logging.error(e)
            self.naloxone_temp_c = self.old_naloxone_temp_c
        else:
            if (self.naloxone_temp_c is None):
                self.naloxone_temp_c = self.old_naloxone_temp_c
        finally:
            self.naloxone_temp_f = int(self.naloxone_temp_c * 1.8 + 32)
            # change the naloxone temperature from degrees C to degrees F.

    def calculate_pwm(self):
        """
        Adjust the fan speed by using PWM.
        """
        if (self.cpu_temp < self.fan_threshold_temp):
            # the minimum temperature to turn on the fan is determined by the
            # fan_threshold_temp.
            self.fan_pwm = 0
        elif (self.cpu_temp >= 212):
            # hardcoded max temperature for cpu is 212 degrees F.
            self.fan_pwm = 100
        else:
            self.fan_pwm = int((100.0 / (212 - self.fan_threshold_temp))
                               * (self.cpu_temp - self.fan_threshold_temp))

    def send_pwm(self):
        """
        Send the PWM to the fan pin to change the fan speed.
        """
        self.fan_gpio.ChangeDutyCycle(self.fan_pwm)

    def read_cpu_sensor(self):
        """
        Read the cpu temperature sensor.
        """
        self.cpu_temp = int(CPUTemperature().temperature * 1.8 + 32)

    def read_door_sensor(self):
        """
        Read the door sensor.
        """
        if GPIO.input(DOOR_PIN):
            self.door_opened = True
        else:
            self.door_opened = False

    def is_expiry(self):
        """
        Determine whether the naloxone has expired.
        """
        # Used QDate from Qt because it is simpler.
        today = QDate().currentDate()
        return today > self.expiration_date

    def is_overheat(self):
        """
        Determine whether the naloxone temperature is higher than the max_temp.
        """
        return self.max_temp < self.naloxone_temp_f

    def run(self):
        """
        Read the sensors by order.
        """
        while True:
            if (self.isInterruptionRequested()):
                # If the thread is asked to be interrupted, break the infinite loop
                break
            if (not self.worker_initialized or not self.in_queue.empty()):
                # Used to get the settings from the io queue.
                config = self.in_queue.get()  # blocking
                self.disarmed = config.disarmed
                self.max_temp = config.max_temp
                self.fan_enabled = config.fan_enabled
                self.fan_threshold_temp = config.fan_threshold_temp
                self.expiration_date = config.expiration_date
                self.naloxone_counter = 9
                self.worker_initialized = True
            self.naloxone_counter += 1
            if (self.naloxone_counter == 10):
                # Only read the naloxone temperature sensor every 10 seconds
                # Read too frequently will return wrong readings.
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
                self.dhtDevice.exit()
                GPIO.cleanup()
                break
            sleep(1)


class MediaCreator(QThread):
    """
    Used to create the alarm mp3 file.
    """
    media_created = pyqtSignal()  # signal to emit when the media is created.

    def __init__(self, alarm_message):
        """
        media creator thread initialization

        :param alarm_message: the alarm message in text.
        """
        super(MediaCreator, self).__init__()
        self.alarm_message = alarm_message  # the alarm message in text.

    def run(self):
        # Use google TTS engine to convert the text to speech
        self.tts = gTTS(self.alarm_message, lang="en")
        self.tts.save("res/alarm.mp3")  # save to mp3 file.
        self.media_created.emit()


class AlarmWorker(QThread):
    """
    Used to play the alarm for one time or continuously.
    """

    def __init__(self, voice_volume, loop, use_default_alarm):
        """
        Alarm worker initialization

        :param voice_volume: the loudness of the alarm.
        :param loop: whether to loop the alarm forever.
        """
        super(AlarmWorker, self).__init__()
        self.voice_volume = voice_volume
        self.loop = loop
        self.use_default_alarm = use_default_alarm
        self.audio_process = None
        # Set the volume by using pactl.
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
                            "{}%".format(self.voice_volume)])
        except Exception as e:
            logging.error(e)
        logging.debug("alarm thread go.")

    def run(self):
        if (self.use_default_alarm):
            logging.debug("use_default_alarm is True")
        else:
            logging.debug("use_default_alarm is False")

        if (self.loop):
            # loop until stopped by interruption
            while (not self.isInterruptionRequested()):
                logging.debug("playing")
                if (self.use_default_alarm):
                    self.audio_process = subprocess.Popen(
                        ["mpg123", "-q", "res/default.mp3"])
                else:
                    self.audio_process = subprocess.Popen(
                        ["mpg123", "-q", "res/alarm.mp3"])

                while (self.audio_process.poll() is None):
                    if (self.isInterruptionRequested()):
                        self.audio_process.terminate()
                        self.audio_process.wait()
                        break
        else:
            logging.debug("saying alarm now.")
            if (self.use_default_alarm):
                self.audio_process = subprocess.Popen(
                    ["mpg123", "-q", "res/default.mp3"])
            else:
                self.audio_process = subprocess.Popen(
                    ["mpg123", "-q", "res/alarm.mp3"])
            while (self.audio_process.poll() is None):
                if (self.isInterruptionRequested()):
                    self.audio_process.terminate()
                    self.audio_process.wait()
                    break
            logging.debug("finish")


class NetworkWorker(QThread):
    """
    The thread to check the network connection
    Send the network checking result and remaining account balance to to the GUI thread.
    """
    update_server = pyqtSignal(bool, float, str, QTime)

    def __init__(self, twilio_sid, twilio_token):
        """
        network worker thread initialization

        :param twilio_sid: The twilio sid provided by Twilio.
        :param twilio_token: The twilio account token provided by Twilio.
        These two parameters are used to check the account remaining balance.
        """
        super(NetworkWorker, self).__init__()
        self.hostname = "www.twilio.com"  # ping twilio directly
        logging.debug("network thread go.")
        self.currentTime = QTime()
        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token

    def run(self):
        try:
            # Check the network connection using system ping.
            client = Client(self.twilio_sid, self.twilio_token)
            ping_command = ["ping", "-c", "1", self.hostname]
            process = subprocess.Popen(
                ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            response = process.returncode
            if (response == 1):
                logging.error("Internet failed.")
                self.update_server.emit(
                    False, 0, "USD", self.currentTime.currentTime())
            else:
                # If the server is connected, get the Twilio account balance.
                logging.info("Attempt to get Twilio balance.")
                balance = client.api.v2010.account.balance.fetch().balance
                currency = client.api.v2010.account.balance.fetch().currency
                logging.info("balance="+balance+".")
                self.update_server.emit(True, float(
                    balance), currency, self.currentTime.currentTime())
                logging.info("Twilio account balance updated.")
        except Exception as e:
            self.update_server.emit(
                False, 0, "USD", self.currentTime.currentTime())
            logging.error("Failed to retrieve Twilio account balance.")
            logging.error(e)


class TwilioWorker(QThread):
    """
    The Twilio thread is used to handle Twilio phone calling and SMS
    """
    twilio_thread_status = pyqtSignal(int, str)
    emergency_call_status = pyqtSignal(int, str)

    def __init__(self, in_queue, out_queue):
        """
        Twilio worker initialization

        :param in_queue: the Twilio request queue.
        :param out_queue: the notification queue.
        """
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
                # Handle the Twilio calling request.
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
                # Handle the Twilio SMS request.
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
        self.runtime_state = RuntimeState()
        self.active_settings = ActiveSettings()

        self.status_queue = PriorityQueue()
        self.request_queue = PriorityQueue()
        self.reporting_queue = Queue()
        self.io_queue = Queue()
        if __debug__:
            self.backlight = Backlight()
        self.ui = Ui_door_close_main_window()  # From ui file
        self.ui.setupUi(self)
        if __debug__:
            self.showFullScreen()
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
        self.ui.stop_test_alarm_pushbutton.clicked.connect(
            self.destroy_alarm_worker)
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
            "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_1.png) 0 0 0 0 stretch stretch}")
        self.ui.home_text.setText("Safe medication use is key.")

        # Used to change the view using the scrollbar for all windows
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

        if __debug__:
            self.ui.brightness_slider.setValue(self.backlight.brightness)

        # Start timer and thread to handle the GUI update
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.create_network_worker)

        self.twilio_worker = None
        self.network_worker = None
        self.io_worker = None
        self.alarm_worker = None
        self.countdown_worker = None
        self.media_creator = None
        if __debug__:
            self.create_io_worker()
        self.create_twilio_worker()
        self.twilio_worker.emergency_call_status.connect(
            self.update_phone_call_gui)

        # Create network worker timer.
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.create_network_worker)

        # Create status bar timer. Used to change displays on the taskbar.
        self.status_bar_timer = QTimer()
        self.status_bar_timer.timeout.connect(self.update_time_status)
        self.update_time_status()
        self.status_bar_timer.start(2000)

        # Create status bar timer. Used to change the GUI to the home screen when staying on the dashboard for 1 minute.
        self.dashboard_timer = QTimer()
        self.dashboard_timer.timeout.connect(self.goto_home)
        self.dashboard_timer.setSingleShot(True)

        # Create SMS reporting timer. This task will report to the admin phone number every 10 seconds.
        self.reporting_timer = QTimer()
        self.reporting_timer.timeout.connect(self.reporting_handling)
        self.reporting_handling()
        self.reporting_timer.start(10000)

        # Create daily SMS reporting timer. This task will report to the admin phone number every day.
        self.daily_reporting_timer = QTimer()
        self.daily_reporting_timer.timeout.connect(self.daily_reporting)
        self.daily_reporting_timer.start(86400000)

        # Create image changing timer. This task will change the image on the home screen every 10 seconds.
        self.image_change_timer = QTimer()
        self.image_change_timer.timeout.connect(self.change_image)
        self.image_change_timer.start(10000)

        self.goto_home()
        self.lock_settings()
        self.load_settings()

    def destroy_twilio_worker(self):
        """
        Used to destroy the Twilio worker. This should be called when the application exits.
        """
        if (self.twilio_worker is not None):
            self.twilio_worker.quit()
            self.twilio_worker.requestInterruption()
            self.twilio_worker.wait()

    def create_twilio_worker(self):
        """
        Create Twilio worker thread.
        """
        self.destroy_twilio_worker()
        self.twilio_worker = TwilioWorker(
            self.request_queue, self.status_queue)
        self.twilio_worker.start(QThread.HighPriority)
        # self.twilio_worker.setPriority()

    def destroy_io_worker(self):
        """
        Used to destroy the IO worker thread. This should be called when the application exits.
        """
        if (self.io_worker is not None):
            self.io_worker.quit()
            self.io_worker.requestInterruption()
            self.io_worker.wait()

    def create_io_worker(self):
        """
        Used to create the IO worker thread. This should only be called when the settings are valid.
        """
        self.destroy_io_worker()
        self.io_worker = IOWorker(self.io_queue)
        # Connect the signal to the slot so that when the signal is emit, the slot function is called to run.
        self.io_worker.update_door.connect(self.update_door_ui)
        self.io_worker.go_to_door_open_signal.connect(self.goto_door_open)
        self.io_worker.update_temperature.connect(
            self.update_temperature_ui)
        self.io_worker.update_naloxone.connect(self.update_naloxone_ui)
        # will be blocked when no config is sent
        self.io_worker.start(QThread.HighPriority)

    def destroy_network_worker(self):
        if (self.network_worker is not None):
            self.network_worker.quit()
            self.network_worker.requestInterruption()
            self.network_worker.wait()

    def create_network_worker(self):
        self.destroy_network_worker()
        self.network_worker = NetworkWorker(
            self.active_settings.twilio_sid, self.active_settings.twilio_token)
        self.network_worker.update_server.connect(
            self.update_server_ui)
        self.network_worker.start(QThread.LowestPriority)

    def destroy_media_creator(self):
        if (self.media_creator is not None):
            self.media_creator.quit()
            self.media_creator.requestInterruption()
            self.media_creator.wait()

    def create_media_creator(self, alarm_message):
        self.destroy_media_creator()
        self.media_creator = MediaCreator(alarm_message)
        self.media_creator.media_created.connect(self.alarm_file_generated)
        self.media_creator.start(QThread.NormalPriority)

    def destroy_alarm_worker(self):
        if (self.alarm_worker is not None):
            self.alarm_worker.quit()
            self.alarm_worker.requestInterruption()
            self.alarm_worker.wait()

    def create_alarm_worker(self, voice_volume, loop, use_default_alarm):
        self.destroy_alarm_worker()
        self.alarm_worker = AlarmWorker(voice_volume, loop, use_default_alarm)
        self.alarm_worker.start(QThread.HighPriority)

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
        self.countdown_worker.time_end_signal.connect(self.speak_now)
        self.countdown_worker.start()
        self.countdown_worker.setPriority(QThread.HighPriority)

    def create_call_request(self, number, body, t_sid, t_token, t_number, priority=4):
        """
        Used to create call request in the Twilio request queue using the given parameters.

        :param number: The destination phone number
        :param body: The body of the calling
        :param t_sid: The twilio sid provided by Twilio.
        :param t_token: The twilio account token
        :param t_number: The twilio phone number
        :param priority: The request priority, default is 4. Highest priority is 0.
        """
        request = RequestItem(priority, "call", number, body,
                              t_sid, t_token, t_number)
        self.request_queue.put(request)  # blocking

    def create_sms_request(self, number, body, t_sid, t_token, t_number, priority=4):
        """
        Used to create sms request in the Twilio request queue using the given parameters.

        :param number: The destination phone number
        :param body: The body of the sms
        :param t_sid: The twilio sid provided by Twilio.
        :param t_token: The twilio account token
        :param t_number: The twilio phone number
        :param priority: The request priority, default is 4. Highest priority is 0.
        """
        request = RequestItem(priority, "SMS", number,
                              body, t_sid, t_token, t_number)
        self.request_queue.put(request)  # blocking

    def send_notification(self, priority, message):
        self.status_queue.put(NotificationItem(priority, message))  # blocking

    def load_settings_ui(self):
        """
        Only changes the displayed settings on the GUI.
        This function will not change the settings stored in memory.
        """
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
                self.active_settings.naloxone_expiration_date)
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
            self.ui.instr_radio_button.setChecked(
                config["alarm"]["use_default_alarm"] == "True")
            self.ui.custom_radio_button.setChecked(
                config["alarm"]["use_default_alarm"] == "False")
            self.ui.alarm_message_lineedit.setText(
                config["alarm"]["alarm_message"])
            self.ui.voice_volume_slider.setValue(
                int(config["alarm"]["voice_volume"]))
        except Exception as e:
            logging.error(e)
            return
        else:
            return

    def load_settings(self):
        """
        Load the settings from the conf file.
        """
        try:
            config = ConfigParser()
            config.read("safety_kit.conf")
            self.ui.twilioSIDLineEdit.setText(config["twilio"]["twilio_sid"])
            self.active_settings.twilio_sid = config["twilio"]["twilio_sid"]
            self.ui.twilioTokenLineEdit.setText(
                config["twilio"]["twilio_token"])
            self.active_settings.twilio_token = config["twilio"]["twilio_token"]
            self.ui.twilioPhoneNumberLineEdit.setText(
                config["twilio"]["twilio_phone_number"])
            self.active_settings.twilio_phone_number = config["twilio"]["twilio_phone_number"]
            self.ui.emergencyPhoneNumberLineEdit.setText(
                config["emergency_info"]["emergency_phone_number"])
            self.active_settings.to_phone_number = config["emergency_info"]["emergency_phone_number"]
            self.ui.emergencyAddressLineEdit.setText(
                config["emergency_info"]["emergency_address"])
            self.active_settings.address = config["emergency_info"]["emergency_address"]
            self.ui.emergencyMessageLineEdit.setText(
                config["emergency_info"]["emergency_message"])
            self.active_settings.message = config["emergency_info"]["emergency_message"]
            self.active_settings.naloxone_expiration_date = QDate.fromString(
                config["naloxone_info"]["naloxone_expiration_date"])
            self.ui.naloxoneExpirationDateEdit.setSelectedDate(
                self.active_settings.naloxone_expiration_date)
            self.ui.temperatureSlider.setValue(
                int(config["naloxone_info"]["absolute_maximum_temperature"]))
            self.runtime_state.naloxone_destroyed = False
            self.ui.fan_temperature_slider.setValue(
                int(config["power_management"]["threshold_temperature"]))
            self.active_settings.max_temp = int(
                config["naloxone_info"]["absolute_maximum_temperature"])
            self.active_settings.fan_threshold_temp = int(
                config["power_management"]["threshold_temperature"])
            self.ui.brightness_slider.setValue(
                int(config["power_management"]["brightness"]))
            self.ui.passcodeLineEdit.setText(config["admin"]["passcode"])
            self.active_settings.admin_passcode = config["admin"]["passcode"]
            self.ui.naloxonePasscodeLineEdit.setText(
                config["admin"]["naloxone_passcode"])
            self.active_settings.naloxone_passcode = config["admin"]["naloxone_passcode"]
            self.ui.adminPhoneNumberLineEdit.setText(
                config["admin"]["admin_phone_number"])
            self.active_settings.admin_phone_number = config["admin"]["admin_phone_number"]
            self.ui.enableSMSCheckBox.setChecked(
                config["admin"]["enable_sms"] == "True")
            self.active_settings.sms_reporting = (
                config["admin"]["enable_sms"] == "True")
            self.ui.reportDoorOpenedCheckBox.setChecked(
                config["admin"]["report_door_opened"] == "True")
            self.active_settings.report_door_opened = (
                config["admin"]["report_door_opened"] == "True")
            self.ui.reportEmergencyCalledCheckBox.setChecked(
                config["admin"]["report_emergency_called"] == "True")
            self.active_settings.report_emergency_called = (
                config["admin"]["report_emergency_called"] == "True")
            self.ui.reportNaloxoneDestroyedCheckBox.setChecked(
                config["admin"]["report_naloxone_destroyed"] == "True")
            self.active_settings.report_naloxone_destroyed = (
                config["admin"]["report_naloxone_destroyed"] == "True"
            )
            self.ui.reportSettingsChangedCheckBox.setChecked(
                config["admin"]["report_settings_changed"] == "True")
            self.active_settings.report_settings_changed = (
                config["admin"]["report_settings_changed"] == "True"
            )
            self.ui.reportLowAccountBalanceCheckBox.setChecked(
                config["admin"]["report_low_account_balance"] == "True"
            )
            self.active_settings.report_low_balance = (
                config["admin"]["report_low_account_balance"] == "True")
            self.ui.allowParamedicsCheckBox.setChecked(
                config["admin"]["allow_paramedics"] == "True")
            if (config["admin"]["allow_paramedics"] == "False"):
                self.ui.paramedic_frame.setVisible(False)
                self.ui.admin_only_frame.setVisible(True)
            else:
                self.ui.paramedic_frame.setVisible(True)
                self.ui.admin_only_frame.setVisible(False)
            self.active_settings.fan_enabled = (
                config["power_management"]["enable_active_cooling"] == "True"
            )
            self.ui.enableActiveCoolingCheckBox.setChecked(
                config["power_management"]["enable_active_cooling"] == "True")
            self.ui.instr_radio_button.setChecked(
                config["alarm"]["use_default_alarm"] == "True")
            self.ui.custom_radio_button.setChecked(
                config["alarm"]["use_default_alarm"] == "False")
            self.active_settings.use_default_alarm = (
                config["alarm"]["use_default_alarm"] == "True")
            self.ui.alarm_message_lineedit.setText(
                config["alarm"]["alarm_message"])
            self.ui.voice_volume_slider.setValue(
                int(config["alarm"]["voice_volume"]))
            self.active_settings.voice_volume = int(
                config["alarm"]["voice_volume"])

            # Generate the admin qr code to be displayed on the main page and the settings page.
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
            self.ui.admin_qrcode_2.setPixmap(admin_qrcode_pixmap)

            # Change the io settings by giving a new request.
            self.io_queue.put(IOItem(
                self.active_settings.disarmed, self.active_settings.max_temp, self.active_settings.fan_enabled, self.active_settings.fan_threshold_temp, self.active_settings.naloxone_expiration_date))
            self.create_network_worker()  # initialize the network checker.
            self.network_timer.start(600000)

        except Exception as e:
            logging.error(e)
            self.runtime_state.initialized = False
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
            if (not self.runtime_state.emergency_mode):
                self.ui.homePushButton.setVisible(True)
                self.ui.dashboardPushButton.setVisible(True)
            if (not self.runtime_state.initialized):
                logging.debug("sensor armed")
                self.arm_door_sensor()
            self.runtime_state.initialized = True
            logging.debug("self.initialized: " +
                          str(self.runtime_state.initialized))

    def lock_settings(self):
        """
        lock the whole setting page.
        """
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
        logging.debug("Settings Locked.")

    def unlock_naloxone_settings(self):
        """
        Only unlock the naloxone settings.
        """
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
        """
        Unlock the whole setting page. Should only be called after the user enter the correct passcode.
        """
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
        """
        First read from the conf file

        :return:
        0: wrong passcode
        1: unlock all settings
        2: unlock naloxone settings
        """
        if (self.active_settings.admin_passcode == str() or self.ui.passcodeEnterLineEdit.text() == self.active_settings.admin_passcode):
            logging.debug("admin passcode detected.")
            return 1
        if (self.ui.passcodeEnterLineEdit.text() == self.active_settings.naloxone_passcode):
            logging.debug("naloxone passcode detected.")
            return 2
        else:
            self.send_notification(0, "Wrong Passcode")
            self.ui.passcodeEnterLabel.setText("Sorry, try again")
            self.ui.passcodeEnterLineEdit.clear()
            return 0

    def check_passcode_unlock_settings(self):
        """
        Determine the correct behavior using the return values from the check_passcode function.
        """
        passcode_check_result = self.check_passcode()
        if (passcode_check_result == 1):
            # If admin passcode is correct, unlock the settings
            self.goto_settings()
            self.unlock_all_settings()

        elif (passcode_check_result == 2):
            self.goto_settings()
            self.unlock_naloxone_settings()

        else:
            # If passcode is wrong, lock the settings
            self.lock_settings()

    def lock_unlock_settings(self):
        """
        Determine whether to go to the passcode page depending on whether the passcode has been set.
        """
        if (self.active_settings.admin_passcode == str()):
            self.unlock_all_settings()
        else:
            self.goto_passcode()

    @pyqtSlot()
    def goto_door_open(self):
        """
        Go to the door open page.
        """
        logging.debug("door opened.")
        self.dashboard_timer.stop()
        if ((self.ui.stackedWidget.currentIndex() == 0 or self.ui.stackedWidget.currentIndex() == 1) and not self.active_settings.disarmed):
            # Only go to the door open page when the user is not changing settings.
            if (self.runtime_state.help_dialog is not None):
                self.runtime_state.help_dialog.close()
            self.runtime_state.emergency_mode = True
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
        """
        Goes back to the door open page when the device is in emergency mode and the user is in the settings page.
        """
        self.ui.settingsPushButton.setChecked(False)
        self.ui.settingsPushButton.setEnabled(True)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(4)

    def goto_passcode(self):
        """
        Change the GUI to the passcode page when the user presses the unlock settings button.
        """
        self.ui.passcodeEnterLineEdit.clear()
        self.ui.paramedic_phone_number_lineedit.clear()
        self.ui.passcodeEnterLabel.setText("Enter Passcode")
        self.ui.stackedWidget.setCurrentIndex(3)

    def goto_settings(self):
        """
        Change the GUI to the settings page when the user presses the icon.
        """
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
        if (self.active_settings.admin_passcode == str()):
            self.unlock_all_settings()

    def goto_dashboard(self):
        """
        Change the GUI to the dashboard page when the user presses the icon.
        """
        self.ui.homePushButton.setChecked(False)
        self.ui.dashboardPushButton.setChecked(True)
        self.ui.settingsPushButton.setChecked(False)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(1)
        # wait for 1 min before going back to home
        self.dashboard_timer.start(60000)

    def goto_home(self):
        """
        Change the GUI to the home page when the user presses the icon.
        """
        self.dashboard_timer.stop()
        self.ui.homePushButton.setChecked(True)
        self.ui.dashboardPushButton.setChecked(False)
        self.ui.settingsPushButton.setChecked(False)
        self.ui.backPushButton.setVisible(False)
        self.lock_settings()
        self.ui.stackedWidget.setCurrentIndex(0)

    def send_sms_using_config_file(self, msg):
        """
        Used to contact the admin via the info in the conf file
        """
        self.create_sms_request(self.active_settings.admin_phone_number, " ".join(
            ["The naloxone safety box at", self.active_settings.address, "sent the following information:", msg]), self.active_settings.twilio_sid, self.active_settings.twilio_token, self.active_settings.twilio_phone_number)
        self.send_notification(4, "SMS Requested")

    def call_911_using_config_file(self):
        """
        Use the config file to call emergency service.
        """

        loop = "0"
        voice = "woman"

        # create the response
        response = VoiceResponse()
        response.say("".join(["Someone has overdosed at ",
                     self.active_settings.address, ". ", self.active_settings.message]), voice=voice, loop=loop)
        logging.debug(str(response))

        self.create_call_request(self.active_settings.to_phone_number, response, self.active_settings.twilio_sid,
                                 self.active_settings.twilio_token, self.active_settings.twilio_phone_number, 0)
        self.send_notification(0, "911 Requested")

    def sms_test_pushbutton_clicked(self):
        """
        Use the info on the setting page to make sms test.
        """
        phone_number = self.ui.adminPhoneNumberLineEdit.text()
        t_sid = self.ui.twilioSIDLineEdit.text()
        t_token = self.ui.twilioTokenLineEdit.text()
        t_number = self.ui.twilioPhoneNumberLineEdit.text()
        body = "".join(["Internet-based Naloxone Safety Kit. These are the words that will be heard by ", self.ui.emergencyPhoneNumberLineEdit.text(), " when the door is opened: Someone has overdosed at ",
                       self.ui.emergencyAddressLineEdit.text(), ". ", self.ui.emergencyMessageLineEdit.text(), " If the message sounds good, you can save the settings. Thank you."])
        self.create_sms_request(phone_number, body, t_sid, t_token, t_number)
        self.send_notification(4, "SMS Requested")

    def call_test_pushbutton_clicked(self):
        """
        Use the info on the setting page to make phone call test
        """
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
        """
        Communicate with the IO thread to disable the door sensor
        """
        self.ui.disarmPushButton.setVisible(False)
        self.ui.armPushButton.setVisible(True)
        # show notification on taskbar
        self.send_notification(1, "Door Sensor OFF")
        self.active_settings.disarmed = True
        self.io_queue.put(IOItem(
            True, self.active_settings.max_temp, self.active_settings.fan_enabled, self.active_settings.fan_threshold_temp, self.active_settings.naloxone_expiration_date))  # send request to io queue
        logging.info("door sensor disarmed.")

    def arm_door_sensor(self):
        """
        Communicate with the IO thread to enable the door sensor
        """
        self.ui.armPushButton.setVisible(False)
        self.ui.disarmPushButton.setVisible(True)
        self.active_settings.disarmed = False
        self.io_queue.put(IOItem(
            False, self.active_settings.max_temp, self.active_settings.fan_enabled, self.active_settings.fan_threshold_temp, self.active_settings.naloxone_expiration_date))
        logging.info("door sensor armed.")

    def reset_to_default(self):
        """
        Used to check whether the door is still opened and door is still armed.
        """
        if (self.runtime_state.door_opened and not self.active_settings.disarmed):
            self.send_notification(1, "Close Door First")
        else:
            self.goto_home()
            self.runtime_state.emergency_mode = False
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
        """
        Stop the countdown timer by stop the thread.
        """
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
        """
        When the forgot password button is pushed, use the conf file to send the passcode.
        """
        self.send_sms_using_config_file(
            " ".join(["Passcode is ", self.active_settings.admin_passcode]))

    @pyqtSlot()
    def update_time_status(self):
        """
        Change the task bar time and notifications.
        """
        time = QDateTime()
        self.ui.time_label.setText(
            time.currentDateTime().toString("h:mm AP"))
        if (self.request_queue.qsize() != 0):
            self.ui.wait_icon.setVisible(True)
        else:
            self.ui.wait_icon.setVisible(False)
        if (self.status_queue.empty()):
            if (not self.runtime_state.initialized):
                self.ui.status_bar.setVisible(True)
                self.ui.status_bar.setText("Initial Setup")
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
            elif (self.runtime_state.naloxone_destroyed):
                # only show when status queue is empty
                self.ui.status_bar.setVisible(True)
                self.ui.status_bar.setText("Naloxone Destroyed")
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: red; border-radius:25px;border-color: red;border-width: 1px;border-style: solid;")
            else:
                self.ui.status_bar.setVisible(False)
        else:
            msg = self.status_queue.get()
            self.runtime_state.message_level = msg.priority
            self.runtime_state.message_to_display = msg.message
            self.ui.status_bar.setText(self.runtime_state.message_to_display)
            if (self.runtime_state.message_level == 0):
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: red; border-radius:25px;border-color: red;border-width: 1px;border-style: solid;")
                logging.error(self.runtime_state.message_to_display)
            elif (self.runtime_state.message_level == 1):
                self.ui.status_bar.setStyleSheet(
                    "color: black; background-color: yellow; border-radius:25px;border-color: yellow;border-width: 1px;border-style: solid;")
                logging.warning(self.runtime_state.message_to_display)
            else:
                self.ui.status_bar.setStyleSheet(
                    "color: white; background-color: rgb(50,50,50); border-radius:25px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
                logging.info(self.runtime_state.message_to_display)
            self.ui.status_bar.setVisible(True)

    @pyqtSlot()
    def reporting_handling(self):
        """
        Determine whether to send the SMS depending on the admin preferences.
        """
        if (not self.reporting_queue.empty()):
            self.reporting_event = self.reporting_queue.get()
            self.runtime_state.reporting_cat = self.reporting_event.cat
            self.runtime_state.reporting_message = self.reporting_event.message
            if (self.active_settings.sms_reporting and self.active_settings.report_door_opened and self.runtime_state.reporting_cat == 0):
                self.send_sms_using_config_file(
                    self.runtime_state.reporting_message)
            elif (self.active_settings.sms_reporting and self.active_settings.report_emergency_called and self.runtime_state.reporting_cat == 1):
                self.send_sms_using_config_file(
                    self.runtime_state.reporting_message)
            elif (self.active_settings.sms_reporting and self.active_settings.report_naloxone_destroyed and self.runtime_state.reporting_cat == 2):
                self.send_sms_using_config_file(
                    self.runtime_state.reporting_message)
            elif (self.active_settings.sms_reporting and self.active_settings.report_settings_changed and self.runtime_state.reporting_cat == 3):
                self.send_sms_using_config_file(
                    self.runtime_state.reporting_message)
            elif (self.active_settings.sms_reporting and self.active_settings.report_low_balance and self.runtime_state.reporting_cat == 4):
                self.send_sms_using_config_file(
                    self.runtime_state.reporting_message)
            logging.info(self.runtime_state.reporting_message)

    @pyqtSlot()
    def daily_reporting(self):
        """
        Send the SMS to the admin daily.
        It does not guarantee that the message will be delivered as the admin can choose not to receive SMS
        """
        if (self.runtime_state.naloxone_destroyed):
            self.reporting_queue.put(EventItem(2, "Naloxone Destroyed"))
        if (self.runtime_state.low_account_balance):
            self.reporting_queue.put(
                EventItem(4, "Low Twilio Account Balance"))

    @pyqtSlot()
    def twilio_sid_validator(self):
        """
        Used to verify whether the Twilio SID is valid.
        """
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
        """
        Used to verify that whether a phone number is valid.
        """
        result = False
        if (self.sender().text() == str()):
            self.sender().setStyleSheet(
                "color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid;")
            return
        try:
            z = parse(self.sender().text(), None)
        except Exception as e:
            logging.error(e)
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
        """
        Send the passcode to the paramedics phone number.
        Also send the paramedic's phone number to the admin.
        """
        self.create_sms_request(self.ui.paramedic_phone_number_lineedit.text(), " ".join(
            ["The passcode is", self.active_settings.naloxone_passcode]), self.active_settings.twilio_sid, self.active_settings.twilio_token, self.active_settings.twilio_phone_number)
        self.send_sms_using_config_file("Passcode retrieved. The phone number is {}".format(
            self.ui.paramedic_phone_number_lineedit.text()))

    @pyqtSlot()
    def notify_admin(self):
        """
        Send the SMS to the admin to notify them that the paramedics has arrived.
        """
        self.send_sms_using_config_file("Paramedics arrived!")

    @pyqtSlot()
    def test_tts_engine(self):
        """
        Say the alarm message by saying the alarm once.
        """
        self.create_alarm_worker(self.ui.voice_volume_slider.value(
        ), False, self.ui.instr_radio_button.isChecked())

    @pyqtSlot()
    def generate_alarm_file(self):
        """
        Change the GUI to disable multiple alarm file generation.
        Create a separate thread to handle the generation.
        """
        self.create_media_creator(self.ui.alarm_message_lineedit.text())
        self.ui.generate_pushbutton.setEnabled(False)

    @pyqtSlot()
    def alarm_file_generated(self):
        """
        Change the GUI when the alarm file has been generated.
        """
        self.ui.generate_pushbutton.setEnabled(True)
        self.send_notification(4, "Alarm Generated")

    @pyqtSlot()
    def speak_now(self):
        """
        Used to say the alarm when the emergency phone call has failed.
        """
        self.create_alarm_worker(
            self.active_settings.voice_volume, True, self.active_settings.use_default_alarm)
        self.ui.alarmStatusLabel.setText("Speaking")
        self.ui.alarmMutePushButton.setVisible(True)

    @pyqtSlot()
    def stop_alarm(self):
        """
        Stop the alarm by killing the alarm thread.
        """
        self.destroy_alarm_worker()
        self.ui.alarmStatusLabel.setText("Muted")
        self.ui.alarmMutePushButton.setVisible(False)

    @pyqtSlot()
    def call_emergency_now(self):
        """
        Used to call the emergency service.
        """
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
        """
        Used to update the GUI for the countdown time.

        :param sec: The current countdown remaining time.
        """
        self.ui.emergencyCallCountdownLabel.setText(
            "".join(["T-", str(sec), "s"]))
        if (not self.runtime_state.door_opened):
            # when the door is closed within the countdown time, auto reset it.
            self.stop_countdown_button_pushed()
            self.reset_to_default()

    @pyqtSlot(int, str)
    def update_phone_call_gui(self, priority, message):
        """
        Update the phone call status ui. This function is only applied to emergency phone calls.
        The emergency phone call is identified by the priority.

        :param priority: The priority of the phone call.
        :param message: The message to be displayed.
        """
        if (priority == 0 and message == "Call Delivered"):
            self.ui.emergencyCallStatusLabel.setText("Successful")
            self.ui.emergencyCallLastCallLabel.setText(
                QTime().currentTime().toString("h:mm AP"))
            self.reporting_queue.put(
                EventItem(1, "Emergency Call Placed Successfully"))
        else:
            self.ui.emergencyCallStatusLabel.setText("Failed")
            self.reporting_queue.put(EventItem(1, "Emergency Call Failed"))

    @pyqtSlot(bool, bool)
    def update_door_ui(self, door, armed):
        """
        Update the door ui of the main window.

        :param door: Whether the door has been opened.
        :param armed: Whether the door sensor has been armed.
        """
        logging.debug("{} {}".format(str(door), str(armed)))
        if (not door):
            self.ui.doorClosedLineEdit.setText("Closed")
            self.ui.doorOpenLabel.setText("Closed")
            self.runtime_state.door_opened = False
        else:
            self.ui.doorClosedLineEdit.setText("Open")
            self.ui.doorOpenLabel.setText("Open")
            self.runtime_state.door_opened = True
        if (armed):
            self.ui.door_sensor_icon.setVisible(False)
            self.ui.doorArmedLineEdit.setText("Armed")
        else:
            self.ui.door_sensor_icon.setVisible(True)
            self.ui.doorArmedLineEdit.setText("Disarmed")

    @pyqtSlot(bool, QDate)
    def update_naloxone_ui(self, naloxone_good, naloxone_expiration_date):
        """
        Update the naloxone of the main window.

        :param naloxone_good: Whether the naloxone has been destroyed by overheat or expiration.
        :param naloxone_expiration_date: The naloxone expiration date
        """
        self.ui.naloxoneExpirationDateLineEdit.setText(
            naloxone_expiration_date.toString("MMM dd, yy"))
        if (naloxone_good and not self.runtime_state.naloxone_destroyed):
            self.runtime_state.naloxone_destroyed = False
            self.ui.naloxone_destroyed_icon.setVisible(False)
            self.ui.naloxoneStatusLineEdit.setText("OK")
        else:
            self.runtime_state.naloxone_destroyed = True
            self.ui.naloxone_destroyed_icon.setVisible(True)
            self.ui.naloxoneStatusLineEdit.setText("Destroyed")

    @pyqtSlot(bool, float, str, QTime)
    def update_server_ui(self, server, balance, currency, server_check_time):
        """
        Update the server of the main window

        :param server: Whether the Twilio server can be reached.
        :param balance: The current account balance.
        :param currency: The currency type for the account balance.
        :param server_check_time: The last check time of the server status.
        """
        self.ui.serverCheckLineEdit.setText(
            server_check_time.toString("h:mm AP"))
        self.ui.accountBalanceLineEdit.setText(
            " ".join([str(round(balance, 2)), currency]))
        if (server):
            self.ui.no_connection_icon.setVisible(False)
            self.ui.serverStatusLineEdit.setText("ONLINE")
            if (balance < 5):
                self.runtime_state.low_account_balance = True
                self.ui.low_charge_icon.setVisible(True)
            else:
                self.runtime_state.low_account_balance = False
                self.ui.low_charge_icon.setVisible(False)
        else:
            self.ui.no_connection_icon.setVisible(True)
            self.ui.low_charge_icon.setVisible(False)
            self.ui.serverStatusLineEdit.setText("OFFLINE")

    @pyqtSlot(int, int, int, bool)
    def update_temperature_ui(self, temperature, cpu_temperature, pwm, over_temperature):
        """
        Update the temperature of the main window.

        :param temperature: The current naloxone temperature.
        :param cpu_temperature: The current CPU temperature.
        :param pwm: The current pwm of the CPU fan.
        :param over_temperature: Whether the naloxone temperature exceeds the max allowed temperature.
        """
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
        """
        Used to update the displayed screen brightness when the user used the slider on the settings page.
        """
        self.ui.brightness_label.setText("".join([str(value), "%"]))
        if __debug__:
            self.backlight.brightness = value

    @pyqtSlot(int)
    def update_voice_volume(self, value):
        """
        Used to update the voice volume when the user used the slider on the setting page.
        """
        self.ui.voice_volume_label.setText("".join([str(value), "%"]))

    @pyqtSlot(int)
    def update_current_max_temperature(self, value):
        """
        Used to update the current temperature selection when the user uses the slider on the setting page.
        """
        self.ui.CurrentTemperatureLabel.setText("".join([str(value), "℉"]))

    @pyqtSlot(int)
    def update_current_threshold_temperature(self, value):
        """
        Used to update the displayed CPU fan threshold temperature in the settings.
        """
        self.ui.current_fan_temperature.setText("".join([str(value), "℉"]))

    def save_config_file(self):
        """
        Save the config file
        """
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
            "use_default_alarm": self.ui.instr_radio_button.isChecked(),
            "alarm_message": self.ui.alarm_message_lineedit.text(),
            "voice_volume": self.ui.voice_volume_slider.value()
        }
        # Write to a file called "safety_kit.conf"
        with open("safety_kit.conf", "w") as configfile:
            config.write(configfile)
        if (self.ui.enableSMSCheckBox.isChecked() and self.ui.reportSettingsChangedCheckBox.isChecked()):
            self.send_sms_using_config_file("Settings Changed")
        # Send a notification to the task bar.
        self.send_notification(4, "Settings Saved")
        self.load_settings()  # load the settings after saving.

    def show_help(self):
        """
        This function is used to show the helps
        It will read the markdown file depending on the page when the help button is pressed.
        """
        if (self.ui.stackedWidget.currentIndex() == 0):
            logging.debug("home page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/HomePage.md")

        elif (self.ui.stackedWidget.currentIndex() == 1):
            logging.debug("dashboard page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/DashboardPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 0):
            logging.debug("security page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/SecurityPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 1):
            logging.debug("naloxone page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/NaloxonePage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 2):
            logging.debug("twilio page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/TwilioPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 3):
            logging.debug("emergency page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/EmergencyPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 4):
            logging.debug("alarm page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/AlarmPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 5):
            logging.debug("power page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/PowerPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 2 and self.ui.settingsTab.currentIndex() == 6):
            logging.debug("admin page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/AdminPage.md")
        elif (self.ui.stackedWidget.currentIndex() == 3):
            logging.debug("lock screen page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/lock_screen_manual.md")
        elif (self.ui.stackedWidget.currentIndex() == 4):
            logging.debug("door open page")
            self.runtime_state.help_dialog = helpDialog(
                "../user_manual/gui_manual/DoorOpenPage.md")

        self.runtime_state.help_dialog.exec_()

    def change_image(self):
        """
        This function is used to change the image on the home screen
        The user can change the file name to put their own images on the home screen.
        """
        if (self.runtime_state.image_index == 1):
            self.ui.home_frame.setStyleSheet(
                "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_1.png) 0 0 0 0 stretch stretch}")
            self.ui.home_text.setText("Safe medication use is key.")
            self.runtime_state.image_index = 2
        elif (self.runtime_state.image_index == 2):
            self.ui.home_frame.setStyleSheet(
                "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_2.png) 0 0 0 0 stretch stretch}")
            self.ui.home_text.setText("Recovery is possible.")
            self.runtime_state.image_index = 3
        else:
            self.ui.home_frame.setStyleSheet(
                "QWidget#home_frame{border-radius: 5px;border-color:rgb(50,50,50);border-width: 1px;border-style: solid;border-image:url(res/main_page_3.png) 0 0 0 0 stretch stretch}")
            self.ui.home_text.setText("Reach out for help.")
            self.runtime_state.image_index = 1

    def exit_program(self):
        """
        Call to exit the program.
        """
        self.network_timer.stop()  # stop the network timer
        self.status_bar_timer.stop()  # stop the status bar updater
        self.request_queue.put(RequestItem(
            0, "exit", str(), str(), str(), str(), str()))  # stop the io thread
        # stop all other threads
        self.destroy_twilio_worker()
        self.destroy_network_worker()
        self.destroy_io_worker()
        self.destroy_alarm_worker()
        self.destroy_countdown_worker()
        subprocess.run(["pkill", "mpg123"])
        logging.info("exit program.")
        logging.shutdown()
        self.close()


def handleVisibleChanged():
    """
    Used to show windows when virtual keyboard is up.
    control the position of the virtual keyboard
    """
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


def gui_manager():
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    # enable high dpi scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)

    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    if __debug__:
        logging.disable(logging.CRITICAL)  # turn off all loggings

    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                            level=logging.DEBUG)

    gui_manager()
