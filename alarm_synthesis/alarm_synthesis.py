import pyttsx3


def say_alarm(message, loop, voice):
    engine = pyttsx3.init()

    # Change the voice for the alarm
    voices = engine.getProperty('voices')
    if (voice == "woman"):
        engine.setProperty("voice", voices[1].id)
    else:
        engine.setProperty("voice", voices[0].id)

    if (loop == 0):
        # say the alarm forever if loop==0
        while (True):
            engine.say(message)
            engine.runAndWait()
    else:
        # else, say for limited times
        for _ in range(loop):
            engine.say(message)
            engine.runAndWait()


if __name__ == "__main__":
    say_alarm("Hello World", 2, "man")
