import numpy as np
from datetime import datetime
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
from scipy.optimize import curve_fit
import json

class LoopWorker(QObject):
    """Worker class for the loop function. This class is used to perform the loop function in a separate thread."""
    
    update_status = pyqtSignal(str)
    finished = pyqtSignal()
    measurement_completed = pyqtSignal(np.ndarray, np.ndarray)
    coupling_measurement_completed = pyqtSignal(np.ndarray, np.ndarray, str, np.ndarray, np.ndarray)
    motor_offset_completed = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)

    def __init__(self, keithley, apt_tab, exfo_device, lower_optical_switch, upper_optical_switch, temp_controller, min_current, max_current, steps_current, temp_setpoint, start_wavelength, stop_wavelength, sampling, laser_power, scan_speed, save_path, filename, switch_settings, input_waveguide_distance, output_waveguide_distance, chip_distance, number_of_chips, inputs_per_chip, outputs_per_chip, coupling_threshold, gaus_min, gaus_max, scan_type):
        super().__init__()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_event = threading.Event()

        # Devices
        self.keithley = keithley

        self.apt_tab = apt_tab 

        self.exfo_device = exfo_device

        self.lower_optical_switch = lower_optical_switch
        self.upper_optical_switch = upper_optical_switch

        self.temp_controller = temp_controller
        self.temp_setpoint = temp_setpoint

        # Parameters
        self.min_current = min_current
        self.max_current = max_current
        self.steps_current = int(steps_current)
        # self.current = self.current_square(self.min_current, self.max_current, self.steps_current)
        self.current = np.array([80.20195098111061, 81.67366916757271, 83.1193330664519, 84.54027929649519, 85.93773395690079, 87.31282501307987, 88.66659295294002, 90.0])
        self.current = self.current * 1e-3
        self.voltage = [0]
        self.measured_power = [0]
        # self.current = np.linspace(self.min_current, self.max_current, self.steps_current)

        self.start_wavelength = start_wavelength
        self.stop_wavelength = stop_wavelength
        self.sampling = sampling
        self.laser_power = laser_power
        self.scan_speed = scan_speed
        self.save_path = save_path
        self.filename = filename

        self.switch_settings = switch_settings

        self.input_waveguide_distance = input_waveguide_distance
        self.output_waveguide_distance = output_waveguide_distance
        self.chip_distance = chip_distance
        self.number_of_chips = number_of_chips
        self.inputs_per_chip = inputs_per_chip
        self.outputs_per_chip = outputs_per_chip

        self.coupling_threshold = coupling_threshold
        self.gaus_min = gaus_min
        self.gaus_max = gaus_max
        self.scan_type = scan_type

        self.power_array = []
        self.power_array_linear = []
        self.fitted_power_array = []
        self.popt = []
        
        self.input_motor_position = [0.0]
        self.output_motor_position = [0.0]
        self.input_horz_offset_tracking = [0.0]
        self.input_vert_offset_tracking = [0.0]
        self.output_horz_offset_tracking = [0.0]
        self.output_vert_offset_tracking = [0.0]
        self.focus_horz_offset_tracking = [0.0]
        self.focus_vert_offset_tracking = [0.0]

    def pause_loop(self):
        self.pause_event.clear()
        self.pause_event.wait()

    def continue_loop(self):
        self.pause_event.set()

    def stop_loop(self):
       self.stop_event.set()

    def start_loop(self):
        self.temp_controller.set_temp(self.temp_setpoint)
        self.check_temp()
        for i in self.current:
            if self.stop_event.is_set(): break
            self.keithley.set_current(i)
            self.update_status.emit(f"Set current: {format(i, '.4f')}A")
            time.sleep(20)
            # self.voltage.append(self.keithley.measure_voltage())
            self.measured_power.append(self.keithley.measure_power())
            self.check_temp()
            self.pause_event.wait()
            output_wg = 0

            try:
                if self.stop_event.is_set(): break
                if not self.confirm_coupling(self.scan_type): self.pause_loop()                   
        
                wavelength_array_te, il_data_te = self.perform_scan("TE")
                wavelength_array_tm, il_data_tm = self.perform_scan("TM")

                self.save_measurement_data(wavelength_array_te, il_data_te, il_data_tm, output_wg, current=i)
                
                output_waveguide_startposition = self.apt_tab.MotorOUT.motor_position()
                skip_first_iteration = False
                for j in range(self.number_of_chips):
                    self.pause_event.wait()
                    if self.stop_event.is_set(): break
                    if j != 0:
                        self.move_motors("both", self.chip_distance) # TODO change to output
                        skip_first_iteration = True
                    
                    for k in range(self.outputs_per_chip):
                        output_wg += 1
                        self.pause_event.wait()
                        if self.stop_event.is_set(): break
                        if k == 0 and j == 0:
                            self.move_motors("both", self.output_waveguide_distance) # TODO change to output
                        elif k == 3 and j == 0:
                            continue
                        elif skip_first_iteration:
                            skip_first_iteration = False
                        else:
                            self.move_motors("both", self.output_waveguide_distance) # TODO change to output
                        # self.upper_optical_switch.set_routing(f'A,12')
                        if not self.tracking(): self.pause_loop()
                        counter = 0
                        while not self.confirm_coupling():
                            self.pause_loop()
                            counter += 1
                            if counter == 2:
                                break
                        self.motor_offset()
                        if self.stop_event.is_set(): break

                        wavelength_array_te, il_data_te = self.perform_scan("TE")
                        wavelength_array_tm, il_data_tm = self.perform_scan("TM")
                        self.save_measurement_data(wavelength_array_te, il_data_te, il_data_tm, output_wg, current=i)
                
                if self.stop_event.is_set(): break
                output_waveguide_endposition = self.apt_tab.MotorOUT.motor_position()
                to_start_waveguide = abs(output_waveguide_startposition - output_waveguide_endposition)
                self.move_motors("both", -to_start_waveguide)
                # self.upper_optical_switch.set_routing(f'A,12')
                if not self.tracking(): self.pause_loop()
                
            except Exception as e:
                self.update_status.emit(f"An error occurred in the loop: {e}")

        self.keithley.set_current(0)
        self.update_status.emit("Loop finished.")
        self.finished.emit()
    
    def confirm_coupling(self, scan_type='1D'):
        """
        Confirm the coupling of the fiber to the chip by scanning the power at different positions.
        
        :param scan_type: Type of scan, either '1D' or '2D'
        :type scan_type: str
        :return: True if the coupling was successful, False if not
        :rtype: bool
        """
        horz_pos_input, vert_pos_input, _ = self.apt_tab.InputNT.circ_position()
        volt_array = []
        x_pos_array = []
        y_pos_array = []
        scan_range = 21
        if self.scan_type == '1D':
            # 1D scan (horizontal)
            for i in range(scan_range):
                self.apt_tab.InputNT.move_nanotrak(i/2, vert_pos_input)
                time.sleep(0.1) # Wait for the nanotrak to move
                _, _, current_power = self.apt_tab.InputNT.circ_position()
                volt_array.append(current_power)
        
        elif self.scan_type == '2D':
            # 2D scan (horizontal and vertical)
            for i in range(scan_range):
                for j in range(scan_range):
                    self.apt_tab.InputNT.move_nanotrak(i/2, j/2)
                    if j == 0:
                        time.sleep(0.25)
                    else:
                        time.sleep(0.1) 
                    x_pos_array.append(i/2)
                    y_pos_array.append(j/2)
                    _, _, current_power = self.apt_tab.InputNT.circ_position()  
                    volt_array.append(current_power)

        self.apt_tab.InputNT.move_nanotrak(horz_pos_input, vert_pos_input)

        # Convert the voltage to dBm: dBm = ((V - max_current) * Faktor_exfo) - Offset_exfo
        self.power_array = ((np.array(volt_array) - 3.5) * 22.17647059) - 20.1
        self.power_array_linear = 10**(self.power_array/10)

        if self.scan_type == '2D':
            self.power_array_toemit = self.power_array.reshape(scan_range, scan_range)
            x = np.array(x_pos_array)
            y = np.array(y_pos_array)
            xy_array = np.column_stack((x, y))
            initial_guess = [np.max(self.power_array_linear), np.mean(x), np.mean(y), 3, 3, 0, np.min(self.power_array_linear)]
            try:
                self.popt, self.pcov = curve_fit(self.gaus_2d, xy_array, self.power_array_linear.ravel(), p0=initial_guess)
                self.fitted_power_array_2d = self.gaus_2d(xy_array, *self.popt).reshape(scan_range, scan_range)
                self.power_array_linear_2d = self.power_array_linear.reshape(scan_range, scan_range)
                json.dump(self.fitted_power_array_2d.tolist(), open('fitted_power_array_2d.json', 'w'))
                json.dump(self.power_array_linear_2d.tolist(), open('power_array_linear_2d.json', 'w'))
                json.dump(self.power_array_toemit.tolist(), open('power_array_toemit.json', 'w'))
                self.coupling_measurement_completed.emit(self.power_array_toemit, self.fitted_power_array_2d, '2D', x, y)

                if self.gaus_min < self.popt[1] < self.gaus_max and self.gaus_min < self.popt[2] < self.gaus_max:
                    self.update_status.emit("Coupling successful.")
                    return True
                else:
                    self.update_status.emit("Adjust manually.")
                    self.update_status.emit("Loop paused.")
                    return False

            except Exception as e:
                self.update_status.emit(f"Error during 2D scan fitting: {e}")
                self.update_status.emit("Adjust manually.")
                self.update_status.emit("Loop paused.")
                return False
            
        else:
            # Fit 1D data
            x = np.arange(0, 10.5, 0.5)
            try:
                self.popt, self.pcov = curve_fit(self.gaus, x, self.power_array_linear,  p0 = [0.01, 5, 4]) # popt = Optimal parameters for the function, pcov = Covariance of the parameters
                x_fine = np.arange(0, 10.5, 0.01) # TODO test or delete
                self.fitted_power_array = self.gaus(x_fine,*self.popt)
                self.fitted_power_array = np.array(self.fitted_power_array)
                self.coupling_measurement_completed.emit(self.power_array_linear, self.fitted_power_array, '1D', np.array([]), np.array([]))
                if self.gaus_min < abs(self.popt[2]) < self.gaus_max:
                    self.update_status.emit("Coupling successful.")
                    return True  
                else:
                    self.update_status.emit("Adjust manually.")
                    self.update_status.emit("Loop paused.")
                    return False
            except Exception as e:
                self.update_status.emit(f"{e}")
                self.update_status.emit("Adjust manually.")
                self.update_status.emit("Loop paused.")
                return False

    def gaus(self, x, a, x0, sigma):
        """
        Gaussian function for fitting the power array.
        
        :param x: The x values
        :type x: np.ndarray
        :param a: The amplitude of the Gaussian function
        :type a: float
        :param x0: The mean of the Gaussian function
        :type x0: float
        :param sigma: The standard deviation of the Gaussian function
        :type sigma: float
        :return: The Gaussian function
        :rtype: np.ndarray
        """
        return a*np.exp(-(x-x0)**2/(2*sigma**2))

    def gaus_2d(self, XY, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
        x, y = XY[:,0], XY[:,1]
        xo = float(xo)
        yo = float(yo)
        a = (np.cos(theta)**2) / (2 * sigma_x**2) + (np.sin(theta)**2) / (2 * sigma_y**2)
        b = -(np.sin(2 * theta)) / (4 * sigma_x**2) + (np.sin(2 * theta)) / (4 * sigma_y**2)
        c = (np.sin(theta)**2) / (2 * sigma_x**2) + (np.cos(theta)**2) / (2 * sigma_y**2)
        
        g = offset + amplitude * np.exp(- (a * ((x - xo)**2) + 2 * b * (x - xo) * (y - yo) + c * ((y - yo)**2)))
        return g.ravel()

    def perform_scan(self, polarization_type):
        """
        Perform a scan with the EXFO device and return the wavelength array and the IL data.
        
        :param polarization_type: The polarization type to scan. Can be "TE" or "TM"
        :type polarization_type: str
        :return: The wavelength array and the IL data
        :rtype: tuple
        """
        lower = self.switch_settings[2][f"switch_1500_1630_{polarization_type}"][0]
        upper = self.switch_settings[2][f"switch_1500_1630_{polarization_type}"][1]
        self.lower_optical_switch.set_routing(f'A,{lower}')
        self.upper_optical_switch.set_routing(f'A,{upper}')
        self.update_status.emit(f"Switch settings: {polarization_type} Lower {lower}, Upper {upper}")

        self.update_status.emit("Scanning...")
        self.exfo_device.clear_trace_queue()
        self.exfo_device.set_scan_parameters(
            start_wav=self.start_wavelength, 
            stop_wav=self.stop_wavelength, 
            sampling=self.sampling, 
            speed=self.scan_speed, 
            laser_power=self.laser_power
        )
        
        error_code, error_name = self.exfo_device.perform_scan()

        while error_code != 0:
            self.update_status.emit(f"Scan failed with error code {error_code}: {error_name}")
            self.update_status.emit("Scan again...")
            
            self.exfo_device.clear_trace_queue()
            self.exfo_device.set_scan_parameters(
                start_wav=self.start_wavelength, 
                stop_wav=self.stop_wavelength, 
                sampling=self.sampling, 
                speed=self.scan_speed, 
                laser_power=self.laser_power
            )
            error_code, error_name = self.exfo_device.perform_scan()
        
        if error_code == 0:
            self.update_status.emit("Scan completed successfully.")
            wavelength_array = self.exfo_device.create_wavelength_array()
            il_data = self.exfo_device.retrieve_ASCii_trace()
            self.measurement_completed.emit(np.array(wavelength_array), np.array(il_data))
        
        return wavelength_array, il_data

    def save_measurement_data(self, wavelength_array_te, il_data_te, il_data_tm, output_wg, current=0.0):
        """
        Save the measurement data to a JSON file.
        
        :param wavelength_array_te: The wavelength array for the TE mode
        :type wavelength_array_te: list
        :param il_data_te: The IL data for the TE mode
        :type il_data_te: list
        :param il_data_tm: The IL data for the TM mode
        :type il_data_tm: list
        """
        # if output_wg >= 4:
        #     output_wg -= 1

        if type(self.popt) == np.ndarray:
            self.popt = self.popt.tolist()
        if type(self.power_array) == np.ndarray:
            self.power_array = self.power_array.tolist()
        if type(self.fitted_power_array) == np.ndarray:
            self.fitted_power_array = self.fitted_power_array.tolist()

        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        data = {
            'metadata': {
                'measurement_time': now,
                'start_wavelength_nm': wavelength_array_te[0],
                'stop_wavelength_nm': wavelength_array_te[-1],
                'sampling_resolution_pm': self.sampling,
                'laser_sweep_speed_nm_per_s': self.scan_speed,
                'laser_power_dbm': self.laser_power,
                'gaussian_fit_params': self.popt, 
                'sampled_power_output': self.power_array,  
                'fitted_power_output': self.fitted_power_array, 
                'currents_a': current,
                # 'voltage_v': self.voltage,
                'measured_power_dbm': self.measured_power
            },
            'data': {
                'wavelength_nm': wavelength_array_te.tolist(),  
                'il_te_db': il_data_te, 
                'il_tm_db': il_data_tm 
            }
        }
        
        # File naming
        current_tmp = format(current, '.6f')
        name = f'output_{output_wg}_current_{current_tmp}A'
        full_path = f'{self.save_path}/{now}_{name}.json'
        
        # Save as JSON
        with open(full_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        
        self.update_status.emit(f"Data saved to {full_path}")

    def move_motors(self, motor, distance):
        """
        Move the motors to the specified distance and append the motor positions to the motor position arrays.
        
        :param motor: The motor to move. Can be "input", "output" or "both"
        :type motor: str
        """
        if motor == "output":
            self.apt_tab.MotorOUT.move_relative(distance)
            self.update_status.emit('Output motor is moving...')
            while self.apt_tab.MotorOUT.is_moving():
                time.sleep(0.1)
            self.update_status.emit('Output motor stopped.')
            self.output_motor_position.append(self.apt_tab.MotorOUT.motor_position())

        elif motor == "input":
            self.apt_tab.MotorIN.move_relative, args=(distance)
            self.update_status.emit('Input motor is moving...')
            while self.apt_tab.MotorIN.is_moving():
                time.sleep(0.1)
            self.update_status.emit('Input motor stopped.')
            self.input_motor_position.append(self.apt_tab.MotorIN.motor_position)

        else:
            motor_input_thread = threading.Thread(target=self.apt_tab.MotorIN.move_relative, args=(self.input_waveguide_distance,))
            motor_output_thread = threading.Thread(target=self.apt_tab.MotorOUT.move_relative, args=(distance,))
            motor_input_thread.start()
            motor_output_thread.start()
            self.update_status.emit('Motors are moving...')
            while self.apt_tab.MotorIN.is_moving() or self.apt_tab.MotorOUT.is_moving():
                time.sleep(0.1)
            motor_input_thread.join()
            motor_output_thread.join()
            self.update_status.emit('Motors stopped')
            self.input_motor_position.append(self.apt_tab.MotorIN.motor_position())
            self.output_motor_position.append(self.apt_tab.MotorOUT.motor_position())

    def tracking(self):
        """
        Track the fiber to the chip by moving the nanotrak and perform a latch. Calculate the offset of the motors.
        
        :return: True if the tracking was successful, False if not
        :rtype: bool
        """
        input_horz_pos_before, input_vert_pos_before, _ = self.apt_tab.InputNT.circ_position()
        output_horz_pos_before, output_vert_pos_before, _ = self.apt_tab.OutputNT.circ_position()
        focus_horz_pos_before, focus_vert_pos_before, _ = self.apt_tab.FocusNT.circ_position()

        self.update_status.emit("Tracking...")
        self.apt_tab.change_circ_diameter_all(1)  
        self.apt_tab.track_all()
        time.sleep(3.75)
        self.apt_tab.change_circ_diameter_all(0.75)  
        time.sleep(3.75)
        self.apt_tab.change_circ_diameter_all(0.25)
        time.sleep(5)
        self.apt_tab.latch_all()
        self.update_status.emit("Latched.")

        input_horz_pos_after, input_vert_pos_after, _ = self.apt_tab.InputNT.circ_position()
        output_horz_pos_after, output_vert_pos_after ,_ = self.apt_tab.OutputNT.circ_position()
        focus_horz_pos_after, focus_vert_pos_after, _ = self.apt_tab.FocusNT.circ_position()

        self.input_horz_offset_tracking.append(input_horz_pos_before - input_horz_pos_after)
        self.input_vert_offset_tracking.append(input_vert_pos_before - input_vert_pos_after)
        self.output_horz_offset_tracking.append(output_horz_pos_before - output_horz_pos_after)
        self.output_vert_offset_tracking.append(output_vert_pos_before - output_vert_pos_after)
        self.focus_horz_offset_tracking.append(focus_horz_pos_before - focus_horz_pos_after)
        self.focus_vert_offset_tracking.append(focus_vert_pos_before - focus_vert_pos_after)

        if self.apt_tab.get_circ_position_all() == False:
            self.update_status.emit("Adjust manually.")
            self.update_status.emit("Loop paused.")
            return False
        else:
            self.update_status.emit("Tracking successful.")
            return True

    def motor_offset(self):
        """Calculates the offset from nanotrak units to nm, sends the motor positions and the offset tracking to the GUI"""
        input_motor_position = np.array(self.input_motor_position)
        output_motor_position = np.array(self.output_motor_position)
        input_horz_offset_tracking = 2*np.array(self.input_horz_offset_tracking)
        input_vert_offset_tracking = 2*np.array(self.input_vert_offset_tracking)
        output_horz_offset_tracking = 2*np.array(self.output_horz_offset_tracking)
        output_vert_offset_tracking = 2*np.array(self.output_vert_offset_tracking)
        focus_horz_offset_tracking = 2*np.array(self.focus_horz_offset_tracking)
        focus_vert_offset_tracking = 2*np.array(self.focus_vert_offset_tracking)

        self.motor_offset_completed.emit(input_motor_position, output_motor_position, input_horz_offset_tracking, input_vert_offset_tracking, output_horz_offset_tracking, output_vert_offset_tracking, focus_horz_offset_tracking, focus_vert_offset_tracking)

    def check_temp(self):
        """Check the temperature of the chip and adjust the temperature controller if necessary."""
        current_temp = float(self.temp_controller.measure_temp())
        temp_diff = abs(self.temp_setpoint - current_temp)
        self.update_status.emit(f"Setting temperature to 25°C. Current temperature: {format(current_temp, '.2f')}°C")
        while temp_diff > 0.01:
            if self.stop_event.is_set(): break
            current_temp = float(self.temp_controller.measure_temp())
            temp_diff = abs(self.temp_setpoint - current_temp)
            time.sleep(10)
            self.update_status.emit(f"Current temperature: {format(current_temp, '.2f')}°C")

        self.update_status.emit("Temperature stabilized.")
    
    def current_square(self,  start_value, end_value, steps):
        norm_values = np.linspace(0, 1, steps)
        wurzel_values = np.sqrt(norm_values) * (end_value - start_value) + start_value
        return list(wurzel_values)
    
