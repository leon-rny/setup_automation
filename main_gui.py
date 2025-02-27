from PyQt5 import QtWidgets
import sys

from core import APTTab, MeasurementTab

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self.initUI()

    def initUI(self):
        """Initialize the main window of the application and add the tabs."""
        self.setWindowTitle('Automated Waveguide Measurement')

        tabWidget = QtWidgets.QTabWidget()
        self.apt_tab = APTTab()                    
        self.init_tab = MeasurementTab(self.apt_tab)
        tabWidget.addTab(self.init_tab, 'Initialize')
        tabWidget.addTab(self.apt_tab, 'APT')
        self.setCentralWidget(tabWidget)
        
    def get_status_printer(self):
        return self.init_tab.StatusPrinter
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow(app)
    mainWin.show()
    sys.exit(app.exec_())
