# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'time_picker.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_activeHoursPicker(object):
    def setupUi(self, activeHoursPicker):
        activeHoursPicker.setObjectName("activeHoursPicker")
        activeHoursPicker.resize(400, 300)
        activeHoursPicker.setStyleSheet("background-color:black")
        self.verticalLayoutWidget = QtWidgets.QWidget(activeHoursPicker)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(9, 9, 381, 281))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.activeHoursPickerVerticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.activeHoursPickerVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.activeHoursPickerVerticalLayout.setObjectName("activeHoursPickerVerticalLayout")
        self.activeHoursPickerLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.activeHoursPickerLabel.setMinimumSize(QtCore.QSize(0, 30))
        self.activeHoursPickerLabel.setMaximumSize(QtCore.QSize(16777215, 20))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.activeHoursPickerLabel.setFont(font)
        self.activeHoursPickerLabel.setStyleSheet("color:white")
        self.activeHoursPickerLabel.setObjectName("activeHoursPickerLabel")
        self.activeHoursPickerVerticalLayout.addWidget(self.activeHoursPickerLabel)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.activeHoursPickerVerticalLayout.addItem(spacerItem)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.startTimeLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.startTimeLabel.setFont(font)
        self.startTimeLabel.setStyleSheet("color:white")
        self.startTimeLabel.setObjectName("startTimeLabel")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.startTimeLabel)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.startTimeEdit = QtWidgets.QTimeEdit(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.startTimeEdit.setFont(font)
        self.startTimeEdit.setStyleSheet("color:white; border-color:white;border-width: 1px; border-radius:3px;border-style: outset;text-size:14px;")
        self.startTimeEdit.setTime(QtCore.QTime(8, 0, 0))
        self.startTimeEdit.setObjectName("startTimeEdit")
        self.horizontalLayout.addWidget(self.startTimeEdit)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout)
        self.endTimeLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.endTimeLabel.setFont(font)
        self.endTimeLabel.setStyleSheet("color:white")
        self.endTimeLabel.setObjectName("endTimeLabel")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.endTimeLabel)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.endTimeEdit = QtWidgets.QTimeEdit(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.endTimeEdit.setFont(font)
        self.endTimeEdit.setStyleSheet("color:white; border-color:white;border-width: 1px; border-radius:3px;border-style: outset;text-size:14px;")
        self.endTimeEdit.setTime(QtCore.QTime(18, 0, 0))
        self.endTimeEdit.setObjectName("endTimeEdit")
        self.horizontalLayout_2.addWidget(self.endTimeEdit)
        self.formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.activeHoursPickerVerticalLayout.addLayout(self.formLayout)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.activeHoursPickerVerticalLayout.addItem(spacerItem1)
        self.activeHoursPickerButtonBox = QtWidgets.QDialogButtonBox(self.verticalLayoutWidget)
        self.activeHoursPickerButtonBox.setMinimumSize(QtCore.QSize(102, 0))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.activeHoursPickerButtonBox.setFont(font)
        self.activeHoursPickerButtonBox.setStyleSheet("color: white; background-color: black; border-color:white;border-width: 1px; border-radius:3px;border-style: outset;min-width: 100px;min-height=25px;\n"
"")
        self.activeHoursPickerButtonBox.setOrientation(QtCore.Qt.Horizontal)
        self.activeHoursPickerButtonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.activeHoursPickerButtonBox.setCenterButtons(False)
        self.activeHoursPickerButtonBox.setObjectName("activeHoursPickerButtonBox")
        self.activeHoursPickerVerticalLayout.addWidget(self.activeHoursPickerButtonBox)

        self.retranslateUi(activeHoursPicker)
        self.activeHoursPickerButtonBox.accepted.connect(activeHoursPicker.accept) # type: ignore
        self.activeHoursPickerButtonBox.rejected.connect(activeHoursPicker.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(activeHoursPicker)

    def retranslateUi(self, activeHoursPicker):
        _translate = QtCore.QCoreApplication.translate
        activeHoursPicker.setWindowTitle(_translate("activeHoursPicker", "Time Picker"))
        self.activeHoursPickerLabel.setText(_translate("activeHoursPicker", "Select Active Hours"))
        self.startTimeLabel.setText(_translate("activeHoursPicker", "Start at"))
        self.endTimeLabel.setText(_translate("activeHoursPicker", "End at"))
