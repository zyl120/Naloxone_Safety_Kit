from PyQt5.QtCore import QDateTime, Qt, QTimer, QRegExp
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
                             QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
                             QVBoxLayout, QWidget, QMainWindow)
from PyQt5.QtGui import QRegExpValidator
import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.originalPalette = QApplication.palette()
        #self.createMessageGroup()
        bottomRightGroupBox = QGroupBox("Emergency Info")
        lineEditLabel = QLabel("Emergency Contact")
        lineEdit = QLineEdit("+15189615258")
        phoneRegex = QRegExp(
            "^(\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$")
        phoneValidator = QRegExpValidator(phoneRegex)
        lineEdit.setValidator(phoneValidator)
        addressLabel = QLabel("Address")
        addressLineEdit = QLineEdit("115 Hoy Rd, Ithaca, NY 14850")
        textEditLabel = QLabel("Message")
        textEdit = QTextEdit()
        textEdit.setPlainText("Please enter the message here")
        textEdit.textChanged.connect(self.phone_call)
        callButton = QPushButton("Call")
        callButton.setDefault(True)
        callButton.clicked.connect(self.phone_call)
        callButton.setParent(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(lineEditLabel)
        layout.addWidget(lineEdit)
        layout.addWidget(addressLabel)
        layout.addWidget(addressLineEdit)
        layout.addWidget(textEditLabel)
        layout.addWidget(textEdit)

        voiceLayout = QHBoxLayout()
        voiceLabel = QLabel("Voice")
        voice1RadioButton = QRadioButton("Voice 1")
        voice1RadioButton.setChecked(True)
        voice2RadioButton = QRadioButton("Voice 2")
        voiceLayout.addWidget(voiceLabel)
        voiceLayout.addWidget(voice1RadioButton)
        voiceLayout.addWidget(voice2RadioButton)
        loopLayout = QHBoxLayout()
        loopLabel = QLabel("Loop")
        loopSlider = QSlider(Qt.Orientation.Horizontal)
        loopSlider.setMinimum(0)
        loopSlider.setMaximum(100)
        loopSlider.setValue(20)
        loopSlider.setTickPosition(2)
        loopLayout.addWidget(loopLabel)
        loopLayout.addWidget(loopSlider)
        layout.addLayout(voiceLayout)
        layout.addLayout(loopLayout)
        layout.addWidget(callButton)
        bottomRightGroupBox.setLayout(layout)

        mainLayout = QGridLayout()
        mainLayout.addWidget(bottomRightGroupBox)
        widget = QWidget()
        widget.setLayout(mainLayout)
        self.setCentralWidget(widget)

    def phone_call(self):
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        resonse = VoiceResponse()
        location = sender.text()
        resonse.say("Hello World from " + location +
                    ". ", voice="woman", loop=0)
        print(resonse)
        


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
