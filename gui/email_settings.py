from PyQt5 import uic
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QGroupBox, QMessageBox
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailSettings(QGroupBox):
    def __init__(self, *args, **kwargs):
        super(EmailSettings, self).__init__(*args, **kwargs)
        uic.loadUi("gui/email_settings.ui", self)
        self.load_settings()
        self.test_email_button.clicked.connect(self.send_test_email)

    def load_settings(self):
        settings = QSettings()
        self.sender_email.setText(settings.value("EmailSettings/sender_email", ""))
        self.email_password.setText(settings.value("EmailSettings/password", ""))
        self.recipient_email.setText(settings.value("EmailSettings/recipient", ""))

    def save_settings(self):
        settings = QSettings()
        settings.setValue("EmailSettings/sender_email", self.sender_email.text())
        settings.setValue("EmailSettings/password", self.email_password.text())
        settings.setValue("EmailSettings/recipient", self.recipient_email.text())
        settings.sync()

    def send_test_email(self):
        """Send a test email to verify the email settings."""
        try:
            # Email configuration
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = self.sender_email.text()
            password = self.email_password.text()
            recipient = self.recipient_email.text()

            if not all([sender_email, password, recipient]):
                QMessageBox.warning(self, "Missing Information", 
                    "Please fill in all email settings before sending a test email.")
                return

            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = "Battery Tester - Test Email"

            body = """This is a test email from your Battery Tester application.
            
If you're receiving this email, your email settings are configured correctly!"""
            msg.attach(MIMEText(body, 'plain'))

            # Connect to server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)

            QMessageBox.information(self, "Success", 
                "Test email sent successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Failed to send test email:\n{str(e)}") 