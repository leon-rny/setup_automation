import pyvisa
import time

rm = pyvisa.ResourceManager()

class Keithley2400:
    """
    This class represents the Keithley 2400 Sourcemeter.
    """
    def __init__(self, gpib_add, compliance_voltage=4):
        """
        Initialize Keithley with given GPIB address.

        :param gpib_add: The GPIB address of the Keithley.
        :type gpib_add: int
        """
        self._gpib = str(gpib_add)
        self.unit = rm.open_resource(f"GPIB1::{self._gpib}::INSTR")
        self.unit.write("*RST")
        self.unit.write("*CLS")
        self.unit.write(":SOUR:FUNC CURR")
        self.unit.write(f":SENS:VOLT:PROT {compliance_voltage}")

    def write(self, command):
        """
        Send a command to the Keithley.

        :param command: The command to send.
        :type command: str
        """
        self.unit.write(command)

    def query(self, command):
        """
        Send a query to the Keithley and return the response.

        param command: The query to send.
        :type command: str
        """
        return self.unit.query(command)

    def measure_voltage(self):
        """
        Measure and return the voltage.

        :return: The measured voltage.
        :rtype: float
        """
        self.write(":SENS:FUNC 'VOLT:DC'")
        self.write(":FORM:ELEM VOLT")
        return self.query(":READ?")

    def measure_current(self):
        """
        Measure and return the current.
        
        :return: The measured current.
        :rtype: float
        """
        self.write(":SENS:FUNC 'CURR:DC'")
        self.write(":FORM:ELEM CURR")
        return self.query(":READ?")
    
    def measure_power(self):
        """
        Measure and return the power.

        :return: The measured power.
        :rtype: float
        """
        self.write(":SYSTem:KEY 5")
        return self.query(":READ?")

    def set_voltage(self, voltage):
        """
        Set the source voltage.

        :param voltage: The voltage to set.
        :type voltage: float
        """
        self.write(f":SOUR:FUNC VOLT")
        self.write(f":SOUR:VOLT {voltage}")
        self.write(":OUTP ON")

    def set_current(self, current):
        """
        Set the source current.
        
        :param current: The current to set.
        :type current: float
        """
        self.write(f":SOUR:FUNC CURR")
        self.write(f":SOUR:CURR {current}")
        self.write(":OUTP ON")

    def turn_off(self):
        """Turn off the output."""
        self.write(":OUTP OFF")
        self.write("*RST")

    def close(self):
        """Close the connection to the instrument."""
        self.unit.close()


print('available resources:', rm.list_resources())
keithley = Keithley2400(26, compliance_voltage=15)

liste = [0.0, 15.434872662825796, 21.82820625326997, 26.733983660370207, 30.869745325651593, 34.51342449813167, 37.807562268756264, 40.836834583786356, 43.65641250653994, 46.30461798847739, 48.809353009197636, 51.19168130950689, 53.467967320740414, 55.65122481607581, 57.75200531277731, 59.77900477395643, 61.739490651303186, 63.63961030678928, 65.4846187598099, 67.27905014367619, 69.02684899626334, 70.73147231940382, 72.39596998858593, 74.0230488746977, 75.61512453751253, 77.17436331412898, 78.70271689756855, 80.20195098111061, 81.67366916757271, 83.1193330664519, 84.54027929649519, 85.93773395690079, 87.31282501307987, 88.66659295294002, 90.0]

keithley.set_current(80.20195098111061*1e-3)
keithley.measure_power()

# for i in liste:
#     keithley.set_current(i*1e-3)
#     keithley.measure_power()
#     time.sleep(3)


