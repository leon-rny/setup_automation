import sys
import os
from PyQt5 import QtWidgets, QAxContainer, uic, QtGui

from devices import ThorlabsNanoTrak, ThorlabsMotor, OwisHumes100

class APTTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Load the UI file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(current_dir, '..', 'GUI', 'apt_tab.ui')
        ui_file_path = os.path.abspath(ui_file_path)
        self.ui = uic.loadUi(ui_file_path, self)

        # Logo
        self.Logo = self.ui.findChild(QtWidgets.QLabel, 'Logo')
        pixmap = QtGui.QPixmap(os.path.join(current_dir, '..', 'GUI', 'figures', 'HHI_Logo.png'))
        self.Logo.setPixmap(pixmap)
        self.Logo.setScaledContents(True)

        # Embed ActiveX controls using QAxWidget (Control Panels)
        self.InputNT_Ctrl = self.ui.findChild(QAxContainer.QAxWidget, 'InputNanotrak')
        self.InputNT_Ctrl.setControl("{1C7D94A1-5153-4D3F-85C5-FBBE60F634AF}")
        self.OutputNT_Ctrl = self.ui.findChild(QAxContainer.QAxWidget, 'OutputNanotrak')
        self.OutputNT_Ctrl.setControl("{1C7D94A1-5153-4D3F-85C5-FBBE60F634AF}")
        self.FocusNT_Ctrl = self.ui.findChild(QAxContainer.QAxWidget, 'FocusNanotrak')
        self.FocusNT_Ctrl.setControl("{1C7D94A1-5153-4D3F-85C5-FBBE60F634AF}")
        self.Motor_Ctrl = self.ui.findChild(QAxContainer.QAxWidget, 'MotorControl')
        self.Motor_Ctrl.setControl("{3CE35BF3-1E13-4D2C-8C0B-DEF6314420B3}")
        self.MotorChip_Ctrl = self.ui.findChild(QAxContainer.QAxWidget, 'MotorControlChip')
        self.MotorChip_Ctrl.setControl("{3CE35BF3-1E13-4D2C-8C0B-DEF6314420B3}")
        
        self.IB = self.ui.findChild(QtWidgets.QPushButton, 'InitializeButton')
        self.IB.clicked.connect(self.initialize_apt)

        self.DB = self.ui.findChild(QtWidgets.QPushButton, 'DeinitializeButton')
        self.DB.clicked.connect(self.deinitialize_apt)

        self.TrackB = self.ui.findChild(QtWidgets.QPushButton, 'TrackAllButton')
        self.TrackB.clicked.connect(self.track_all)

        self.LatchB = self.ui.findChild(QtWidgets.QPushButton, 'LatchAllButton')
        self.LatchB.clicked.connect(self.latch_all)

        self.move_motor_button = self.ui.findChild(QtWidgets.QPushButton, 'MoveMotorButton')
        self.move_motor_button.clicked.connect(self.move_motor)

        self.input_motor = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'InputMotor')
        self.output_motor = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'OutputMotor')
        self.focus_motor = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'FocusMotor')
        self.chip_motor = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'MiddleStage')
        self.height_chip_motor = self.ui.findChild(QtWidgets.QDoubleSpinBox, 'HeightMiddleStage')

    def get_circ_position_all(self):
        """Get the circular position of all three NanoTrak devices and checks if they are in the center of the tracking area."""
        hor_pos_input, vert_pos_input, _ =  self.InputNT.circ_position()
        hor_pos_output, vert_pos_output, _ =  self.OutputNT.circ_position()
        hor_pos_focus, vert_pos_focus, _ =  self.FocusNT.circ_position()
        if hor_pos_input <=2 or hor_pos_input >= 8 or vert_pos_input <= 2 or vert_pos_input >= 8 or hor_pos_output <=2 or hor_pos_output >= 8 or vert_pos_output <= 2 or vert_pos_output >= 8 or hor_pos_focus <=2 or hor_pos_focus >= 8 or vert_pos_focus <= 2 or vert_pos_focus >= 8:
            return False
        else:
            return True

    def latch_all(self):
        """Latch all three NanoTrak devices."""
        self.InputNT.latch()
        self.OutputNT.latch()
        self.FocusNT.latch()

    def track_all(self):
        """Track all three NanoTrak devices."""
        self.InputNT.track()
        self.OutputNT.track()
        self.FocusNT.track()

    def change_circ_diameter_all(self, diameter):
        """
        Change the circular diameter of all three NanoTrak devices.
        
        :param diameter: The diameter of the circular range in NT units (0.0 to 5.0 NT units).
        :type diameter: float
        """
        self.InputNT.circ_diameter(diameter)
        self.OutputNT.circ_diameter(diameter)
        self.FocusNT.circ_diameter(diameter)

    def move_motor(self):
        input_motor = float(self.input_motor.text())
        output_motor = float(self.output_motor.text())
        focus_motor = float(self.focus_motor.text())
        chip_motor = float(self.chip_motor.text())
        height_chip_motor = float(self.height_chip_motor.text())

        if input_motor != 0:
            self.MotorIN.move_relative(input_motor)
        if output_motor != 0:
            self.MotorOUT.move_relative(output_motor)
        if focus_motor != 0:
            self.MotorFocus.move_relative(focus_motor)
        if chip_motor != 0:
            self.MotorChip.move_relative(chip_motor)
        if height_chip_motor != 0:
            owis = OwisHumes100('ASRL9::INSTR')
            owis.move_relative(height_chip_motor)
        if input_motor == output_motor == focus_motor == chip_motor == height_chip_motor == 0:
            QtWidgets.QMessageBox.information(self, 'Information', 'No motor selected.')
        
    def initialize_apt(self):
        """Initialize all APT devices with given parameters. It is important that the frequency of the Nanotrak devices are different and not colinear."""
        InputNT_TextBox = self.ui.findChild(QtWidgets.QLineEdit, 'InputNTSerial')
        InputNT_serial = int(InputNT_TextBox.text())
        self.InputNT = ThorlabsNanoTrak(self.InputNT_Ctrl, HWSerialNum=InputNT_serial, iGain=250, fFreq=25, fHorzHomePos=5, fVertHomePos=5, fDia=0.1, InputSignal=None)
        self.InputNT.initialize()

        OutputNT_TextBox = self.ui.findChild(QtWidgets.QLineEdit, 'OutputNTSerial')
        OutputNT_serial = int(OutputNT_TextBox.text())
        self.OutputNT = ThorlabsNanoTrak(self.OutputNT_Ctrl, HWSerialNum=OutputNT_serial, iGain=250, fFreq=40, fHorzHomePos=5, fVertHomePos=5, fDia=0.1, InputSignal=None) # set Input InputSignal='OP' or None
        self.OutputNT.initialize()

        FocusNT_TextBox = self.ui.findChild(QtWidgets.QLineEdit, 'FocusNTSerial')
        FocusNT_serial = int(FocusNT_TextBox.text())
        self.FocusNT = ThorlabsNanoTrak(self.FocusNT_Ctrl, HWSerialNum=FocusNT_serial, iGain=250, fFreq=30, fHorzHomePos=5, fVertHomePos=5, fDia=0.5, InputSignal=None)
        self.FocusNT.initialize()

        MotorControl_TextBox = self.ui.findChild(QtWidgets.QLineEdit, 'MCSerial')
        MotorControl_Serial = int(MotorControl_TextBox.text())
        self.MotorFocus = ThorlabsMotor(self.Motor_Ctrl, HWSerialNum=MotorControl_Serial, IChanID=0, fMinVel=0, fAccn=0.2, fMaxVel=0.5, fStepSize=0.001, fMinPos=-50, fMaxPos=50, IUnits=1, fPitch=1, IDirSense=1, IRewLimSwitch=1, IFwdLimSwitch=1)        
        self.MotorOUT = ThorlabsMotor(self.Motor_Ctrl, HWSerialNum=MotorControl_Serial, IChanID=1, fMinVel=0, fAccn=0.2, fMaxVel=0.5, fStepSize=0.001, fMinPos=-50, fMaxPos=50, IUnits=1, fPitch=1, IDirSense=1, IRewLimSwitch=1, IFwdLimSwitch=1)
        self.MotorFocus.initialize()
        self.MotorOUT.initialize()

        MotorChipControl_TextBox = self.ui.findChild(QtWidgets.QLineEdit, 'MCChipSerial')
        MotorChipControl_Serial = int(MotorChipControl_TextBox.text())
        self.MotorIN = ThorlabsMotor(self.MotorChip_Ctrl, HWSerialNum=MotorChipControl_Serial, IChanID=0, fMinVel=0, fAccn=0.2, fMaxVel=0.5, fStepSize=0.001, fMinPos=-50, fMaxPos=50, IUnits=1, fPitch=1, IDirSense=1, IRewLimSwitch=1, IFwdLimSwitch=1)
        self.MotorChip = ThorlabsMotor(self.MotorChip_Ctrl, HWSerialNum=MotorChipControl_Serial, IChanID=1, fMinVel=0, fAccn=0.2, fMaxVel=0.5, fStepSize=0.001, fMinPos=-50, fMaxPos=50, IUnits=1, fPitch=1, IDirSense=1, IRewLimSwitch=1, IFwdLimSwitch=1)
        self.MotorIN.initialize()
        self.MotorChip.initialize()

    def deinitialize_apt(self):
        """Deinitialize all APT devices."""
        self.InputNT.deinitialize()
        self.OutputNT.deinitialize()
        self.FocusNT.deinitialize()
        self.MotorIN.deinitialize_motor()
        self.MotorOUT.deinitialize_motor()
        self.MotorChip.deinitialize_motor()
        self.MotorFocus.deinitialize_motor()
        self.MotorIN.deinitialize()
        self.MotorOUT.deinitialize()
        self.MotorChip.deinitialize()
        self.MotorFocus.deinitialize()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = APTTab()
    window.show()
    sys.exit(app.exec_())
