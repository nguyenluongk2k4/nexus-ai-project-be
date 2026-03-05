import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from config.settings import settings

class EmailService:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD

    def _send_sync(self, to_email: str, subject: str, body: str):
        """Synchronously send an email using smtplib"""
        if not self.user or not self.password:
            print("❌ SMTP credentials not configured.")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False

    async def send_otp_email(self, to_email: str, otp: str):
        """Asynchronously send OTP email"""
        subject = "Your NexusAI Password Reset Code"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your NexusAI password.</p>
                <p>Your 6-digit verification code is:</p>
                <h1 style="color: #7C3AED; font-size: 32px; letter-spacing: 5px; padding: 10px; background-color: #F3F4F6; border-radius: 8px; width: fit-content;">{otp}</h1>
                <p>This code will expire in exactly 2 minutes.</p>
                <p>If you didn't request a password reset, please ignore this email.</p>
                <br/>
                <p>Best regards,</p>
                <p><strong>The NexusAI Team</strong></p>
            </body>
        </html>
        """
        success = await asyncio.to_thread(self._send_sync, to_email, subject, body)
        return success

def get_email_service() -> EmailService:
    return EmailService()
