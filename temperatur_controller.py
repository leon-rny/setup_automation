import pyvisa as visa
import time

rm = visa.ResourceManager()

class ThorlabsITC4005:
    def __init__(self, usb_add, timeout=5000):
        self._usb = str(usb_add)
        self.rm = visa.ResourceManager()
        self.unit = self.rm.open_resource(self._usb)
        self.unit.timeout = timeout

    def write(self, input_):
        """
        Writes to TEC.
        
        :param input_: str
        """
        self.unit.write(f"{input_}")

    def query(self, input_):
        """
        Query to TEC.

        :param input_: str
        """
        return self.unit.query(f"{input_}")
    
    def read(self, input_ = ""):
        """
        Read from TEC
        :param input_: str
        """
        return self.unit.read()
    
    def measure_temp(self):
        """
        Measure temperature.

        :return: TEC temperature reading in degrees C
        :rtype: float
        """
        return self.query(f"MEAS:TEMP?")
    
    def set_temp_lim(self, low = 20, high = 50):
        """
        Sets temperature limit.

        :param low: low temperature limit
        :type low: float
        :param high: high temperature limit
        :type high: float
        """
        self.write(f"SOUR2:TEMP:LIM:LOW {low};HIGH {high}")

    def set_temp(self, temp=25):
        """
        Set temperature of TEC.

        :param temp: temperature in degrees C
        :type temp: float
        """
        self.write(f"SOUR2:TEMP {temp}")
        
    
if __name__ == '__main__':
    resources = rm.list_resources()
    print(f'--------------\nAvailable resources: {resources}\n--------------')
    tec = ThorlabsITC4005("USB0::4883::32842::M00934166")
    tec.set_temp(25)
    temp_diff = 1
    while temp_diff > 0.01:
        temp = float(tec.measure_temp())
        print(f"Current temperature: {temp}")
        temp_diff = abs(40 - temp)
        time.sleep(1)
