import numpy as np
import json
from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QThread

#plt.style.use("HHI-HYB")

from core.loop_worker import LoopWorker

from devices import Keithley2400, KeysightN7734A, ThorlabsITC4005, EXFOCTP10

class MeasurementTab(QtWidgets.QWidget):
    # Define a signal to send to main window
    send_parameters = pyqtSignal(dict)

    def __init__(self, apt_tab):
        super().__init__()
        self.apt_tab = apt_tab
        self.params = {} # Store all parameters here
        self.paused = False

        # Load the .ui file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(current_dir, '..', 'GUI', 'measurement_tab.ui')
        ui_file_path = os.path.abspath(ui_file_path)
        self.ui = uic.loadUi(ui_file_path, self)

        # Keithley Inputs
        self.min_current = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'minVoltage')
        self.max_current = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'maxVoltage')
        self.steps_current = self.ui.findChild(QtWidgets.QSpinBox, 'stepsVoltage')
        self.current_limit = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'Strombegrenzung')
        self.temp_setpoint = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'tempSetPoint')

        # EXFO Inputs
        self.start_wavelength = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'startWavelength')
        self.end_wavelength = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'endWavelength')
        self.wavelength_resolution = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'wavelengthResolution')
        self.optical_power = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'opticalPower')
        self.scan_speed = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'scanSpeed')

        # APT Settings Inputs
        self.input_waveguide_distance = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'inputWaveguideDistance')
        self.output_waveguide_distance = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'outputWaveguideDistance')
        self.chip_distance = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'chipDistance')
        self.number_of_chips = self.ui.findChild(QtWidgets.QSpinBox, 'numberOfChips')
        self.inputs_per_chip = self.ui.findChild(QtWidgets.QSpinBox, 'inputsPerChip')
        self.outputs_per_chip = self.ui.findChild(QtWidgets.QSpinBox, 'outputsPerChip')

        # Optical Switches Inputs
        self.switch_1260_1360_TE = self.ui.findChild(QtWidgets.QLineEdit, 'WL_1_TE')
        self.switch_1260_1360_TM = self.ui.findChild(QtWidgets.QLineEdit, 'WL_1_TM')
        self.switch_1350_1510_TE = self.ui.findChild(QtWidgets.QLineEdit, 'WL_2_TE')
        self.switch_1350_1510_TM = self.ui.findChild(QtWidgets.QLineEdit, 'WL_2_TM')
        self.switch_1500_1630_TE = self.ui.findChild(QtWidgets.QLineEdit, 'WL_3_TE')
        self.switch_1500_1630_TM = self.ui.findChild(QtWidgets.QLineEdit, 'WL_3_TM')

        # Address Inputs
        self.lower_switch_IP = self.ui.findChild(QtWidgets.QLineEdit, 'LowerSwitchAdd')
        self.upper_switch_IP = self.ui.findChild(QtWidgets.QLineEdit, 'UpperSwitchAdd')
        self.temp_controller_address = self.ui.findChild(QtWidgets.QLineEdit, 'TempCtrlAdd')
        self.keithley_GPIB = self.ui.findChild(QtWidgets.QLineEdit, 'KeithleyAdd')
        self.exfo_IP = self.ui.findChild(QtWidgets.QLineEdit, 'EXFOAdd')

        # Coupling Inputs
        self.coupling_threshold = self.ui.findChild(QtWidgets.QSpinBox, 'couplingThreshold')
        self.gaus_min = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'gausMin')
        self.gaus_max = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'gausMax')
        self.one_d_scan = self.ui.findChild(QtWidgets.QCheckBox, 'checkBox1D')
        self.two_d_scan = self.ui.findChild(QtWidgets.QCheckBox, 'checkBox2D')

        self.StatusPrinter = self.ui.findChild(QtWidgets.QTextBrowser, 'StatusUpdate')

        # Buttons
        self.InitButton = self.ui.findChild(QtWidgets.QPushButton, 'InitializeButton')
        self.InitButton.clicked.connect(self.initialize_button)

        self.InitButton = self.ui.findChild(QtWidgets.QPushButton, 'DeinitializeButton')
        self.InitButton.clicked.connect(self.deinitialize_button)
        
        self.ClearButton = self.ui.findChild(QtWidgets.QPushButton, 'ClearButton')
        self.ClearButton.clicked.connect(self.clear_button)

        self.LoadSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'LoadSettingsButton')
        self.LoadSettingsButton.clicked.connect(self.load_settings)

        self.SaveSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'SaveSettingsButton')
        self.SaveSettingsButton.clicked.connect(self.save_settings)

        self.SaveSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'StartLoopButton')
        self.SaveSettingsButton.clicked.connect(self.start_loop_button)
        self.loop_thread = None

        self.SaveSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'PauseLoopButton')
        self.SaveSettingsButton.clicked.connect(self.pause_loop_button)

        self.SaveSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'ContinueLoopButton')
        self.SaveSettingsButton.clicked.connect(self.continue_loop_button)

        self.SaveSettingsButton = self.ui.findChild(QtWidgets.QPushButton, 'StopLoopButton')
        self.SaveSettingsButton.clicked.connect(self.stop_loop_button)

        self.ILMeasurementButton = self.ui.findChild(QtWidgets.QPushButton, 'ILButton')
        self.ILMeasurementButton.clicked.connect(self.perform_IL_measurement)

        self.PlotIL = self.ui.findChild(QtWidgets.QFrame, 'PlotIL')
        self.plot_layout = QVBoxLayout(self.PlotIL)
        self.plot_canvas = FigureCanvas(Figure())
        self.plot_toolbar = NavigationToolbar(self.plot_canvas, self)
        self.plot_layout.addWidget(self.plot_toolbar)
        self.plot_layout.addWidget(self.plot_canvas)
        self.ax = self.plot_canvas.figure.add_subplot(111)

        self.PlotCoupling = self.ui.findChild(QtWidgets.QFrame, 'PlotCoupling')
        self.coupling_layout = QVBoxLayout(self.PlotCoupling)
        self.coupling_canvas = FigureCanvas(Figure())
        self.coupling_toolbar = NavigationToolbar(self.coupling_canvas, self)
        self.coupling_layout.addWidget(self.coupling_toolbar)
        self.coupling_layout.addWidget(self.coupling_canvas)
        self.ax_coupling = self.coupling_canvas.figure.add_subplot(111)

        self.PlotMotor = self.ui.findChild(QtWidgets.QFrame, 'PlotMotor')
        self.motor_layout = QVBoxLayout(self.PlotMotor)
        self.motor_canvas = FigureCanvas(Figure())
        self.motor_toolbar = NavigationToolbar(self.motor_canvas, self)
        self.motor_layout.addWidget(self.motor_toolbar)
        self.motor_layout.addWidget(self.motor_canvas)
        self.ax_motor = self.motor_canvas.figure.add_subplot(111)

        self.plotty(np.array([1550, 1552, 1554, 1556, 1558, 1560]), np.array([0,0,0,0,0,0]))
        self.coupling_plot(np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), '1D')
        self.motor_plot(np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]), np.array([0,0,0,0,0,0]))

        # Logo
        self.Logo = self.ui.findChild(QtWidgets.QLabel, 'Logo')
        pixmap = QtGui.QPixmap(os.path.join(current_dir, '..', 'GUI', 'figures', 'HHI_Logo.png'))
        self.Logo.setPixmap(pixmap)
        self.Logo.setScaledContents(True)   

    def initialize_button(self):
        self.collect_and_send_all_params()
        self.initialize_devices()

    def initialize_devices(self):
        """Initializes all devices with the given addresses and creates instances of the classes."""
        self.StatusPrinter.append("Initializing devices...")
        try:
            self.keithley = Keithley2400(self.params['keithley_address'], self.params['compliance_voltage'])
            self.StatusPrinter.append(f"Keithley initialized at address {self.params['keithley_address']}")

            exfo_ip = self.params['exfo_IP']
            exfo_port = 5025  # Standardport für EXFO CTP10
            self.exfo_device = EXFOCTP10(IP=exfo_ip, Port=exfo_port, Module=3, Channel=1, Trace_Type=11)
            self.StatusPrinter.append(f"EXFO CTP10 initialized at IP {exfo_ip} and Port {exfo_port}")

            # Lower and Upper Optical Switch Initialization
            self.lower_optical_switch = KeysightN7734A(self.params['lower_switch_ip'])
            self.StatusPrinter.append(f"Lower Optical Switch initialized at IP {self.params['lower_switch_ip']}")
            self.upper_optical_switch = KeysightN7734A(self.params['upper_switch_ip'])
            self.StatusPrinter.append(f"Upper Optical Switch initialized at IP {self.params['upper_switch_ip']}")

            # Setting routing based on dictionary values
            switch_1500_1630_TE = self.params['switch_1500_1630_TE']

            self.lower_optical_switch.set_routing(f'A,{switch_1500_1630_TE[0]}')
            self.upper_optical_switch.set_routing(f'A,{switch_1500_1630_TE[2]}')
            self.StatusPrinter.append(f"Routing set for switches: Lower - A,{switch_1500_1630_TE[0]}, Upper - A,{switch_1500_1630_TE[2]}")
            
            self.temp_controller = ThorlabsITC4005(self.params['temp_controller_address'])
            self.temp_controller.set_temp(self.params['temp_setpoint'])

            self.apt_tab.initialize_apt()
            self.StatusPrinter.append("All devices initialized successfully.")
        except Exception as e:
            self.StatusPrinter.append(f"Error during device initialization: {e}")
            print(f"Error during device initialization: {e}")

    def deinitialize_button(self):
        """Deinitializes all devices. Sets the Voltage of the Keithley to 0 and closes the communication between the APT and computer."""
        self.StatusPrinter.append("Deinitializing devices...")
        try:
            self.keithley.turn_off()
            self.apt_tab.deinitialize_apt()
            self.StatusPrinter.append("All devices deinitialized successfully.")
        except Exception as e:
            self.StatusPrinter.append(f"Error during device deinitialization: {e}")
            print(f"Error during device deinitialization: {e}")

    def collect_and_send_all_params(self):
        """Collect all parameters, saves them into a dictionary send them to the main window"""        
        try:
            self.params['min_current'] = float(self.min_current.text()) * 1e-3
            self.params['max_current'] = float(self.max_current.text()) * 1e-3
            self.params['steps_current'] = float(self.steps_current.text())
            self.params['compliance_voltage'] = float(self.current_limit.text())
            self.params['temp_setpoint'] = float(self.temp_setpoint.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid Keithley voltage values.')
            return

        try:
            self.params['start_wavelength'] = float(self.start_wavelength.text())
            self.params['end_wavelength'] = float(self.end_wavelength.text())
            self.params['wavelength_resolution'] = float(self.wavelength_resolution.text())
            self.params['optical_power'] = float(self.optical_power.text())
            self.params['scan_speed'] = float(self.scan_speed.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid EXFO values.')
            return

        try: 
            self.params['input_waveguide_distance'] = float(self.input_waveguide_distance.text())
            self.params['output_waveguide_distance'] = float(self.output_waveguide_distance.text())
            self.params['chip_distance'] = float(self.chip_distance.text())
            self.params['number_of_chips'] = int(self.number_of_chips.text()) 
            self.params['inputs_per_chip'] = int(self.inputs_per_chip.text())
            self.params['outputs_per_chip'] = int(self.outputs_per_chip.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid APT Settings values.')
            return

        try:
            self.params['switch_1260_1360_TE'] = self.switch_1260_1360_TE.text()
            self.params['switch_1260_1360_TM'] = self.switch_1260_1360_TM.text()
            self.params['switch_1350_1510_TE'] = self.switch_1350_1510_TE.text()
            self.params['switch_1350_1510_TM'] = self.switch_1350_1510_TM.text()
            self.params['switch_1500_1630_TE'] = self.switch_1500_1630_TE.text()
            self.params['switch_1500_1630_TM'] = self.switch_1500_1630_TM.text()
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid Optical Switch values.')
            return

        try:
            self.params['lower_switch_ip'] = self.lower_switch_IP.text()
            self.params['upper_switch_ip'] = self.upper_switch_IP.text()
            self.params['temp_controller_address'] = self.temp_controller_address.text()
            self.params['keithley_address'] = self.keithley_GPIB.text()
            self.params['exfo_IP'] = self.exfo_IP.text()
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid Address values.')
            return
        
        try:
            self.params['coupling_threshold'] = int(self.coupling_threshold.text())
            self.params['gaus_min'] = float(self.gaus_min.text())
            self.params['gaus_max'] = float(self.gaus_max.text())
            self.params['one_d_scan'] = self.one_d_scan.isChecked()
            self.params['two_d_scan'] = self.two_d_scan.isChecked()
        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter valid Coupling values.')
            return

        self.send_parameters.emit(self.params)
        # QtWidgets.QMessageBox.information(self, 'Success', 'Parameters set successfully.')

    def clear_button(self):
        """Clear all input fields in the UI."""
        self.min_current.clear()
        self.max_current.clear()
        self.steps_current.clear()
        self.start_wavelength.clear()
        self.end_wavelength.clear()
        self.wavelength_resolution.clear()
        self.optical_power.clear()
        self.input_waveguide_distance.clear()
        self.output_waveguide_distance.clear()
        self.chip_distance.clear()
        self.number_of_chips.clear()
        self.inputs_per_chip.clear()
        self.outputs_per_chip.clear()
        self.coupling_threshold.clear()
        self.gaus_min.clear()
        self.gaus_max.clear()
        self.switch_1260_1360_TE.clear()
        self.switch_1260_1360_TM.clear()
        self.switch_1350_1510_TE.clear()
        self.switch_1350_1510_TM.clear()
        self.switch_1500_1630_TE.clear()
        self.switch_1500_1630_TM.clear()
        self.lower_switch_IP.clear()
        self.upper_switch_IP.clear()
        self.temp_controller_address.clear()
        self.keithley_GPIB.clear()
        self.exfo_IP.clear()
        self.temp_setpoint.clear()
        self.scan_speed.clear()

    def save_settings(self):
        """Save all parameters to a JSON file."""
        # Open a file dialog for the user to choose where to save the settings
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, 'Save Settings', '', 'JSON Files (*.json)')

        if file_path:
            # Ensure the file has a .json extension
            if not file_path.endswith('.json'):
                file_path += '.json'

            try:
                # Create the settings dictionary
                settings = {
                    'min_current': self.min_current.value(),
                    'max_current': self.max_current.value(),
                    'steps_current': self.steps_current.value(),
                    'start_wavelength': self.start_wavelength.value(),
                    'end_wavelength': self.end_wavelength.value(),
                    'wavelength_resolution': self.wavelength_resolution.value(),
                    'optical_power': self.optical_power.value(),
                    'temp_setpoint': self.temp_setpoint.value(),
                    'set_scan_speed': self.scan_speed.value(),
                    'compliance_voltage': self.current_limit.value(),
                    'input_waveguide_distance': self.input_waveguide_distance.value(),
                    'output_waveguide_distance': self.output_waveguide_distance.value(),
                    'chip_distance': self.chip_distance.value(),
                    'number_of_chips': self.number_of_chips.value(),
                    'inputs_per_chip': self.inputs_per_chip.value(),
                    'outputs_per_chip': self.outputs_per_chip.value(),
                    'coupling_threshold': self.coupling_threshold.value(),
                    'gaus_min': self.gaus_min.value(),
                    'gaus_max': self.gaus_max.value(),
                    'switch_1260_1360_TE': self.switch_1260_1360_TE.text(),
                    'switch_1260_1360_TM': self.switch_1260_1360_TM.text(),
                    'switch_1350_1510_TE': self.switch_1350_1510_TE.text(),
                    'switch_1350_1510_TM': self.switch_1350_1510_TM.text(),
                    'switch_1500_1630_TE': self.switch_1500_1630_TE.text(),
                    'switch_1500_1630_TM': self.switch_1500_1630_TM.text(),
                    'lower_switch_ip': self.lower_switch_IP.text(),
                    'upper_switch_ip': self.upper_switch_IP.text(),
                    'temp_controller_address': self.temp_controller_address.text(),
                    'keithley_address': self.keithley_GPIB.text(),
                    'exfo_IP': self.exfo_IP.text()
                }
                with open(file_path, 'w') as file:
                    json.dump(settings, file, indent=4)
                self.StatusPrinter.append("Settings saved successfully.")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, 'Error', f'Error saving settings: {e}')
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Save operation cancelled.')

    def load_settings(self):
        """Load all parameters from a JSON file."""
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, 'Load Settings', '', 'JSON Files (*.json)')
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    settings = json.load(file)
                    self.min_current.setValue(settings['min_current'])
                    self.max_current.setValue(settings['max_current'])
                    self.steps_current.setValue(settings['steps_current'])
                    self.start_wavelength.setValue(settings['start_wavelength'])
                    self.end_wavelength.setValue(settings['end_wavelength'])
                    self.wavelength_resolution.setValue(settings['wavelength_resolution'])
                    self.optical_power.setValue(settings['optical_power'])
                    self.temp_setpoint.setValue(settings['temp_setpoint'])
                    self.scan_speed.setValue(settings['set_scan_speed'])
                    self.current_limit.setValue(settings['compliance_voltage'])
                    self.input_waveguide_distance.setValue(settings['input_waveguide_distance'])
                    self.output_waveguide_distance.setValue(settings['output_waveguide_distance'])
                    self.chip_distance.setValue(settings['chip_distance'])
                    self.number_of_chips.setValue(settings['number_of_chips'])
                    self.inputs_per_chip.setValue(settings['inputs_per_chip'])
                    self.outputs_per_chip.setValue(settings['outputs_per_chip'])
                    self.coupling_threshold.setValue(settings['coupling_threshold'])
                    self.gaus_min.setValue(settings['gaus_min'])
                    self.gaus_max.setValue(settings['gaus_max'])
                    self.switch_1260_1360_TE.setText(settings['switch_1260_1360_TE'])
                    self.switch_1260_1360_TM.setText(settings['switch_1260_1360_TM'])
                    self.switch_1350_1510_TE.setText(settings['switch_1350_1510_TE'])
                    self.switch_1350_1510_TM.setText(settings['switch_1350_1510_TM'])
                    self.switch_1500_1630_TE.setText(settings['switch_1500_1630_TE'])
                    self.switch_1500_1630_TM.setText(settings['switch_1500_1630_TM'])
                    self.lower_switch_IP.setText(settings['lower_switch_ip'])
                    self.upper_switch_IP.setText(settings['upper_switch_ip'])
                    self.temp_controller_address.setText(settings['temp_controller_address'])
                    self.keithley_GPIB.setText(settings['keithley_address'])
                    self.exfo_IP.setText(settings['exfo_IP'])
                    self.StatusPrinter.append("Settings loaded successfully.")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, 'Error', f'Error loading settings: {e}')
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', 'No file selected.')

    def start_loop_button(self):
        """
        Starts the loop worker in a separate thread. The APT is communicating with the computer and therefore 
        the loop worker is started in a separate thread to not block the main thread.
        """
        if self.loop_thread and self.loop_thread.isRunning():
            reply = QtWidgets.QMessageBox.question(self, 'Confirmation', 'Do you want to start a new loop?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                self.loop_worker.stop_loop()
                self.loop_thread.quit()
                self.loop_thread.wait()
                self.loop_thread = None
            else:
                return 

        save_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory for Saving Measurement Data', '')

        if not save_path:
            self.StatusPrinter.append("No directory selected. Loop aborted.")
            return

        # EXFO Settings
        start_wavelength = self.params['start_wavelength']
        stop_wavelength = self.params['end_wavelength']
        sampling = self.params['wavelength_resolution']
        laser_power = self.params['optical_power']
        scan_speed = self.params['scan_speed']
        filename = 'measurement'

        # keithleyeinstellungen
        min_current = self.params['min_current']
        max_current = self.params['max_current']
        steps_current = self.params['steps_current']
        temp_setpoint = self.params['temp_setpoint']

        # Switcheinstellungen
        switch_settings = [
        {"switch_1260_1360_TE": self.params['switch_1260_1360_TE'].split(','), "switch_1260_1360_TM": self.params['switch_1260_1360_TM'].split(',')},
        {"switch_1350_1510_TE": self.params['switch_1350_1510_TE'].split(','), "switch_1350_1510_TM": self.params['switch_1350_1510_TM'].split(',')},
        {"switch_1500_1630_TE": self.params['switch_1500_1630_TE'].split(','), "switch_1500_1630_TM": self.params['switch_1500_1630_TM'].split(',')}
        ]

        input_waveguide_distance = self.params['input_waveguide_distance']
        output_waveguide_distance = self.params['output_waveguide_distance']
        chip_distance = self.params['chip_distance']
        number_of_chips = self.params['number_of_chips']
        inputs_per_chip = self.params['inputs_per_chip']
        outputs_per_chip = self.params['outputs_per_chip']

        coupling_threshold = self.params['coupling_threshold']
        gaus_min = self.params['gaus_min']
        gaus_max = self.params['gaus_max']
        if self.params['two_d_scan']:
            scan_type = '2D'
        else:
            scan_type = '1D'
        
        # Erstelle den LoopWorker und übergebe alle notwendigen Parameter:
        self.loop_worker = LoopWorker(self.keithley, self.apt_tab, self.exfo_device, self.lower_optical_switch, self.upper_optical_switch, self.temp_controller, min_current, max_current, steps_current, temp_setpoint, start_wavelength, stop_wavelength, sampling, laser_power, scan_speed, save_path, filename, switch_settings, input_waveguide_distance, output_waveguide_distance, chip_distance, number_of_chips, inputs_per_chip, outputs_per_chip, coupling_threshold, gaus_min, gaus_max, scan_type)
        self.loop_thread = QThread()

        # Verbinde das Signal des Workers mit der Statusaktualisierungsmethode in der GUI
        self.loop_worker.update_status.connect(self.update_status_in_printer)
        self.loop_worker.finished.connect(self.loop_thread.quit)
        self.loop_worker.finished.connect(self.loop_worker.deleteLater)
        self.loop_thread.finished.connect(self.loop_thread.deleteLater)

        # Bewege den Worker in den separaten Thread
        self.loop_worker.moveToThread(self.loop_thread)
        self.loop_thread.started.connect(self.loop_worker.start_loop)

        # Verbinde das Signal des LoopWorkers mit der Plot-Methode
        self.loop_worker.measurement_completed.connect(self.plotty)
        self.loop_worker.coupling_measurement_completed.connect(self.coupling_plot)
        self.loop_worker.motor_offset_completed.connect(self.motor_plot)
        self.loop_worker.finished.connect(self.on_loop_finished)

        # Thread starten
        self.loop_thread.start()

    def pause_loop_button(self):
        """Pauses the loop worker."""
        if hasattr(self, 'loop_worker'):
            self.loop_worker.pause_loop()
            self.StatusPrinter.append("Loop will be paused after the current iteration.")

    def continue_loop_button(self):
        """Continues the loop worker."""
        if hasattr(self, 'loop_worker'):
            self.loop_worker.continue_loop()
            self.StatusPrinter.append("Loop continued.")
    
    def stop_loop_button(self):
        """Slot to handle the clicked signal of the stop loop button."""
        if hasattr(self, 'loop_thread') and self.loop_thread is not None and self.loop_thread.isRunning():
            self.loop_worker.stop_loop()
            self.StatusPrinter.append("Loop stopped.")
        else:
            self.StatusPrinter.append("No loop running.")

    def on_loop_finished(self):
        """Slot to handle the finished signal of the loop worker."""
        if hasattr(self, 'loop_thread') and self.loop_thread is not None:
            if self.loop_thread and self.loop_thread.isRunning():
                self.loop_thread.quit()
                self.loop_thread.wait()
            self.loop_thread = None
            self.loop_worker = None

    def update_status_in_printer(self, message):
        """Slot to update the status printer with the given message."""
        self.StatusPrinter.append(message)

    def perform_IL_measurement(self):
        """Performs an IL measurement with the given parameters."""
        self.StatusPrinter.append("Scanning...")
        
        start_wavelength = self.params['start_wavelength']
        end_wavelength = self.params['end_wavelength']
        sampling = self.params['wavelength_resolution']
        laser_power = self.params['optical_power']
        scan_speed = self.params['scan_speed']
        
        try:
            self.exfo_device.clear_trace_queue()
            self.exfo_device.set_scan_parameters(start_wav=start_wavelength, stop_wav=end_wavelength, sampling=sampling, speed=scan_speed, laser_power=laser_power)
            error_code, error_name = self.exfo_device.perform_scan()
            
            if error_code == 0:
                self.StatusPrinter.append("Scan completed successfully.")
                wavelength_array = self.exfo_device.create_wavelength_array()
                il_data = self.exfo_device.retrieve_ASCii_trace()

            else:
                self.StatusPrinter.append(f"Scan failed with error code {error_code}: {error_name}")
                return

            self.plotty(wavelength_array, il_data)

            now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            data = {
                'metadata': {
                    'measurement_time': now,
                    'start_wavelength_nm': wavelength_array[0],
                    'stop_wavelength_nm': wavelength_array[-1],
                    'sampling_resolution_pm': sampling,
                    'laser_sweep_speed_nm_per_s': scan_speed,
                    'laser_power_dbm': laser_power,
                },
                'data': {
                    'wavelength_nm': wavelength_array.tolist(),
                    'il_te_dbm': il_data,
                }
            }

            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Measurement Data", "", "Json Files (*.json);;All Files (*)")
            
            if file_path:
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file, indent=4)
                self.StatusPrinter.append(f"Data saved to {file_path}")
            else:
                self.StatusPrinter.append("Save operation cancelled.")

        except Exception as e:
            self.StatusPrinter.append(f"Error during IL measurement: {str(e)}")

    def plotty(self, x, y):
        """Slot to plot the given data."""
        self.ax.clear()
        # y = 10 * np.log10(y)
        self.ax.plot(x, y)
        self.ax.set_xlabel('Wavelength [nm]')
        self.ax.set_ylabel('Insertion loss [dB]')
        self.ax.set_title('Current measurement')
        self.ax.grid(True)
        self.plot_canvas.figure.tight_layout()
        self.plot_canvas.draw()

    def coupling_plot(self, power, fitted_power, scan_type='1D', x_vals=None, y_vals=None):
        """Slot to plot the coupling data.
        
        :param power: Measured power values
        :type power: np.ndarray
        :param fitted_power: Fitted power values
        :type fitted_power: np.ndarray
        :param scan_type: Type of scan, '1D' or '2D'
        :type scan_type: str
        :param x_vals: X positions for 2D scan (if scan_type is '2D')
        :type x_vals: np.ndarray
        :param y_vals: Y positions for 2D scan (if scan_type is '2D')
        :type y_vals: np.ndarray
        """
        self.ax_coupling.clear()
        
        if scan_type == '1D':
            # 1D Scan: Linienplot
            position = np.linspace(0, 20, len(power))
            self.ax_coupling.plot(position, power, marker='o', label='Measured power')
            self.ax_coupling.plot(position, fitted_power, label='Fitted power')
            self.ax_coupling.legend(loc='upper right')
            self.ax_coupling.set_xlabel('Position [nm]')
            self.ax_coupling.set_ylabel('Relative power')
            self.ax_coupling.set_title('Coupling check (1D)')
            self.ax_coupling.grid(True)

        elif scan_type == '2D' and x_vals is not None and y_vals is not None:
            # 2D Scan: Heatmap
            x_vals_2d, y_vals_2d = np.meshgrid(np.unique(x_vals), np.unique(y_vals))
            fitted_power = 10 * np.log10(fitted_power/1e-3)
            try:
                # Create the colorplot (heatmap) for the measured data
                c = self.ax_coupling.pcolormesh(x_vals_2d, y_vals_2d, power, shading='auto', cmap='viridis')
                self.coupling_canvas.figure.colorbar(c, ax=self.ax_coupling, label='Measured Power')

                # Plot the fitted 2D Gaussian as contour lines
                if fitted_power is not None:
                    contours = self.ax_coupling.contour(x_vals_2d, y_vals_2d, fitted_power, levels=8, colors='white', linewidths=1)
                    self.ax_coupling.clabel(contours, inline=True, fontsize=8, fmt='%1.1f')

                # Axis labels and title
                self.ax_coupling.set_xlabel('Horizontal Position [nm]')
                self.ax_coupling.set_ylabel('Vertical Position [nm]')
                self.ax_coupling.set_title('Coupling check (2D)')

            except Exception as e:
                self.StatusPrinter.append(f"Error during 2D scan plotting: {e}")    
        
        # Update the plot and refresh the canvas
        self.coupling_canvas.figure.tight_layout()
        self.coupling_canvas.draw()

    def motor_plot(self, input_motor_position, output_motor_position, input_horz_offset, input_vert_offset, output_horz_offset, output_vert_offset, focus_horz_offset, focus_vert_offset):
        """Slot to plot the motor data."""
        try:
            self.ax_motor.clear()
            self.ax_motor.plot(output_motor_position, output_horz_offset, marker = 'o', label='Output: horizontal offset')
            self.ax_motor.plot(output_motor_position, output_vert_offset, marker = 'o', label='Output: vertical offset')
            self.ax_motor.plot(output_motor_position, focus_vert_offset, marker = 'o', label='Output: focus offset')
            self.ax_motor.set_xlabel('Position [mm]')
            self.ax_motor.set_ylabel('Offset [nm]')
            self.ax_motor.set_title('Motor offset')
            self.ax_motor.legend(loc='upper left')
            self.ax_motor.grid(True)
            self.motor_canvas.figure.tight_layout()
            self.motor_canvas.draw()
        except Exception as e:
            self.StatusPrinter.append(f"Error during motor plotting: {e}")