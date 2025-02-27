import numpy as np

class ThorlabsNanoTrak:
    def __init__(self, AX, HWSerialNum: int, iGain: int, fFreq: float, fHorzHomePos: float, fVertHomePos:float, fDia:float, InputSignal: str):
        self.AX = AX
        self.HWSerialNum = HWSerialNum
        self.iGain = iGain
        self.fFreq = np.float32(fFreq)
        self.fHorzHomePos = np.float32(fHorzHomePos)
        self.fVertHomePos = np.float32(fVertHomePos)
        self.fDia = np.float32(fDia)
        self.InputSignal = InputSignal

    def initialize(self, lMode=2):
        """
        Initializes the NanoTrak module.
        This method configures the hardware by setting the serial number, enabling hardware channels, 
        setting loop gain and circular frequency, and moving the device to the home position. 
        Additionally, if the input signal is optical ('OP'), it sets the input source and tracking threshold 
        and configures the units mode accordingly.
        """
        self.AX.setProperty('HWSerialNum', self.HWSerialNum)
        self.AX.dynamicCall('StartCtrl()')
        self.AX.dynamicCall('EnableHWChannel(0)')
        self.AX.dynamicCall('EnableHWChannel(1)')
        self.AX.dynamicCall('SetLoopGain({})'.format(self.iGain))
        self.AX.dynamicCall('SetCircFreq({})'.format(self.fFreq))
        self.AX.dynamicCall('SetCircHomePos({},{})'.format(self.fHorzHomePos, self.fVertHomePos))
        self.AX.dynamicCall('SetAmpControlMode({})'.format(lMode))
        self.AX.dynamicCall('SetAmpControlMode({})'.format(lMode))
        self.AX.dynamicCall('MoveCircHome()')
        if self.InputSignal == 'OP':
            self.AX.dynamicCall('SetInputSrc({})'.format(1))
            self.AX.dynamicCall('SetTrackThreshold({})'.format(1 * 10 ** (-8)))
            # SetUnitsMode needs 4 parameters: ITIAMode, fAmpPerWatt, IBNCMode, fVoltCalib
            self.AX.dynamicCall('SetUnitsMode({},{},{},{})'.format(3, 0.18, 1, 1))
        else:
            self.AX.dynamicCall('SetInputSrc({})'.format(5))

        self.AX.dynamicCall('Latch()')

    def deinitialize(self):
        """Deinitializes the NanoTrak module by stopping the control loop."""
        self.AX.dynamicCall('StopCtrl()')

    def track(self):
        """Starts tracking the signal."""
        self.AX.dynamicCall('Track()')

    def latch(self):
        """Latches the current position of the Nanotrak."""
        self.AX.dynamicCall('Latch()')
    
    def circ_position(self):
        """
        Retrieves the current horizontal and vertical position of the circle along with the signal strength.
        
        :return: A tuple containing the horizontal position (0.0 to 10.0 NT units), vertical position (0.0 to 10.0 NT units), and signal strength at the current position, as displayed on the GUI panel.
        :rtype: tuple
        """
        results = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # (pfHorzPos, pfVertPos, pfAbsReading, plRange, pfRelReading , plUnderOverRead
        self.AX.dynamicCall('GetCircPosReading(float&, float&, float&, int&, float&, int&)', results)
        horz_pos = results[0]
        vert_pos = results[1]
        signal = results[2]
        return horz_pos, vert_pos, signal
    
    def circ_diameter(self, fDia):
        """
        Sets the diameter of the circular range for tracking.
        
        :param fDia: The diameter of the circular range in NT units.
        :type fDia: float
        """
        fDia = np.float32(fDia)
        self.AX.dynamicCall('SetCircDia({})'.format(fDia))

    def move_nanotrak(self, horz_pos, vert_pos):
        """
        Moves the Nanotrak to the specified position.
        
        :param vert_pos: The vertical position to move to in NT units (0.0 to 10.0 NT units).
        :type vert_pos: float
        :param horz_pos: The horizontal position to move to in NT units (0.0 to 10.0 NT units).
        :type horz_pos: float
        """
        self.AX.dynamicCall('SetCircHomePos({},{})'.format(horz_pos, vert_pos))
        self.AX.dynamicCall('MoveCircHome()')

class ThorlabsMotor:
    def __init__(self, AX, HWSerialNum: int, IChanID: int, fMinVel: float, fAccn: float, fMaxVel: float, fStepSize: float, fMinPos: float, fMaxPos: float, IUnits: int, fPitch: float, IDirSense: int, IRewLimSwitch: int, IFwdLimSwitch: int):
        self.AX = AX
        self.HWSerialNum = HWSerialNum
        self.IChanID = IChanID
        self.fMinVel = np.float32(fMinVel)
        self.fAccn = np.float32(fAccn)
        self.fMaxVel = np.float32(fMaxVel)
        self.fStepSize = np.float32(fStepSize)
        self.fMinPos = np.float32(fMinPos)
        self.fMaxPos = np.float32(fMaxPos)
        self.IUnits = IUnits
        self.fPitch = np.float32(fPitch)
        self.IDirSense = IDirSense
        self.IRewLimSwitch = IRewLimSwitch
        self.IFwdLimSwitch = IFwdLimSwitch

    def initialize(self):
        """
        Initializes the hardware channel with specified parameters.
        This method configures the hardware channel by setting its serial number, disabling the channel temporarily, 
        setting velocity parameters, jog step size, and stage axis information. Finally, it re-enables the channel.
        """
        self.AX.setProperty('HWSerialNum', self.HWSerialNum)
        self.AX.dynamicCall('StartCtrl()')
        self.AX.dynamicCall('DisableHWChannel({})'.format(self.IChanID))
        self.AX.dynamicCall('SetVelParams({},{},{},{})'.format(self.IChanID, self.fMinVel, self.fAccn, self.fMaxVel))
        self.AX.dynamicCall('SetJogStepSize({},{})'.format(self.IChanID, self.fStepSize))
        self.AX.dynamicCall('SetStageAxisInfo({},{},{},{},{},{})'.format(self.IChanID, self.fMinPos, self.fMaxPos, self.IUnits, self.fPitch, self.IDirSense))
        self.AX.dynamicCall('SetHWLimSwitches({},{},{})'.format(self.IChanID, self.IRewLimSwitch, self.IFwdLimSwitch))
        self.AX.dynamicCall('EnableHWChannel({})'.format(self.IChanID))

    def deinitialize(self):
        """Deinitializes the motor module by stopping the control loop."""
        self.AX.dynamicCall('StopCtrl()')
    
    def deinitialize_motor(self):
        """Deinitializes the motor channel by disabling it."""
        self.AX.dynamicCall('DisableHWChannel({})'.format(self.IChanID))

    def move_relative(self, distance: float):
        """
        Moves the motor by the specified distance.
        
        :param distance: The distance to move the motor in the current units.
        :type distance: float
        """
        self.AX.dynamicCall('SetRelMoveDist({},{})'.format(self.IChanID, distance))
        self.AX.dynamicCall('MoveRelative({}, False)'.format(self.IChanID))

    def check_motor_status(self):
        """Checks the status of the motor. Returns the status bits."""
        status_bits = [self.IChanID, 0] 
        self.AX.dynamicCall('LLGetStatusBits(int&, int&)', status_bits)
        return status_bits[1]
    
    def is_moving(self):
        """
        Checks if the motor is moving by bitwise comparison.
        
        :return: True if the motor is moving, False otherwise.
        :rtype: bool
        """
        moving_cw = 0x00000010
        moving_ccw = 0x00000020
        status_bits = self.check_motor_status()
        if (status_bits & moving_cw == moving_cw) or (status_bits & moving_ccw == moving_ccw):
            return True
        else: return False

    def motor_position(self):
        """
        Returns the current position of the motor.
        
        :return: The current position of the motor.
        :rtype: float
        """
        position = [self.IChanID, 0.0]
        self.AX.dynamicCall('GetPosition(int&, float&)', position)
        return position[1]
      
    def home(self):
        self.AX.dynamicCall('MoveHome()')
