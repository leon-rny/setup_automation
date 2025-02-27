import numpy as np
import time
from datetime import datetime
import pyvisa as visa


class EXFOCTP10:
    """ 
    Class for controlling the EXFO CTP10 tunable laser source.
    """
    EOL = '\r\n'
    Timeout = 5

    def __init__(self, IP: str, Port: int, Module: int, Channel: int, Trace_Type: int, Start_WL=None, Stop_WL=None, Sampling=None, Laser_Speed=None, Laser_Power=None):
        self.IP = IP
        self.Port = Port
        self.Module = Module
        self.Channel = Channel
        self.Trace_Type = Trace_Type
        self.Start_WL = Start_WL
        self.Stop_WL = Stop_WL
        self.Sampling = Sampling
        self.Laser_Speed = Laser_Speed
        self.Laser_Power = Laser_Power
        self.resource = f"TCPIP0::{self.IP}::{self.Port}::SOCKET"
        self.connect()

    def connect(self):
        """Connects to the device."""
        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(self.resource)
        self.inst.timeout = self.Timeout * 1000
        self.inst.read_termination = self.EOL
        self.inst.write_termination = self.EOL

    def close(self):
        """Closes the connection to the device."""
        self.inst.close()

    def query(self, command: str):
        """Sends a command and returns the response."""
        response = self.inst.query(command)
        return response

    def send(self, command: str):
        """Sends the command to the device."""
        self.inst.write(command)
        
    def read_until_crlf(self):
        """Reads a non-binary response from the device."""
        response = self.inst.read()
        return response

    # Angepasste EXFO-spezifische Methoden
    def query_condition_register(self):
        """Queries the operation status of the CTP10."""
        response = int(self.query(':STAT:OPER:COND?'))
        return response

    def clear_error_queue(self):
        """Deletes the error queue of the CTP10."""
        self.send('*CLS')

    def query_error_queue(self):
        """Queries the first element of the error queue."""
        response = self.query(':SYST:ERR?')
        Error = response.split(',')
        error_code = int(Error[0])
        error_name = Error[1]
        return error_code, error_name

    def clear_trace_queue(self):
        """Deletes the trace queue."""
        self.send('CLE')

    def wait_for_condition(self, condition_number=0, timeout=30.0):
        """Waits until a certain condition is met or a timeout occurs."""
        time_start = time.time()
        while True:
            time.sleep(0.02)
            condition = self.query_condition_register()
            if condition == condition_number:
                return 0, 'NO ERROR'
            if time.time() - time_start > timeout:
                return -1, 'TIMEOUT ERROR WAITING FOR CONDITION'

    def set_scan_parameters(self, start_wav: float, stop_wav: float, sampling: int, speed: int, laser_power: float):
        """Sets the scan parameters of the CTP10."""
        self.send(f':INIT:WAV:STAR {start_wav:.3f}NM')
        self.send(f':INIT:WAV:STOP {stop_wav:.3f}NM')
        self.send(f':INIT:WAV:SAMP {sampling}PM')
        self.send(f':INIT:TLS1:SPE {speed}')
        self.send(f':INIT:TLS1:POW {laser_power:.2f}DBM')
        self.send(':INIT:STAB ON')
        self.send(':INIT:SMOD SING')

    def perform_scan(self, timeout=60.0):
        """Starts a sweep scan and waits until it is complete."""
        self.clear_error_queue()
        self.send(':INIT')
        error_code, error_name = self.wait_for_condition(condition_number=0, timeout=timeout)
        if error_code == 0:
            error_code, error_name = self.query_error_queue()
        self.send('INIT:FBC:SENS 1')
        self.send('CTP:RLAS1:WAV 1550NM')
        return error_code, error_name

    def create_wavelength_array(self):
        """Creates the wavelength array based on the passed parameters."""
        Query_start_wav = f':TRAC:SENS{self.Module}:CHAN{self.Channel}:TYPE{self.Trace_Type}:DATA:STAR?'
        L_start = self.query(Query_start_wav)
        L_start = float(L_start) * 1E9  # in nm

        Query_sampling = f':TRAC:SENS{self.Module}:CHAN{self.Channel}:TYPE{self.Trace_Type}:DATA:SAMP?'
        Sampling = self.query(Query_sampling)
        Sampling = float(Sampling) * 1E12  # in pm

        Query_length = f':TRAC:SENS{self.Module}:CHAN{self.Channel}:TYPE{self.Trace_Type}:DATA:LENG?'
        Length = self.query(Query_length)
        Length = int(Length)

        L_stop = L_start + Sampling * (Length - 1) / 1000  # Stop wavelength in nm
        Wavelength_array = np.linspace(L_start, L_stop, Length)
        return Wavelength_array

    def retrieve_ASCii_trace(self):
        """Retrieves the trace array in ASCII format."""
        Query_data = f':TRAC:SENS{self.Module}:CHAN{self.Channel}:TYPE{self.Trace_Type}:DATA? 0,DB'
        self.send(Query_data)
        Trace_array = self.retrieve_ASCii_response()
        return Trace_array

    def retrieve_ASCii_response(self):
        """Retrieves an ASCII response."""
        D = self.read_until_crlf()
        array = D.split(',')
        return_array = [float(element) for element in array]
        return return_array

    def save_measurement_data(self, wavelength_array, il_data, Sampling, Laser_Speed, Laser_Power, save_path, filename):
        """Saves the measurement data in a text file."""
        data = {
            'Wavelength [nm]': wavelength_array,
            'IL [dBm]': il_data
        }
        combined_array = np.column_stack([v for k, v in data.items()])
        col_headers = '\t'.join(data.keys())
        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        header = [
            'EXFO CTP10',
            f'{now}',
            f'Start-Wavelength: {wavelength_array[0]}nm',
            f'Stop-Wavelength: {wavelength_array[-1]}nm',
            f'Sampling-Resolution: {Sampling}pm',
            f'Laser-Sweep-Speed: {Laser_Speed}nm/s',
            f'Laser-Power: {Laser_Power}dBm',
            '########################\n'
        ]
        header = '\n'.join(header + [col_headers])
        full_path = f'{save_path}/{filename}_{now}.txt'
        np.savetxt(full_path, combined_array, fmt='%.4f', delimiter='\t', header=header, comments='')


if __name__ == "__main__":
    rm = visa.ResourceManager()
    print(rm.list_resources())
    device = EXFOCTP10(IP="192.168.254.10", Port=5025, Module=3, Channel=1, Trace_Type=11)

    try:
        # Verbinde mit dem Gerät und hole die ID ab
        IDN = device.query('*IDN?')
        print("Device IDN:", IDN)

        # Lösche die Trace-Queue
        device.clear_trace_queue()

        # Setze die Scan-Parameter
        print('Setting scan parameters...')
        device.set_scan_parameters(start_wav=1300.0, stop_wav=1600.0, sampling=250, speed=100, laser_power=0)

        # Führe den Scan durch und prüfe auf Fehler
        error_code, error_name = device.perform_scan(timeout=60.0)
        if error_code == 0:
            print('Retrieving trace data...')
            
            # Erstelle das Wellenlängenarray und rufe die IL-Daten ab
            wavelength_array = device.create_wavelength_array()
            il_data = device.retrieve_ASCii_trace()
            print(il_data)
            
            print("Trace data retrieved successfully.")
        else:
            print(f"Scan failed with error code {error_code}: {error_name}")
        
        # Speichere die Messdaten
        device.save_measurement_data(
            wavelength_array, 
            il_data, 
            Sampling=1, 
            Laser_Speed=2, 
            Laser_Power=3, 
            save_path=r'\\hhi.de\abteilung\PC\PC-POL\user\Polygroup\Students-Meeting\All_DF\Neymeyer\BA\03_Messautomatisierung\setup', 
            filename='measurement'
        )

    finally:
        # Stelle sicher, dass die Verbindung zum Gerät geschlossen wird
        device.close()

