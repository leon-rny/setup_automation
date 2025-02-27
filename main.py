import sys
import pyvisa
from PyQt5 import QtWidgets

from main_gui import MainWindow

class App:  
    def __init__(self):
        self.status_printer = None
        self.params = {}
    
    def receive_parameters(self, params):
        self.params = params

    def update_status(self, message):
        self.status_printer.append(message)

def main():
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    print(f'--------------\nAvailable resources: {resources}\n--------------')
    app = QtWidgets.QApplication(sys.argv)
    application = App()
    mainWin = MainWindow(application)
    mainWin.showMaximized()

    application.status_printer = mainWin.get_status_printer()
    application.update_status("GUI started successfully.")
    mainWin.init_tab.send_parameters.connect(application.receive_parameters)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
    