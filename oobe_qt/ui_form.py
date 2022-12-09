# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.4.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(800, 240)
        Widget.setMinimumSize(QSize(800, 240))
        self.verticalLayoutWidget = QWidget(Widget)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 781, 221))
        self.mainVerticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.mainVerticalLayout.setObjectName(u"mainVerticalLayout")
        self.mainVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.verticalLayoutWidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tabWidget.setIconSize(QSize(16, 16))
        self.twilio = QWidget()
        self.twilio.setObjectName(u"twilio")
        self.formLayoutWidget = QWidget(self.twilio)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 10, 751, 111))
        self.twilioFormLayout = QFormLayout(self.formLayoutWidget)
        self.twilioFormLayout.setObjectName(u"twilioFormLayout")
        self.twilioFormLayout.setContentsMargins(0, 0, 0, 0)
        self.twilioSIDLabel = QLabel(self.formLayoutWidget)
        self.twilioSIDLabel.setObjectName(u"twilioSIDLabel")

        self.twilioFormLayout.setWidget(0, QFormLayout.LabelRole, self.twilioSIDLabel)

        self.twilioSIDLineEdit = QLineEdit(self.formLayoutWidget)
        self.twilioSIDLineEdit.setObjectName(u"twilioSIDLineEdit")

        self.twilioFormLayout.setWidget(0, QFormLayout.FieldRole, self.twilioSIDLineEdit)

        self.twilioTokenLabel = QLabel(self.formLayoutWidget)
        self.twilioTokenLabel.setObjectName(u"twilioTokenLabel")

        self.twilioFormLayout.setWidget(1, QFormLayout.LabelRole, self.twilioTokenLabel)

        self.twilioTokenLineEdit = QLineEdit(self.formLayoutWidget)
        self.twilioTokenLineEdit.setObjectName(u"twilioTokenLineEdit")
        self.twilioTokenLineEdit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.twilioFormLayout.setWidget(1, QFormLayout.FieldRole, self.twilioTokenLineEdit)

        self.twilioPhoneNumberLabel = QLabel(self.formLayoutWidget)
        self.twilioPhoneNumberLabel.setObjectName(u"twilioPhoneNumberLabel")

        self.twilioFormLayout.setWidget(2, QFormLayout.LabelRole, self.twilioPhoneNumberLabel)

        self.twilioPhoneNumberLineEdit = QLineEdit(self.formLayoutWidget)
        self.twilioPhoneNumberLineEdit.setObjectName(u"twilioPhoneNumberLineEdit")

        self.twilioFormLayout.setWidget(2, QFormLayout.FieldRole, self.twilioPhoneNumberLineEdit)

        self.tabWidget.addTab(self.twilio, "")
        self.emergency_info = QWidget()
        self.emergency_info.setObjectName(u"emergency_info")
        self.formLayoutWidget_2 = QWidget(self.emergency_info)
        self.formLayoutWidget_2.setObjectName(u"formLayoutWidget_2")
        self.formLayoutWidget_2.setGeometry(QRect(9, 9, 751, 111))
        self.emergencyInfoFormLayout = QFormLayout(self.formLayoutWidget_2)
        self.emergencyInfoFormLayout.setObjectName(u"emergencyInfoFormLayout")
        self.emergencyInfoFormLayout.setContentsMargins(0, 0, 0, 0)
        self.emergencyPhoneNumberLabel = QLabel(self.formLayoutWidget_2)
        self.emergencyPhoneNumberLabel.setObjectName(u"emergencyPhoneNumberLabel")

        self.emergencyInfoFormLayout.setWidget(0, QFormLayout.LabelRole, self.emergencyPhoneNumberLabel)

        self.emergencyPhoneNumberLineEdit = QLineEdit(self.formLayoutWidget_2)
        self.emergencyPhoneNumberLineEdit.setObjectName(u"emergencyPhoneNumberLineEdit")

        self.emergencyInfoFormLayout.setWidget(0, QFormLayout.FieldRole, self.emergencyPhoneNumberLineEdit)

        self.emergencyAddressLabel = QLabel(self.formLayoutWidget_2)
        self.emergencyAddressLabel.setObjectName(u"emergencyAddressLabel")

        self.emergencyInfoFormLayout.setWidget(1, QFormLayout.LabelRole, self.emergencyAddressLabel)

        self.emergencyAddressLineEdit = QLineEdit(self.formLayoutWidget_2)
        self.emergencyAddressLineEdit.setObjectName(u"emergencyAddressLineEdit")

        self.emergencyInfoFormLayout.setWidget(1, QFormLayout.FieldRole, self.emergencyAddressLineEdit)

        self.emergencyMessageLabel = QLabel(self.formLayoutWidget_2)
        self.emergencyMessageLabel.setObjectName(u"emergencyMessageLabel")

        self.emergencyInfoFormLayout.setWidget(2, QFormLayout.LabelRole, self.emergencyMessageLabel)

        self.emergencyMessageLineEdit = QLineEdit(self.formLayoutWidget_2)
        self.emergencyMessageLineEdit.setObjectName(u"emergencyMessageLineEdit")

        self.emergencyInfoFormLayout.setWidget(2, QFormLayout.FieldRole, self.emergencyMessageLineEdit)

        self.twilioAddressWarning = QLabel(self.emergency_info)
        self.twilioAddressWarning.setObjectName(u"twilioAddressWarning")
        self.twilioAddressWarning.setGeometry(QRect(10, 119, 751, 31))
        self.twilioAddressWarning.setTextFormat(Qt.AutoText)
        self.twilioAddressWarning.setAlignment(Qt.AlignCenter)
        self.tabWidget.addTab(self.emergency_info, "")
        self.widget = QWidget()
        self.widget.setObjectName(u"widget")
        self.formLayoutWidget_4 = QWidget(self.widget)
        self.formLayoutWidget_4.setObjectName(u"formLayoutWidget_4")
        self.formLayoutWidget_4.setGeometry(QRect(9, 9, 751, 101))
        self.naloxoneInfoFormLayout = QFormLayout(self.formLayoutWidget_4)
        self.naloxoneInfoFormLayout.setObjectName(u"naloxoneInfoFormLayout")
        self.naloxoneInfoFormLayout.setContentsMargins(0, 0, 0, 0)
        self.naloxoneExpirationDateLabel = QLabel(self.formLayoutWidget_4)
        self.naloxoneExpirationDateLabel.setObjectName(u"naloxoneExpirationDateLabel")

        self.naloxoneInfoFormLayout.setWidget(0, QFormLayout.LabelRole, self.naloxoneExpirationDateLabel)

        self.absoluteMaximumTemperatureLabel = QLabel(self.formLayoutWidget_4)
        self.absoluteMaximumTemperatureLabel.setObjectName(u"absoluteMaximumTemperatureLabel")

        self.naloxoneInfoFormLayout.setWidget(1, QFormLayout.LabelRole, self.absoluteMaximumTemperatureLabel)

        self.temperatureSpinBox = QSpinBox(self.formLayoutWidget_4)
        self.temperatureSpinBox.setObjectName(u"temperatureSpinBox")
        self.temperatureSpinBox.setMaximum(100)
        self.temperatureSpinBox.setSingleStep(5)
        self.temperatureSpinBox.setValue(40)

        self.naloxoneInfoFormLayout.setWidget(1, QFormLayout.FieldRole, self.temperatureSpinBox)

        self.naloxoneExpirationDateHorizontalLayout = QHBoxLayout()
        self.naloxoneExpirationDateHorizontalLayout.setObjectName(u"naloxoneExpirationDateHorizontalLayout")
        self.naloxoneExpirationDateLineEdit = QLabel(self.formLayoutWidget_4)
        self.naloxoneExpirationDateLineEdit.setObjectName(u"naloxoneExpirationDateLineEdit")
        self.naloxoneExpirationDateLineEdit.setAlignment(Qt.AlignCenter)
        self.naloxoneExpirationDateLineEdit.setTextInteractionFlags(Qt.TextEditable)

        self.naloxoneExpirationDateHorizontalLayout.addWidget(self.naloxoneExpirationDateLineEdit)

        self.naloxoneExpirationDatePickerPushButton = QPushButton(self.formLayoutWidget_4)
        self.naloxoneExpirationDatePickerPushButton.setObjectName(u"naloxoneExpirationDatePickerPushButton")

        self.naloxoneExpirationDateHorizontalLayout.addWidget(self.naloxoneExpirationDatePickerPushButton)


        self.naloxoneInfoFormLayout.setLayout(0, QFormLayout.FieldRole, self.naloxoneExpirationDateHorizontalLayout)

        self.tabWidget.addTab(self.widget, "")
        self.admin = QWidget()
        self.admin.setObjectName(u"admin")
        self.formLayoutWidget_3 = QWidget(self.admin)
        self.formLayoutWidget_3.setObjectName(u"formLayoutWidget_3")
        self.formLayoutWidget_3.setGeometry(QRect(10, 10, 751, 91))
        self.adminFormLayout = QFormLayout(self.formLayoutWidget_3)
        self.adminFormLayout.setObjectName(u"adminFormLayout")
        self.adminFormLayout.setContentsMargins(0, 0, 0, 0)
        self.passcodeLabel = QLabel(self.formLayoutWidget_3)
        self.passcodeLabel.setObjectName(u"passcodeLabel")

        self.adminFormLayout.setWidget(0, QFormLayout.LabelRole, self.passcodeLabel)

        self.passcodeLineEdit = QLineEdit(self.formLayoutWidget_3)
        self.passcodeLineEdit.setObjectName(u"passcodeLineEdit")
        self.passcodeLineEdit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.adminFormLayout.setWidget(0, QFormLayout.FieldRole, self.passcodeLineEdit)

        self.adminPhoneNumberLabel = QLabel(self.formLayoutWidget_3)
        self.adminPhoneNumberLabel.setObjectName(u"adminPhoneNumberLabel")

        self.adminFormLayout.setWidget(1, QFormLayout.LabelRole, self.adminPhoneNumberLabel)

        self.adminPhoneNumberLineEdit = QLineEdit(self.formLayoutWidget_3)
        self.adminPhoneNumberLineEdit.setObjectName(u"adminPhoneNumberLineEdit")

        self.adminFormLayout.setWidget(1, QFormLayout.FieldRole, self.adminPhoneNumberLineEdit)

        self.enableSMSLabel = QLabel(self.formLayoutWidget_3)
        self.enableSMSLabel.setObjectName(u"enableSMSLabel")

        self.adminFormLayout.setWidget(2, QFormLayout.LabelRole, self.enableSMSLabel)

        self.enableSMSCheckBox = QCheckBox(self.formLayoutWidget_3)
        self.enableSMSCheckBox.setObjectName(u"enableSMSCheckBox")

        self.adminFormLayout.setWidget(2, QFormLayout.FieldRole, self.enableSMSCheckBox)

        self.tabWidget.addTab(self.admin, "")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.formLayoutWidget_5 = QWidget(self.tab)
        self.formLayoutWidget_5.setObjectName(u"formLayoutWidget_5")
        self.formLayoutWidget_5.setGeometry(QRect(9, 9, 751, 71))
        self.formLayout = QFormLayout(self.formLayoutWidget_5)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.enablePowerSavingLabel = QLabel(self.formLayoutWidget_5)
        self.enablePowerSavingLabel.setObjectName(u"enablePowerSavingLabel")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.enablePowerSavingLabel)

        self.enablePowerSavingCheckBox = QCheckBox(self.formLayoutWidget_5)
        self.enablePowerSavingCheckBox.setObjectName(u"enablePowerSavingCheckBox")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.enablePowerSavingCheckBox)

        self.activeHoursLabel = QLabel(self.formLayoutWidget_5)
        self.activeHoursLabel.setObjectName(u"activeHoursLabel")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.activeHoursLabel)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.startHourLabel = QLabel(self.formLayoutWidget_5)
        self.startHourLabel.setObjectName(u"startHourLabel")
        self.startHourLabel.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.startHourLabel)

        self.activeHoursColon = QLabel(self.formLayoutWidget_5)
        self.activeHoursColon.setObjectName(u"activeHoursColon")
        self.activeHoursColon.setMaximumSize(QSize(20, 16777215))
        self.activeHoursColon.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.activeHoursColon)

        self.endHourLabel = QLabel(self.formLayoutWidget_5)
        self.endHourLabel.setObjectName(u"endHourLabel")
        self.endHourLabel.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.endHourLabel)

        self.activeHoursPushButton = QPushButton(self.formLayoutWidget_5)
        self.activeHoursPushButton.setObjectName(u"activeHoursPushButton")

        self.horizontalLayout_3.addWidget(self.activeHoursPushButton)


        self.formLayout.setLayout(1, QFormLayout.FieldRole, self.horizontalLayout_3)

        self.tabWidget.addTab(self.tab, "")

        self.mainVerticalLayout.addWidget(self.tabWidget)

        self.bottomButtonsHorizontalLayout = QHBoxLayout()
        self.bottomButtonsHorizontalLayout.setObjectName(u"bottomButtonsHorizontalLayout")
        self.saveToFilePushButton = QPushButton(self.verticalLayoutWidget)
        self.saveToFilePushButton.setObjectName(u"saveToFilePushButton")

        self.bottomButtonsHorizontalLayout.addWidget(self.saveToFilePushButton)

        self.saveAndExitPushButton = QPushButton(self.verticalLayoutWidget)
        self.saveAndExitPushButton.setObjectName(u"saveAndExitPushButton")

        self.bottomButtonsHorizontalLayout.addWidget(self.saveAndExitPushButton)

        self.discardAndExitPushButton = QPushButton(self.verticalLayoutWidget)
        self.discardAndExitPushButton.setObjectName(u"discardAndExitPushButton")

        self.bottomButtonsHorizontalLayout.addWidget(self.discardAndExitPushButton)


        self.mainVerticalLayout.addLayout(self.bottomButtonsHorizontalLayout)

#if QT_CONFIG(shortcut)
        self.twilioSIDLabel.setBuddy(self.twilioSIDLineEdit)
        self.twilioTokenLabel.setBuddy(self.twilioTokenLineEdit)
        self.twilioPhoneNumberLabel.setBuddy(self.twilioPhoneNumberLineEdit)
        self.emergencyPhoneNumberLabel.setBuddy(self.emergencyPhoneNumberLineEdit)
        self.emergencyAddressLabel.setBuddy(self.emergencyAddressLineEdit)
        self.emergencyMessageLabel.setBuddy(self.emergencyMessageLineEdit)
        self.naloxoneExpirationDateLabel.setBuddy(self.naloxoneExpirationDatePickerPushButton)
        self.absoluteMaximumTemperatureLabel.setBuddy(self.temperatureSpinBox)
        self.passcodeLabel.setBuddy(self.passcodeLineEdit)
        self.adminPhoneNumberLabel.setBuddy(self.adminPhoneNumberLineEdit)
        self.enableSMSLabel.setBuddy(self.enableSMSCheckBox)
        self.enablePowerSavingLabel.setBuddy(self.enablePowerSavingCheckBox)
        self.activeHoursLabel.setBuddy(self.activeHoursPushButton)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.tabWidget, self.twilioSIDLineEdit)
        QWidget.setTabOrder(self.twilioSIDLineEdit, self.twilioTokenLineEdit)
        QWidget.setTabOrder(self.twilioTokenLineEdit, self.twilioPhoneNumberLineEdit)
        QWidget.setTabOrder(self.twilioPhoneNumberLineEdit, self.emergencyPhoneNumberLineEdit)
        QWidget.setTabOrder(self.emergencyPhoneNumberLineEdit, self.emergencyAddressLineEdit)
        QWidget.setTabOrder(self.emergencyAddressLineEdit, self.emergencyMessageLineEdit)
        QWidget.setTabOrder(self.emergencyMessageLineEdit, self.naloxoneExpirationDatePickerPushButton)
        QWidget.setTabOrder(self.naloxoneExpirationDatePickerPushButton, self.temperatureSpinBox)
        QWidget.setTabOrder(self.temperatureSpinBox, self.passcodeLineEdit)
        QWidget.setTabOrder(self.passcodeLineEdit, self.adminPhoneNumberLineEdit)
        QWidget.setTabOrder(self.adminPhoneNumberLineEdit, self.enableSMSCheckBox)
        QWidget.setTabOrder(self.enableSMSCheckBox, self.enablePowerSavingCheckBox)
        QWidget.setTabOrder(self.enablePowerSavingCheckBox, self.activeHoursPushButton)
        QWidget.setTabOrder(self.activeHoursPushButton, self.saveToFilePushButton)
        QWidget.setTabOrder(self.saveToFilePushButton, self.saveAndExitPushButton)
        QWidget.setTabOrder(self.saveAndExitPushButton, self.discardAndExitPushButton)

        self.retranslateUi(Widget)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Internet-based Naloxone Safety Kit Setup", None))
#if QT_CONFIG(whatsthis)
        self.tabWidget.setWhatsThis(QCoreApplication.translate("Widget", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.twilioSIDLabel.setText(QCoreApplication.translate("Widget", u"Twilio &SID", None))
        self.twilioTokenLabel.setText(QCoreApplication.translate("Widget", u"Twilio &Token", None))
        self.twilioPhoneNumberLabel.setText(QCoreApplication.translate("Widget", u"Twilio Phone &Number", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.twilio), QCoreApplication.translate("Widget", u"Twilio", None))
        self.emergencyPhoneNumberLabel.setText(QCoreApplication.translate("Widget", u"Emergency Phone &Number", None))
        self.emergencyAddressLabel.setText(QCoreApplication.translate("Widget", u"Emergency &Address", None))
        self.emergencyMessageLabel.setText(QCoreApplication.translate("Widget", u"Emergency &Message", None))
        self.twilioAddressWarning.setText(QCoreApplication.translate("Widget", u"Remember to set the proper address in Twilio console as well!", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.emergency_info), QCoreApplication.translate("Widget", u"Emergency Info", None))
        self.naloxoneExpirationDateLabel.setText(QCoreApplication.translate("Widget", u"Naloxone &Expiration Date", None))
        self.absoluteMaximumTemperatureLabel.setText(QCoreApplication.translate("Widget", u"Absolute Maximum &Temperature", None))
        self.naloxoneExpirationDateLineEdit.setText(QCoreApplication.translate("Widget", u"Use Date Picker ->", None))
        self.naloxoneExpirationDatePickerPushButton.setText(QCoreApplication.translate("Widget", u"Open Expiration Date Picker", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.widget), QCoreApplication.translate("Widget", u"Naloxone Info", None))
        self.passcodeLabel.setText(QCoreApplication.translate("Widget", u"&Passcode", None))
        self.adminPhoneNumberLabel.setText(QCoreApplication.translate("Widget", u"Admin Phone &Number", None))
        self.enableSMSLabel.setText(QCoreApplication.translate("Widget", u"Enable &SMS", None))
        self.enableSMSCheckBox.setText(QCoreApplication.translate("Widget", u"Send text message to admin when door is opened or Naloxone is destroyed", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.admin), QCoreApplication.translate("Widget", u"Admin", None))
        self.enablePowerSavingLabel.setText(QCoreApplication.translate("Widget", u"Enable &Power Saving", None))
        self.enablePowerSavingCheckBox.setText(QCoreApplication.translate("Widget", u"Turn off the display outside active hours. Display will be on when door opens.", None))
        self.activeHoursLabel.setText(QCoreApplication.translate("Widget", u"&Active Hours", None))
        self.startHourLabel.setText(QCoreApplication.translate("Widget", u"Start Time", None))
        self.activeHoursColon.setText(QCoreApplication.translate("Widget", u"to", None))
        self.endHourLabel.setText(QCoreApplication.translate("Widget", u"End Time", None))
        self.activeHoursPushButton.setText(QCoreApplication.translate("Widget", u"Open Active Hours Picker", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("Widget", u"Power Management", None))
        self.saveToFilePushButton.setText(QCoreApplication.translate("Widget", u"Save to File", None))
        self.saveAndExitPushButton.setText(QCoreApplication.translate("Widget", u"Save and Exit", None))
        self.discardAndExitPushButton.setText(QCoreApplication.translate("Widget", u"Discard and Exit", None))
    # retranslateUi

