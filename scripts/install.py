import subprocess
import os
import sys
import apt

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit(
            "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")
    print("Checking OS...")
    with subprocess.Popen(["uname", "-o"], stdout=subprocess.PIPE) as process:
        output = process.communicate()[0].decode("utf-8").rstrip()
        if (output != "GNU/Linux"):
            sys.exit("Wrong OS Type, exit.")

    username = input("Enter your user name: ")
    print("Current working directory is {}".format(os.getcwd()))
    try:
        home_dir = os.path.expanduser("~"+username)
        print("It will now be changed to your home directory {}".format(home_dir))
        os.chdir(os.path.expanduser("~"+username))
    except Exception as e:
        sys.exit("Invalid user name.")
    else:
        print("Current working directory is {}".format(os.getcwd()))

    print("Refresh repo list...")
    cache = apt.cache.Cache()
    cache.update()
    cache.open()

    pkg_name_list = ["libgpiod2", "python3-pyqt5", "mpg123", "git", "build-essential", "qtdeclarative5-dev", "libqt5svg5-dev", "qtbase5-private-dev", "qml-module-qtquick-controls2", "qml-module-qtquick-controls", "qml-module-qt-labs-folderlistmodel", "libxcb-composite0-dev", "libxcb-cursor-dev", "libxcb-damage0-dev", "libxcb-dpms0-dev", "libxcb-dri2-0-dev", "libxcb-dri3-dev", "libxcb-ewmh-dev", "libxcb-glx0-dev", "libxcb-icccm4-dev", "libxcb-image0-dev", "libxcb-imdkit-dev", "libxcb-keysyms1-dev", "libxcb-present-dev", "libxcb-randr0-dev",
                     "libxcb-record0-dev", "libxcb-render-util0-dev", "libxcb-render0-dev", "libxcb-res0-dev", "libxcb-screensaver0-dev", "libxcb-shape0-dev", "libxcb-shm0-dev", "libxcb-sync-dev", "libxcb-util-dev", "libxcb-util0-dev", "libxcb-xf86dri0-dev", "libxcb-xfixes0-dev", "libxcb-xinerama0-dev", "libxcb-xinput-dev", "libxcb-xkb-dev", "libxcb-xrm-dev", "libxcb-xtest0-dev", "libxcb-xv0-dev", "libxcb-xvmc0-dev", "libxcb1-dev", "libx11-xcb-dev", "libglu1-mesa-dev", "libxrender-dev", "libxi-dev", "libxkbcommon-dev", "libxkbcommon-x11-dev"]
    for pkg_name in pkg_name_list:
        pkg = cache[pkg_name]
        if pkg.is_installed:
            print("{pkg_name} already installed".format(pkg_name=pkg_name))
        else:
            pkg.mark_install()

    print("Installing packages...")
    try:
        cache.commit()
    except Exception as e:
        sys.exit("Sorry, package installation failed [{}]".format(str(e)))
    else:
        print("apt installation completes successfully")

    pip_list = ["twilio", "qrcode", "adafruit-python-shell",
                "adafruit-circuitpython-dht", "gtts", "phonenumbers", "rpi-backlight"]
    for pip_pkg in pip_list:
        print("Installing {} using pip...".format(pip_pkg))
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_pkg], stdout=subprocess.DEVNULL)
        except Exception as e:
            sys.exit("Sorry, package installation of {} failed [{}]".format(
                pip_pkg, str(e)))
        else:
            print("{} installed successfully".format(pip_pkg))

    print("Update udev rule to allow screen brightness change...")
    try:
        os.system("echo 'SUBSYSTEM==\"backlight\",RUN+=\"/bin/chmod 666 /sys/class/backlight/%k/brightness /sys/class/backlight/%k/bl_power\"' | sudo tee -a /etc/udev/rules.d/backlight-permissions.rules")
    except Exception as e:
        sys.exit("Failed to update udev rule")
    else:
        print("udev rule updated.")

    print("Probing QT_PREFIX_PATH...")
    from PyQt5.QtCore import QLibraryInfo
    QT_PREFIX_PATH = QLibraryInfo.location(QLibraryInfo.PrefixPath)
    print("QT_PREFIX_PATH={}".format(QT_PREFIX_PATH))

    print("Downloading Qt Virtual Keyboard from GitHub...")
    try:
        subprocess.check_call(["git", "clone", "-b", "5.15",
                              "https://github.com/qt/qtvirtualkeyboard.git"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to download Qt Virtual Keyboard [{}]".format(str(e)))
    else:
        print("Download Successfully")

    new_path = os.getcwd() + "/qtvirtualkeyboard"
    print("Change directory to {}".format(new_path))
    os.chdir(new_path)

    print("Running qmake...")
    try:
        subprocess.check_call(["qmake"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run qmake [{}]".format(str(e)))
    else:
        print("qmake Successfully")

    print("Running make, it will take ~30 minutes...")
    try:
        subprocess.check_call(["make"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run make [{}]".format(str(e)))
    else:
        print("make Successfully")

    print("Running make install...")
    try:
        subprocess.check_call(["make", "install"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run make install [{}]".format(str(e)))
    else:
        print("make install Successfully")

    print("Moving Files...")
    try:
        subprocess.check_call(["cp", "-L", "{}/lib/libQt5VirtualKeyboard.so.5".format(new_path),
                              "{}/lib/libQt5VirtualKeyboard.so.5".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["mkdir", "{}/plugins".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["mkdir", "{}/plugins/platforminputcontexts".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(["cp", "{}/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so".format(
            new_path), "{}/plugins/platforminputcontexts/".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(["cp", "-r", "{}/plugins/virtualkeyboard/".format(
            new_path), "{}/plugins/".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["mkdir", "{}/qml".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["mkdir", "{}/qml/QtQuick".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
        subprocess.check_call(["cp", "-r", "{}/qml/QtQuick/VirtualKeyboard/".format(
            new_path), "{}/qml/QtQuick/".format(QT_PREFIX_PATH)], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to move files. [{}]".format(str(e)))
    else:
        print("Moving Files Successfully")

    # print("Changing to home directory")
    # os.chdir(os.path.expanduser("~"+username))

    # print("Cloning Software from GitHub")
    # clone = "git clone https://github.com/zyl120/Naloxone_Safety_Kit"
    # os.system(clone)
    # print("The software is license under LGPL-3. Please read the license before using.")

    # print("Creating systemd service file")
    # L = [
    #     "[Unit]\n",
    #     "Description=Internet-Based Naloxone Safety Kit\n",
    #     "After=network.target\n\n",
    #     "[Service]\n",
    #     "Type=idle\n",
    #     "Restart=on-failure\n",
    #     "User={}\n".format(username),
    #     "ExecStart=/usr/bin/python {}/main.py\n\n".format(
    #         os.getcwd() + "/Naloxone_Safety_Kit/main"),
    #     "[Install]\n",
    #     "WantedBy=graphical.target"]

    # with open("/etc/systemd/system/naloxone_safety_kit.service", "w") as s_file:
    #     s_file.writelines(L)

    # print("Enabling Service")
    # os.system("systemctl enable naloxone_safety_kit.service")

    # print("Starting Service")
    # os.system("systemctl start naloxone_safety_kit.service")

    print("Install Successfully")
    sys.exit(0)
