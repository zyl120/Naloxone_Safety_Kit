# Qt Virtual Keyboard Installation Manual

- The qt virtual keyboard is the virtual keyboard provided by the qt installation. Some applications, such as the plasma desktop, provide the virtual keyboard as an alternative to the physical keyboard so that the user can enter information using the touch screen.
- However, the Raspbian OS does not provide an easy way to install the virtual keyboard, and we must install the virtual keyboard on our own. 
- *Note: If you do not want to change the settings using the touch screen, you can ignore these steps and just copy the edited “safety.conf” to the directory of the GUI script.*
- *You need to finish the steps described in the software installation manual before following this manual.*

## Chapter 1: Install Dependencies

### Step 1.1: Open Terminal

- Open the Terminal on the Raspberry Pi.

### Step 1.2: Refresh package list

- In the opened terminal window, enter the following command:

        sudo apt-get update

- By running this command, we can get an updated list of software and repositories from the server. You may be prompted to enter the password.

### Step 1.3: Install git and build-essential

- After the system finishes the previous command, enter the following command:

        sudo apt install git build-essential

- This command installs the `git` and the `build-essential` packages necessary to build the Qt virtual keyboard.

### Step 1.4: Check the PyQt5 prefix path

- Since the PyQt5 will load the module from the prefix path, we need to determine the prefix path using the following command:

        python -c "from PyQt5.QtCore import QLibraryInfo;  
        print('QT_PREFIX_PATH:', QLibraryInfo.location(QLibraryInfo.PrefixPath))"

    ![Check QT_PREFIX_PATH.](Screenshot_20230104_234533.png)

- In most cases, the prefix path is at `/usr`. However, if your prefix path is not at `/usr`, you need to adjust the command in later steps.
- ***We define `QT_PREFIX_PATH` as `/usr` in later steps. You should adjust the path accordingly before executing the command.***

### Step 1.5: Download dependencies

- We need to download qt5 from the repo. To do so, enter the following command into the terminal: 

        sudo apt-get install python3-pyqt5
        sudo apt-get install qtdeclarative5-dev
        sudo apt-get install libqt5svg5-dev
        sudo apt-get install qtbase5-private-dev
        sudo apt-get install qml-module-qtquick-controls2
        sudo apt-get install qml-module-qtquick-controls
        sudo apt-get install qml-module-qt-labs-folderlistmodel

### Step 1.6: Download More dependencies

        sudo apt-get install '^libxcb.*-dev'
        sudo apt-get install libx11-xcb-dev
        sudo apt-get install libglu1-mesa-dev
        sudo apt-get install libxrender-dev
        sudo apt-get install libxi-dev
        sudo apt-get install libxkbcommon-dev
        sudo apt-get install libxkbcommon-x11-dev

### Step 1.7: Change directory to home

- Later steps assume that your working directory is at your home folder. To change the current working directory to the home folder, run the following command:

        cd ~

### Step 1.8: Download QtVirtualKeyboard source code from GitHub

- We are using the LTS version of the Qt5 for the project. To download the latest LTS source code of the Qt virtual keyboard, run the following command:

        git clone -b 5.15 https://github.com/qt/qtvirtualkeyboard.git

### Step 1.9: Open the qtvirtualkeyboard folder

- By default, step 1.8 will download the source code to a directory called `qtvirtualkeyboard` in your home directory. To open that directory, run the following command:

        cd ~/qtvirtualkeyboard

- You can verify the current working directory by using running the following command:

        pwd
        
- You are expected to see the output of the above command as `/home/USER_NAME/qtvirtualkeyboard`, where `USER_NAME` is the name of the account. 

### Step 1.10: Run qmake

- To generate the `makefile` automatically, run the following command: 

        qmake

### Step 1.11: Build

- Then you can use the below command to compile the Qt virtual keyboard automatically. This will take around 15 minutes on Raspberry Pi.

        sudo make

### Step 1.12: Install

- By running the below command, the binary files will be moved to the appropriate locations on the system.

        sudo make install

- By default, the destination is at `~\qtvirtualkeyboard`.

## Chapter 2: Copy Files

### Step 2.13: Copy libQt5VirtualKeyboard.so.5

- In the terminal window, enter the following command:

        sudo cp -L ~/qtvirtualkeyboard/lib/libQt5VirtualKeyboard.so.5  
        QT_PREFIX_PATH/lib/libQt5VirtualKeyboard.so.5

- If your QT_PREFIX_PATH is `/usr`, the command will be

        sudo cp -L ~/qtvirtualkeyboard/lib/libQt5VirtualKeyboard.so.5  
        /usr/lib/libQt5VirtualKeyboard.so.5

- If your compiled version is 5.15.8, you need to adjust the command to match the version number.

### Step 2.14: Create folder QT_PREFIX_PATH/plugins/platforminputcontexts

- You need to create the folder `QT_PREFIX_PATH/plugins/platforminputcontexts` using the following command:

        sudo mkdir QT_PREFIX_PATH/plugins
        sudo mkdir QT_PREFIX_PATH/plugins/platforminputcontexts

- Again, you should replace the path with the `QT_PREFIX_PATH` on your system. 

### Step 2.15: Copy libqtvirtualkeyboardplugin.so

- You need to copy the `libqtvirtualkeyboardplugin.so` to `QT_PREFIX_PATH/plugins/platforminputcontexts` using the following command:

        sudo cp ~/qtvirtualkeyboard/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so  
        QT_PREFIX_PATH/plugins/platforminputcontexts/

### Step 2.16: Copy virtual keyboard plugin Folder

- You need to cop the whole `virtualkeyboard` folder to `QT_PREFIX_PATH/plugins` using the following command: 

        sudo cp -r ~/qtvirtualkeyboard/plugins/virtualkeyboard/  
        QT_PREFIX_PATH/plugins/

### Step 2.17: Copy virtual keyboard Qml folder

- You will also need to copy the Qml’s virtualkeyboard folder to `QT_PREFIX_PATH/qml/QtQuick` folder. But first, you need to create the destination folder using the command:

        sudo mkdir QT_PREFIX_PATH/qml
        sudo mkdir QT_PREFIX_PATH/qml/QtQuick

- Then, you can copy the whole folder using the following command:

        sudo cp -r ~/qtvirtualkeyboard/qml/QtQuick/VirtualKeyboard/  
        QT_PREFIX_PATH/qml/QtQuick/

## References

- [Install Qt virtual keyboard on Linux.](https://stackoverflow.com/questions/62473386/pyqt5-show-virtual-keyboard)
- [Compile Qt virtual keyboard on Raspberry Pi.](https://stackoverflow.com/questions/63719347/install-qtvirtualkeyboard-in-raspberry-pi/63720177#63720177)
