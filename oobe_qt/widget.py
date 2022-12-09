# This Python file uses the following encoding: utf-8
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from ui_door_close_window import Ui_door_close_main_window

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.active_hour_start = QtCore.QTime(8, 0, 0)
        self.active_hour_end = QtCore.QTime(18, 0, 0)
        self.ui = Ui_door_close_main_window()
        self.ui.setupUi(self)
        self.ui.stackedWidget.setCurrentIndex(1)

        self.ui.naloxoneExpirationDateEdit.setDisplayFormat("MMM dd, yy")
        self.ui.exitPushButton.clicked.connect(self.exit_program)
        #self.ui.disarmPushButton.clicked.connect(self.toggle_door_arm)
        self.ui.homePushButton.clicked.connect(self.goto_home)
        self.ui.settingsPushButton.clicked.connect(self.goto_settings)
        self.ui.dashboardPushButton.clicked.connect(self.goto_dashboard)
        #self.ui.unlockSettingsPushButton.clicked.connect(
        #            self.lock_unlock_settings)
        #self.ui.saveToFilePushButton.clicked.connect(self.save_config_file)
        #self.ui.replaceNaloxonePushButton.clicked.connect(
        #            self.replace_naloxone)
        #self.ui.temperatureSlider.valueChanged.connect(
        #            self.update_current_max_temperature)
        #self.load_settings()
        self.lock_settings()
        self.goto_door_open()


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
        self.close()

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
        self.ui.settingsTab.setCurrentIndex(0)
        self.ui.settingsTab.setTabEnabled(0, True)
        self.ui.settingsTab.setTabEnabled(1, True)
        self.ui.settingsTab.setTabEnabled(2, True)
        self.ui.settingsTab.setTabEnabled(3, True)
        self.ui.settingsTab.setTabEnabled(4, True)
        self.ui.settingsTab.setTabEnabled(5, True)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
