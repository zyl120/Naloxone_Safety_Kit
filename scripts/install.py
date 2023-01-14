import subprocess
import os
import sys
import apt

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit(
            "[E] You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")
    print("[I] Checking OS...")
    with subprocess.Popen(["uname", "-o"], stdout=subprocess.PIPE) as process:
        output = process.communicate()[0].decode("utf-8").rstrip()
        if(output != "GNU/Linux"):
            sys.exit("[E] Wrong OS Type, exit.")

    username = input("Enter your user name: ")
    print("[I] Current working directory is {}".format(os.getcwd()))
    try:
        home_dir = os.path.expanduser("~"+username)
        print("[I] It will now be changed to your home directory {}".format(home_dir))
        os.chdir(os.path.expanduser("~"+username))
    except Exception as e:
        sys.exit("[E] Invalid user name.")
    else:
        print("[I] Current working directory is {}".format(os.getcwd()))

    print("[I] Refresh repo list...")
    cache = apt.cache.Cache()
    cache.update()
    cache.open()

    pkg_name_list = ["python3-pyqt5", "mpg123", "git", "build-essential", "qtdeclarative5-dev", "libqt5svg5-dev", "qtbase5-private-dev", "qml-module-qtquick-controls2", "qml-module-qtquick-controls", "qml-module-qt-labs-folderlistmodel", "libxcb-composite0-dev", "libxcb-cursor-dev", "libxcb-damage0-dev", "libxcb-dpms0-dev", "libxcb-dri2-0-dev", "libxcb-dri3-dev", "libxcb-ewmh-dev", "libxcb-glx0-dev", "libxcb-icccm4-dev", "libxcb-image0-dev", "libxcb-imdkit-dev", "libxcb-keysyms1-dev", "libxcb-present-dev", "libxcb-randr0-dev",
                     "libxcb-record0-dev", "libxcb-render-util0-dev", "libxcb-render0-dev", "libxcb-res0-dev", "libxcb-screensaver0-dev", "libxcb-shape0-dev", "libxcb-shm0-dev", "libxcb-sync-dev", "libxcb-util-dev", "libxcb-util0-dev", "libxcb-xf86dri0-dev", "libxcb-xfixes0-dev", "libxcb-xinerama0-dev", "libxcb-xinput-dev", "libxcb-xkb-dev", "libxcb-xrm-dev", "libxcb-xtest0-dev", "libxcb-xv0-dev", "libxcb-xvmc0-dev", "libxcb1-dev", "libx11-xcb-dev", "libglu1-mesa-dev", "libxrender-dev", "libxi-dev", "libxkbcommon-dev", "libxkbcommon-x11-dev"]
    for pkg_name in pkg_name_list:
        pkg = cache[pkg_name]
        if pkg.is_installed:
            print("[I] {pkg_name} already installed".format(pkg_name=pkg_name))
        else:
            pkg.mark_install()

    print("[I] Installing packages...")
    try:
        cache.commit()
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    else:
        print("[I] apt installation completes successfully")

    pip_list = ["twilio", "qrcode", "Adafruit-DHT", "gtts", "phonenumbers"]
    for pip_pkg in pip_list:
        print("[I] Installing {} using pip...".format(pip_pkg))
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_pkg], stdout=subprocess.DEVNULL)
        except Exception as e:
            sys.exit("[E] Sorry, package installation of {} failed [{}]".format(
                pip_pkg, str(e)))
        else:
            print("[I] {} installed successfully".format(pip_pkg))

    print("[I] Probing QT_PREFIX_PATH...")
    from PyQt5.QtCore import QLibraryInfo
    QT_PREFIX_PATH = QLibraryInfo.location(QLibraryInfo.PrefixPath)
    print("[I] QT_PREFIX_PATH={}".format(QT_PREFIX_PATH))

    print("[I] Downloading Qt Virtual Keyboard from GitHub...")
    try:
        subprocess.check_call(["git", "clone", "-b", "5.15",
                              "https://github.com/qt/qtvirtualkeyboard.git"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to download Qt Virtual Keyboard [{}]".format(str(e)))
    else:
        print("[I] Download Successfully")

    new_path = os.getcwd() + "/qtvirtualkeyboard"
    print("[I] Change directory to {}".format(new_path))
    os.chdir(new_path)

    print("[I] Running qmake...")
    try:
        subprocess.check_call(["qmake"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run qmake [{}]".format(str(e)))
    else:
        print("[I] qmake Successfully")

    print("[I] Running make, it will take ~30 minutes...")
    try:
        subprocess.check_call(["make"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run make [{}]".format(str(e)))
    else:
        print("[I] make Successfully")

    print("[I] Running make install...")
    try:
        subprocess.check_call(["make", "install"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("Failed to run make install [{}]".format(str(e)))
    else:
        print("[I] make install Successfully")

    print("[I] Moving Files...")
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
        sys.exit("[E] Failed to move files. [{}]".format(str(e)))
    else:
        print("[I] Moving Files Successfully")

    print("[I] Install Successfully")
    sys.exit(0)
