import pyvisa
import warnings

warnings.filterwarnings("ignore", message="mkl-service package failed to import")

class KeysightN7734A:
    def __init__(self, address):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(f'TCPIP0::{address}::inst0::INSTR')

    def set_routing(self, route, slot=1):
        """
        Sets the routing for a specific channel.

        :param: route: The routing to be set.
        :type route: str
        :param slot: The slot of the switch module.
        :type slot: int
        """
        command = f':ROUTe{slot} {route}'
        self.instrument.write(command)
        
    def get_config(self, slot=1):
        """
        Returns the current configuration of the switch for a specific channel.
        
        slot: The slot of the switch module.
        :type slot: int
        :return: The current configuration of the switch.
        :rtype: str
        """
        command = f':ROUTe{slot}?'
        response = self.instrument.query(command)
        return response