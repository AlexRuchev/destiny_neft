import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLCDNumber, QPushButton, QLineEdit, QLabel, QFrame, QGridLayout)
from PySide6.QtCore import Qt, QTimer

import time
import minimalmodbus
import sys
import serial


class PI_PWM_Controller:

    def __init__(self, Kp, Ki, setpoint, min_pwm=0, max_pwm=100):
        self.Kp = Kp  
        self.Ki = Ki  
        self.setpoint = setpoint 
        self.min_pwm = min_pwm  
        self.max_pwm = max_pwm 
        self.integral = 0
        self.last_time = time.time()
        self.output=0

    def compute(self, heater, current_value):
        error = self.setpoint - current_value
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        P = self.Kp * error

        self.integral += self.Ki * error * dt
        self.integral = max(min(self.integral, self.max_pwm), self.min_pwm)

        output = P + self.integral

        self.output = int(max(min(output, self.max_pwm), self.min_pwm))


class DeviceData:
    def __init__(self):
        self.temperature = 20.5
        self.density = 1.225
        self.temperature_setpoint = 32.0
        self.heater_enabled = False
        self.pump_enabled = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.device = DeviceData()
        self.setWindowTitle("Управление системой")
        self.setFixedSize(850, 450)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        left_panel = QFrame()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(350)

        indicators_frame = QFrame()
        indicators_layout = QGridLayout()
        indicators_layout.setHorizontalSpacing(20)
        indicators_layout.setVerticalSpacing(10)

        self.heater_indicator = QLabel()
        self.heater_indicator.setFixedSize(24, 24)
        self.update_heater_indicator()
        heater_label = QLabel("Нагреватель:")
        heater_label.setStyleSheet("font-size: 16px;")

        self.pump_indicator = QLabel()
        self.pump_indicator.setFixedSize(24, 24)
        self.update_pump_indicator()
        pump_label = QLabel("Насос:")
        pump_label.setStyleSheet("font-size: 16px;")

        indicators_layout.addWidget(heater_label, 0, 0)
        indicators_layout.addWidget(self.heater_indicator, 0, 1)
        indicators_layout.addWidget(pump_label, 1, 0)
        indicators_layout.addWidget(self.pump_indicator, 1, 1)

        indicators_frame.setLayout(indicators_layout)
        left_layout.addWidget(indicators_frame)

        buttons_frame = QFrame()
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)

        self.heater_button = QPushButton("Включить нагреватель")
        self.heater_button.setCheckable(True)
        self.heater_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 12px 24px;
                min-width: 200px;
                background-color: #e0e0e0;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
            }
        """)
        self.heater_button.clicked.connect(self.toggle_heater)

        self.pump_button = QPushButton("Включить насос")
        self.pump_button.setCheckable(True)
        self.pump_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 12px 24px;
                min-width: 200px;
                background-color: #e0e0e0;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
            }
        """)
        self.pump_button.clicked.connect(self.toggle_pump)

        buttons_layout.addWidget(self.heater_button, 0, Qt.AlignCenter)
        buttons_layout.addWidget(self.pump_button, 0, Qt.AlignCenter)
        buttons_frame.setLayout(buttons_layout)
        left_layout.addWidget(buttons_frame)
        left_layout.addStretch()

        main_layout.addWidget(left_panel)

        right_panel = QFrame()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_panel.setLayout(right_layout)

    
        density_frame = QFrame()
        density_layout = QVBoxLayout()
        density_label = QLabel("Плотность, кг/м³")
        density_label.setAlignment(Qt.AlignCenter)
        density_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.density_lcd = QLCDNumber()
        self.density_lcd.setDigitCount(6)
        self.density_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.density_lcd.setFixedSize(250, 70)
        self.density_lcd.display(self.device.density)
        self.density_lcd.setStyleSheet("""
            QLCDNumber {
                background-color: #f0f0f0;
                color: #333;
                border: 2px solid #ccc;
                border-radius: 5px;
                qproperty-segmentStyle: Flat;
                font-size: 24px;
            }
        """)
        density_layout.addWidget(density_label)
        density_layout.addWidget(self.density_lcd, 0, Qt.AlignCenter)
        density_frame.setLayout(density_layout)
        right_layout.addWidget(density_frame)

    
        temp_frame = QFrame()
        temp_layout = QVBoxLayout()
        temp_layout.setSpacing(10)

        temp_label = QLabel("Температура, °C")
        temp_label.setAlignment(Qt.AlignCenter)
        temp_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.temp_lcd = QLCDNumber()
        self.temp_lcd.setDigitCount(6)
        self.temp_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.temp_lcd.setFixedSize(250, 70)
        self.temp_lcd.display(self.device.temperature)
        self.temp_lcd.setStyleSheet("""
            QLCDNumber {
                background-color: #f0f0f0;
                color: #333;
                border: 2px solid #ccc;
                border-radius: 5px;
                qproperty-segmentStyle: Flat;
                font-size: 24px;
            }
        """)
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_lcd, 0, Qt.AlignCenter)


        setpoint_frame = QFrame()
        setpoint_layout = QHBoxLayout() 

     
        self.temp_setpoint = QLineEdit()
        self.temp_setpoint.setAlignment(Qt.AlignCenter)
        self.temp_setpoint.setPlaceholderText(f"{self.device.temperature_setpoint}")
        self.temp_setpoint.setMinimumHeight(40)
        self.temp_setpoint.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                padding: 8px;
                border: 2px solid #ccc;
                border-radius: 5px;
                min-width: 150px;
            }
        """)

      
        self.setpoint_button = QPushButton("Установить")
        self.setpoint_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 8px 15px;
                min-width: 80px;
                background-color: #e0e0e0;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
        """)
        self.setpoint_button.clicked.connect(self.update_setpoint)

        setpoint_layout.addWidget(self.temp_setpoint)
        setpoint_layout.addWidget(self.setpoint_button)
        setpoint_frame.setLayout(setpoint_layout)

       
        setpoint_container = QVBoxLayout()
        setpoint_label = QLabel("Уставка температуры, °C")
        setpoint_label.setAlignment(Qt.AlignCenter)
        setpoint_label.setStyleSheet("font-size: 16px;")

        setpoint_container.addWidget(setpoint_label)
        setpoint_container.addWidget(setpoint_frame)
        temp_layout.addLayout(setpoint_container)

        temp_frame.setLayout(temp_layout)
        right_layout.addWidget(temp_frame)
        right_layout.addStretch()

        main_layout.addWidget(right_panel)

        port = 'COM3'
        sensor_slave_id = 1
        heater_slave_id = 2

        try:
            self.sensor = minimalmodbus.Instrument(port=port, slaveaddress=sensor_slave_id)
            self.sensor.serial.baudrate = 9600
            self.sensor.serial.bytesize = 8
            self.sensor.serial.stopbits = 1
            self.sensor.serial.parity = serial.PARITY_NONE
            print(f"sensor connect")
        except:
            print("Not connected sensor")

        try:
            self.heater = minimalmodbus.Instrument(port=port, slaveaddress=heater_slave_id)
            self.heater.serial.baudrate = 9600
            self.heater.serial.bytesize = 8
            self.heater.serial.stopbits = 1
            self.heater.serial.parity = serial.PARITY_NONE
            print("Heater connected")
            self.heater.write_bit(0, False, functioncode=5)

        except:
            print("Not connected heater")
        self.Controller = PI_PWM_Controller(2, 2, self.device.temperature_setpoint)
        self.update_timer = QTimer()
        self.on_timer = QTimer()

        self.update_timer.timeout.connect(self.update_values)
        self.on_timer.timeout.connect(self.on_heater)

        self.update_timer.start(5000)

    def update_setpoint(self):
        """Обновление уставки температуры при нажатии кнопки"""
        try:
            value = float(self.temp_setpoint.text())
            self.device.temperature_setpoint = value
            self.temp_setpoint.setPlaceholderText(f"{value}")
            self.temp_setpoint.clear()
        except ValueError:
            self.temp_setpoint.setText("")

    def update_heater_indicator(self):
        color = "#4CAF50" if self.device.heater_enabled else "#ccc"
        border = "#388E3C" if self.device.heater_enabled else "#999"
        self.heater_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 12px;
            border: 2px solid {border};
        """)

    def update_pump_indicator(self):
        color = "#4CAF50" if self.device.pump_enabled else "#ccc"
        border = "#388E3C" if self.device.pump_enabled else "#999"
        self.pump_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 12px;
            border: 2px solid {border};
        """)

    def toggle_heater(self, checked):
        self.device.heater_enabled = checked
        if checked:
            self.heater_button.setText("Выключить нагреватель")
            self.heater.write_bit(1, True, functioncode=5)
        else:
            self.heater_button.setText("Включить нагреватель")
            self.heater.write_bit(1, False, functioncode=5)


    def toggle_pump(self, checked):
        self.device.pump_enabled = checked
        if checked:
            self.pump_button.setText("Выключить насос")
            self.heater.write_bit(0, True, functioncode=5)
        else:
            self.pump_button.setText("Включить насос")
            self.heater.write_bit(0, False, functioncode=5)


    def update_values(self):
        """Мб если это перепишу все заработает Циклическое обновление данных с устройств"""
        try:
            self.device.temperature = self.sensor.read_register(0) / 10
            self.temp_lcd.display(self.device.temperature)
        except Exception as e:
            print(f"Ошибка обновления данных: {e}")
        try:
            self.device.pump_enabled=self.heater.read_bit(0,functioncode=1)
            self.update_pump_indicator()
        except Exception as e:
            print(f"Ошибка обновления данных насос: {e}")
        try:
            self.device.heater_enabled = self.heater.read_bit(1, functioncode=1)
            self.update_heater_indicator()
            print(self.device.heater_enabled)
        except Exception as e:
            print(f"Ошибка обновления данных насос: {e}")
        self.Controller.compute(self.heater, self.device.temperature)
        if (self.Controller.output > 95):
            self.heater.write_bit(1, True, functioncode=5)
            return
        elif(self.Controller.output<5):
            self.heater.write_bit(1, False, functioncode=5)
            return
        elif (self.Controller.output < 95 and self.Controller.output > 5):
            t_hight = self.Controller.output * 5000 / 100
            self.on_timer.start(t_hight)
            return

    def on_heater(self):
        self.on_timer.stop()
        self.heater.write_bit(1, False, functioncode=5)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())