import subprocess, os, sys, apt

def error_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")
    print("Checking OS...")
    with subprocess.Popen(["uname", "-o"], stdout = subprocess.PIPE) as process:
        output = process.communicate()[0].decode("utf-8").rstrip()
        if(output != "Linux"):
            sys.exit("Wrong OS Type, exit.")

    print("Refresh repo list...")
    #with subprocess.Popen(["sudo", "apt-get", "update"], stdout = subprocess.PIPE) as process:
