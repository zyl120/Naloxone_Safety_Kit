import subprocess, os, sys, apt

def error_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("[E] You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")
    print("[I] Checking OS...")
    with subprocess.Popen(["uname", "-o"], stdout = subprocess.PIPE) as process:
        output = process.communicate()[0].decode("utf-8").rstrip()
        if(output != "GNU/Linux"):
            sys.exit("[E] Wrong OS Type, exit.")

    print("[I] Refresh repo list...")
    cache = apt.cache.Cache()
    cache.update()
    cache.open()

    print("[I] Installing python3-pyqt5...")
    pkg_name = "python3-pyqt5"
    pkg = cache[pkg_name]
    if pkg.is_installed:
        print("[I] {pkg_name} already installed".format(pkg_name=pkg_name))
    else:
        pkg.mark_install()

        try:
            cache.commit()
        except Exception as e:
            sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    
    print("[I] Installing mpg123...")
    pkg_name = "mpg123"
    pkg = cache[pkg_name]
    if pkg.is_installed:
        print("[I] {pkg_name} already installed".format(pkg_name=pkg_name))
    else:
        pkg.mark_install()

        try:
            cache.commit()
        except Exception as e:
            sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    
    print("[I] Installing twilio using pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "twilio"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    finally:
        print("[I] twilio installed successfully")

    print("[I] Installing qrcode using pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    finally:
        print("[I] qrcode installed successfully")

    print("[I] Installing Adafruit-DHT using pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Adafruit-DHT"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    finally:
        print("[I] Adafruit-DHT installed successfully")

    print("[I] Installing gtts using pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gtts"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    finally:
        print("[I] gtts installed successfully")

    print("[I] Installing phonenumbers using pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "phonenumbers"], stdout=subprocess.DEVNULL)
    except Exception as e:
        sys.exit("[E] Sorry, package installation failed [{}]".format(str(e)))
    finally:
        print("[I] phonenumbers installed successfully")

    print("[I] Basic Package Set Installed Successfully")
    

    
