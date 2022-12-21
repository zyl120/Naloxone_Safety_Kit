from PyQt5 import QtWidgets, QtCore, QtGui
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
import os
import sys
import configparser
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


class NetworkWorker(QtCore.QThread):
    update_server = QtCore.pyqtSignal(bool, float, str, QtCore.QTime)

    def __init__(self):
        super(NetworkWorker, self).__init__()
        self.hostname = "www.twilio.com"  # ping twilio directly
        self.currentTime = QtCore.QTime()

    def run(self):
        while True:
            config = configparser.ConfigParser()
            config.read("safety_kit.conf")
            account_sid = config["twilio"]["twilio_sid"]
            account_token = config["twilio"]["twilio_token"]
            client = Client(account_sid, account_token)

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

class TimeWorker(QtCore.QThread):
    update_time = QtCore.pyqtSignal(QtCore.QDateTime)

    def __init__(self):
        super(TimeWorker, self).__init__()

    def run(self):
        while True:
            self.update_time.emit(QtCore.QDateTime().currentDateTime())
            sleep(1)


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


class SharedMemoryWorker(QtCore.QThread):
    # Worker thread to read the shared memory block.
    # These signals can be used to change the GUI when emitted.
    update_door = QtCore.pyqtSignal(bool, bool)
    update_temperature = QtCore.pyqtSignal(int, int, int, bool)
    update_server = QtCore.pyqtSignal(bool, QtCore.QTime)
    update_naloxone = QtCore.pyqtSignal(bool, QtCore.QDate)
    update_time = QtCore.pyqtSignal(QtCore.QTime)
    go_to_door_open_signal = QtCore.pyqtSignal()

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
        cpu_temperature = 0
        while True:
            #print("read shm")
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
                cpu_temperature = self.shared_array[19]
            if (door and not disarmed):  # if door opened and the switch is armed
                self.go_to_door_open_signal.emit()
            self.update_door.emit(door, not disarmed)
            self.update_temperature.emit(
                temperature, cpu_temperature, pwm, over_temperature)
            self.update_naloxone.emit(
                not naloxone_expired and not naloxone_overheat, QtCore.QDate(year, month, day))
            sleep(1)


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self, shared_array):
        super(ApplicationWindow, self).__init__()
        self.door_opened = False
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
        self.load_settings()
        self.lock_settings()
        self.goto_home()

        self.get_shared_array_worker = SharedMemoryWorker(self.shared_array)
        self.get_shared_array_worker.update_door.connect(self.update_door_ui)
        self.get_shared_array_worker.update_temperature.connect(
            self.update_temperature_ui)
        self.get_shared_array_worker.update_naloxone.connect(
            self.update_naloxone_ui)
        self.get_shared_array_worker.go_to_door_open_signal.connect(
            self.goto_door_open)
        self.get_shared_array_worker.start()

        self.account_balance_worker = NetworkWorker()
        self.account_balance_worker.update_server.connect(
            self.update_server_ui)
        self.account_balance_worker.start()

        self.time_worker = TimeWorker()
        self.time_worker.update_time.connect(self.update_time_ui)
        self.time_worker.start()

    def load_settings(self):
        # load the settings from the conf file.
        print("loading settings")
        try:
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
            naloxone_expiration_date = QtCore.QDate.fromString(
                config["naloxone_info"]["naloxone_expiration_date"])
            self.ui.naloxoneExpirationDateEdit.setDate(
                naloxone_expiration_date)
            self.ui.temperatureSlider.setValue(
                int(config["naloxone_info"]["absolute_maximum_temperature"]))
            self.ui.passcodeLineEdit.setText(config["admin"]["passcode"])
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
            if (config["admin"]["allow_paramedics"] == "True"):
                self.ui.paramedicsLabel.setVisible(True)
                self.ui.paramedicsPhoneNumberLineEdit.setVisible(True)
                self.ui.getPasscodePushButton.setVisible(True)
                self.ui.paramedicsWarning.setVisible(True)
            else:
                self.ui.paramedicsLabel.setVisible(False)
                self.ui.paramedicsPhoneNumberLineEdit.setVisible(False)
                self.ui.getPasscodePushButton.setVisible(False)
                self.ui.paramedicsWarning.setVisible(False)
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
        except Exception as e:
            print("Failed to load config file")
            msg = QtWidgets.QMessageBox()
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.setDetailedText(str(e))
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Failed to read config file.")
            msg.setStyleSheet(
                "QMessageBox{background-color: black}QLabel{color: white;font-size:16px}QPushButton{ color: white; background-color: rgb(50,50,50); border-radius:3px;border-color: rgb(50,50,50);border-width: 1px;border-style: solid; height:30;width:140; font-size:16px}")
            # msg.buttonClicked.connect(msg.close)
            msg.exec_()
        else:
            print("config file loaded")

    def lock_settings(self):
        # lock the whole setting page.
        self.ui.unlockSettingsPushButton.setText("Unlock Settings")
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

    def unlock_settings(self):
        # unlock the whole setting page. Should only be called after the user enter the correct passcode.
        self.ui.unlockSettingsPushButton.setText("Lock Settings")
        self.ui.unlockSettingsPushButton.setVisible(False)
        self.ui.lockSettingsPushButton.setVisible(True)
        self.load_settings()
        self.ui.saveToFilePushButton.setVisible(True)
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabVisible(0, True)
        self.ui.settingsTab.setTabVisible(1, True)
        self.ui.settingsTab.setTabVisible(2, True)
        self.ui.settingsTab.setTabVisible(3, True)
        self.ui.settingsTab.setTabVisible(4, True)
        self.ui.settingsTab.setTabVisible(5, True)

    def check_passcode(self):
        # First read from the conf file
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        if (self.ui.passcodeEnterLineEdit.text() == config["admin"]["passcode"]):
            # If passcode is correct
            return True
        else:
            # If passcode is wrong
            self.ui.passcodeEnterLabel.setText("Try Again")
            self.ui.passcodeEnterLineEdit.clear()
            return False

    def check_passcode_unlock_settings(self):
        passcode_check_result = self.check_passcode()
        if (passcode_check_result):
            # If passcode is correct, unlock the settings
            self.unlock_settings()
            self.goto_settings()
        else:
            # If passcode is wrong, lock the settings
            self.lock_settings()

    def lock_unlock_settings(self):
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
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        admin_phone_number = config["admin"]["admin_phone_number"]
        address = config["emergency_info"]["emergency_address"]
        t_sid = config["twilio"]["twilio_sid"]
        t_token = config["twilio"]["twilio_token"]
        t_number = config["twilio"]["twilio_phone_number"]
        self.sender = SMSWorker(admin_phone_number, "The naloxone safety box at " +
                                address + " sent the following information: " + msg, t_sid, t_token, t_number)
        self.sender.start()

    def call_911_using_config_file(self):
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        account_sid = config["twilio"]["twilio_sid"]
        auth_token = config["twilio"]["twilio_token"]
        address = config["emergency_info"]["emergency_address"]
        message = config["emergency_info"]["emergency_message"]
        from_phone_number = config["twilio"]["twilio_phone_number"]
        to_phone_number = config["emergency_info"]["emergency_phone_number"]
        loop = "0"
        voice = "woman"

        # create the response
        response = VoiceResponse()
        response.say("Message: " + message + ". Address: " +
                     address + ".", voice=voice, loop=loop)
        print("INFO: resonse: " + str(response))

        self.sender = CallWorker(
            to_phone_number, response, account_sid, auth_token, from_phone_number)
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
            with self.shared_array.get_lock():
                self.shared_array[8] = 1
            return "Information", "Door Disarmed.", "The door sensor is now off."
        else:
            self.ui.disarmPushButton.setText("Disarm")
            with self.shared_array.get_lock():
                self.shared_array[8] = 0
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
            self.ui.emergencyCallStatusLabel.setText("Waiting")
            self.ui.emergencyCallLastCallLabel.setText("N/A")
            return "Information", "System Reset to Default.", "N/A"

    def stop_countdown_button_pushed(self):
        # Stop the countdown timer by stop it.
        self.ui.settingsPushButton.setVisible(True)
        self.ui.stopCountdownPushButton.setVisible(False)
        self.ui.countdownLabel.setVisible(False)
        self.ui.emergencyCallCountdownLabel.setVisible(False)
        self.ui.emergencyCallStatusLabel.setText("Waiting")
        self.ui.emergencyCallLastCallLabel.setText("N/A")
        self.countdown_thread.stop()

    def forgot_password_button_pushed(self):
        # when the forgot password button is pushed, use the conf file to send
        # the passcode
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        passcode = config["admin"]["passcode"]
        self.send_sms_using_config_file("Passcode is " + passcode)

    def get_passcode_button_pushed(self):
        print("Enter function")
        config = configparser.ConfigParser()
        config.read("safety_kit.conf")
        paramedic_phone_number = self.ui.paramedicsPhoneNumberLineEdit.text()
        address = config["emergency_info"]["emergency_address"]
        t_sid = config["twilio"]["twilio_sid"]
        t_token = config["twilio"]["twilio_token"]
        t_number = config["twilio"]["twilio_phone_number"]
        passcode = config["admin"]["passcode"]
        self.send_to_paramedic = SMSWorker(paramedic_phone_number, "The passcode of the naloxone safety box at " +
                                           address + " is: " + passcode, t_sid, t_token, t_number)
        self.send_to_paramedic.start()
        print("sent to paramedics")
        self.send_sms_using_config_file(
            "Paramedics want to access the settings. The number is " + paramedic_phone_number + ".")
        print("sent to admin")

    @QtCore.pyqtSlot()
    # Used to communicate with the shm to make phone calls.
    def call_emergency_now(self):
        print("call 911 now pushed")
        self.call_911_using_config_file()
        self.ui.emergencyCallStatusLabel.setText("Requested")
        # self.ui.emergencyCallLastCallLabel.setText(
        #     QtCore.QTime().currentTime().toString("h:mm AP"))
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

    @QtCore.pyqtSlot(QtCore.QDateTime)
    def update_time_ui(self, current_time):
        # update the time of the main window.
        self.ui.currentTimeLineEdit.setText(current_time.toString("MMM d, yyyy h:mm AP"))

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
            "naloxone_expiration_date": self.ui.naloxoneExpirationDateEdit.date().toString(),
            "absolute_maximum_temperature": self.ui.temperatureSlider.value()
        }
        config["admin"] = {
            "passcode": self.ui.passcodeLineEdit.text(),
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
            # msg.buttonClicked.connect(msg.close)
        msg.exec_()
        if (self.ui.enableSMSCheckBox.isChecked() and self.ui.reportSettingsChangedCheckBox.isChecked()):
            self.send_sms_using_config_file("Settings Changed")
        print("INFO: save config file")
        self.load_settings()

    def exit_program(self):
        os.kill(0, signal.SIGINT)  # kill all processes by sending signal 2.
        self.close()


def gui_manager(shared_array):
    #os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    app = QtWidgets.QApplication(sys.argv)
    # QtGui.QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
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
