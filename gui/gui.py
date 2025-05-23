import matplotlib
import smtplib
import os
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time

matplotlib.use('Qt5Agg')

from PyQt5 import QtWidgets, uic

from PyQt5.QtCore import (
    QSettings,
    Qt,
    QSize,
    QPoint,
    QTimer,
)

from PyQt5.QtWidgets import (
    QVBoxLayout,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure

from instruments.instrument import Instrument
from gui.swcccv import SwCCCV
from gui.internal_r import InternalR
from gui.log_control import LogControl
from sys import argv
from gui.email_settings import EmailSettings


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        uic.loadUi('gui/main.ui', self)
        self.load_settings()

        self.plot_placeholder.setLayout(self.plot_layout())
        self.map_controls()
        self.tab2 = uic.loadUi("gui/settings.ui")
        self.logControl = LogControl()
        self.swCCCV = SwCCCV()
        self.internal_r = InternalR()
        self.email_settings = EmailSettings()
        self.email_settings.set_main_window(self)
        self.controlsLayout.insertWidget(3, self.internal_r)
        self.tab2.layout().addWidget(self.logControl, 0, 0)
        self.tab2.layout().addWidget(self.swCCCV, 1, 0)
        self.tab2.layout().addWidget(self.email_settings, 2, 0)
        self.tabs.addTab(self.tab2, "Settings")
        self.email_sent = False
        self.show()

    def plot_layout(self):
        self.canvas = MplCanvas(self, width=8, height=4, dpi=100)
        self.ax = self.canvas.axes
        self.twinax = self.ax.twinx()

        toolbar = NavigationToolbar(self.canvas, self)
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        return layout

    def map_controls(self):
        self.en_checkbox.stateChanged.connect(self.enabled_changed)
        self.set_voltage.valueChanged.connect(self.voltage_changed)
        self.set_current.valueChanged.connect(self.current_changed)
        self.set_timer.timeChanged.connect(self.timer_changed)
        self.resetButton.clicked.connect(self.reset_dev)

        self.set_voltage_timer = QTimer(singleShot=True,
                                        timeout=self.voltage_set)
        self.set_current_timer = QTimer(singleShot=True,
                                        timeout=self.current_set)
        self.set_timer_timer = QTimer(singleShot=True, timeout=self.timer_set)

    def data_row(self, data, row):
        if data:
            set_voltage = data.lastval('set_voltage')
            if not self.set_voltage.hasFocus():
                self.set_voltage.setValue(set_voltage)

            set_current = data.lastval('set_current')
            if not self.set_current.hasFocus():
                self.set_current.setValue(set_current)

            is_on = data.lastval('is_on')
            if is_on:
                self.en_checkbox.setCheckState(Qt.Checked)
            else:
                self.en_checkbox.setCheckState(Qt.Unchecked)

            voltage = data.lastval('voltage')
            current = data.lastval('current')
            self.setWindowTitle("Battery tester {:4.2f}V {:4.2f}A ".format(
                voltage, current))
            self.readVoltage.setText("{:5.3f} V".format(voltage))
            self.readCurrent.setText("{:5.3f} A".format(current))
            self.readCapAH.setText("{:5.3f} AH".format(data.lastval('cap_ah')))
            self.readCapWH.setText("{:5.3f} WH".format(data.lastval('cap_wh')))
            self.readTime.setText(data.lastval('time').strftime("%H:%M:%S"))

            xlim = (time(0), max([time(0, 1, 0), data.lastval('time')]))
            self.ax.cla()
            self.twinax.cla()
            data.plot(ax=self.ax, x='time', y=['voltage'], xlim=xlim)
            self.ax.legend(loc='center left')
            self.ax.set_ylabel('Voltage, V')
            self.ax.set_ylim(bottom=set_voltage)
            data.plot(ax=self.twinax, x='time', y=['current'], style='r')
            self.twinax.legend(loc='center right')
            self.twinax.set_ylabel('Current, A')
            self.twinax.set_ylim(0, 10)
            self.canvas.draw()

            # Check if test has just completed (device turned off)
            if 'is_on' in row and not row['is_on'] and hasattr(self, 'prev_is_on') and self.prev_is_on:
                if not self.email_sent:
                    print("Test completed, writing logs and sending email...")
                    self.write_logs()
                    self.email_sent = True
                else:
                    print("Email already sent for this test")

            # Store current state for next comparison
            self.prev_is_on = row.get('is_on', False)

    def status_update(self, status):
        self.statusBar().showMessage(status)

    def set_backend(self, backend):
        self.backend = backend
        backend.subscribe(self)
        self.swCCCV.set_backend(backend)
        self.internal_r.set_backend(backend)

    def closeEvent(self, event):
        self.logControl.save_settings()
        self.swCCCV.save_settings()
        self.internal_r.save_settings()
        self.email_settings.save_settings()
        self.save_settings()
        self.write_logs()

        self.backend.at_exit()
        event.accept()

    def enabled_changed(self):
        if self.en_checkbox.hasFocus():
            value = self.en_checkbox.isChecked()
            self.en_checkbox.clearFocus()
            self.backend.send_command({Instrument.COMMAND_ENABLE: value})

    def voltage_changed(self):
        if self.set_voltage.hasFocus():
            self.set_voltage_timer.start(1000)

    def voltage_set(self):
        value = round(self.set_voltage.value(), 2)
        self.set_voltage.clearFocus()
        self.backend.send_command({Instrument.COMMAND_SET_VOLTAGE: value})

    def current_changed(self):
        if self.set_current.hasFocus():
            self.set_current_timer.start(1000)

    def current_set(self):
        value = round(self.set_current.value(), 2)
        self.set_current.clearFocus()
        self.backend.send_command({Instrument.COMMAND_SET_CURRENT: value})

    def timer_changed(self):
        if self.set_timer.hasFocus():
            self.set_timer_timer.start(1000)

    def timer_set(self):
        set_time = self.set_timer.time()
        value = time(set_time.hour(), set_time.minute(), set_time.second())
        self.set_timer.clearFocus()
        self.backend.send_command({Instrument.COMMAND_SET_TIMER: value})

    def reset_dev(self, s):
        self.resetButton.clearFocus()
        self.write_logs()
        self.swCCCV.reset()
        self.internal_r.reset()
        self.backend.datastore.reset()
        self.backend.send_command({Instrument.COMMAND_RESET: 0.0})
        self.email_sent = False

    def load_settings(self):
        settings = QSettings()

        self.resize(settings.value("MainWindow/size", QSize(1024, 600)))
        self.move(settings.value("MainWindow/pos", QPoint(0, 0)))
        self.cellLabel.setText(settings.value("MainWindow/cellLabel",
                                              'Cell x'))

    def write_logs(self):
        if self.logControl.isChecked():
            # Get battery data first to validate
            data = self.backend.datastore
            if not data or len(data.data) < 2:  # Check if we have at least 2 data points
                print("Insufficient data for logging/email")
                return

            # Validate critical data values
            voltage = data.lastval('voltage')
            current = data.lastval('current')
            cap_ah = data.lastval('cap_ah')
            cap_wh = data.lastval('cap_wh')
            test_time = data.lastval('time')

            if any(v is None for v in [voltage, current, cap_ah, cap_wh, test_time]):
                print("Missing critical data values, skipping email")
                return

            if cap_ah <= 0 or cap_wh <= 0:
                print("Invalid capacity values, skipping email")
                return

            cell_label = self.cellLabel.text().replace(" ", "_")  # Replace spaces with underscores
            base_path = self.logControl.full_path
            log_path = os.path.join(base_path, "logs")

            print(f"Writing logs for {cell_label} to {log_path}")

            # Create the log directory if it doesn't exist
            try:
                os.makedirs(log_path, exist_ok=True)
                print(f"Ensured log directory exists: {log_path}")
            except Exception as e:
                print(f"Error creating log directory: {e}")
                return

            # Write logs and get file paths
            internal_r_file = self.internal_r.write(log_path, cell_label)
            data_file = self.backend.datastore.write(log_path, cell_label)

            print(f"Log files: internal_r={internal_r_file}, data={data_file}")

            # At least the data file should exist
            if not data_file:
                print("Failed to write data file")
                return

            # Save the current plot as an image with cell label
            plot_filename = f"{cell_label}_plot.png"
            fd, plot_file = tempfile.mkstemp(suffix=f'_{plot_filename}')
            os.close(fd)
            self.canvas.fig.savefig(plot_file, dpi=100)
            print(f"Plot saved to {plot_file}")

            print(f"Preparing email with data: V={voltage:.3f}, I={current:.3f}, Ah={cap_ah:.3f}, Wh={cap_wh:.3f}")

            # Send email with test results
            subject = f"Battery Test Completed: {cell_label}"
            message = f"""Battery Test Results for {cell_label}

Results:
- Final Voltage: {voltage:.3f} V
- Final Current: {current:.3f} A
- Capacity: {cap_ah:.3f} AH / {cap_wh:.3f} WH
- Test Duration: {test_time.strftime("%H:%M:%S")}

The test data files and plot are attached.
"""
            # Include all available files (internal_r_file might be None)
            attachments = [f for f in [internal_r_file, data_file, plot_file] if f and os.path.exists(f)]
            if attachments:
                print(f"Sending email with {len(attachments)} attachments")
                self.send_email_notification(subject, message, attachments)

                # Clean up the temporary file
                try:
                    os.remove(plot_file)
                except Exception as e:
                    print(f"Error removing temp file: {e}")
            else:
                print("No attachments available, skipping email")

    def save_settings(self):
        settings = QSettings()

        settings.setValue("MainWindow/size", self.size())
        settings.setValue("MainWindow/pos", self.pos())
        settings.setValue("MainWindow/cellLabel", self.cellLabel.text())

        settings.sync()

    def send_email_notification(self, subject, message, attachments=None):
        """Send email notification with optional attachments."""
        try:
            # Email configuration
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = self.email_settings.sender_email.text()
            password = self.email_settings.email_password.text()
            recipient = self.email_settings.recipient_email.text()

            if not all([sender_email, password, recipient]):
                print("❌ Email settings not configured")
                self.email_settings.save_email_history(subject, recipient, 'failed - not configured')
                return

            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject

            # Add message body
            msg.attach(MIMEText(message, 'plain'))

            # Add attachments if any
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as file:
                            from email.mime.application import MIMEApplication
                            part = MIMEApplication(file.read(), Name=os.path.basename(file_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                        msg.attach(part)

            # Connect to server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)

            print(f"✅ Email sent successfully to {recipient}")
            self.email_settings.save_email_history(subject, recipient, 'success')
            
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            self.email_settings.save_email_history(subject, recipient, f'failed - {str(e)}')


class GUI:
    def __init__(self, backend):
        app = QtWidgets.QApplication(argv)
        self.window = MainWindow()
        self.window.set_backend(backend)
        app.exec_()
