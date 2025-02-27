import pyvisa

class OwisHumes100:
    def __init__(self, usb_add):
        self.rm = pyvisa.ResourceManager()
        self._usb = str(usb_add)
        self.instrument = self.rm.open_resource(self._usb, read_termination='\r', write_termination='\r\n')    

        
    def write(self, command):
        """Send a command to the instrument."""
        self.instrument.write(command)

    def read(self):
        """Read the response from the instrument."""
        response = self.instrument.read()
        return response
    
    def query(self, command):
        """Send a query to the instrument."""
        response = self.instrument.query(command)
        return response

    def initialize(self):
        self.write('TERM=0')
        self.write('INIT1')
    
    def move_relative(self, distance):
        """Move the motor by a relative distance."""
        self.write(f'PSET1={distance}')
        self.write('PGO1')

    def reference(self):
        self.write('REF1=6')
    
if __name__ == '__main__':
    owis = OwisHumes100('ASRL9::INSTR')
    owis.move_relative(1000)
