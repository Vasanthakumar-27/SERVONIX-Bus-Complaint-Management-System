"""Email service for sending OTP, notifications, and messages"""
import os
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EmailService:
    """Handles all email sending functionality"""
    
    def __init__(self):
        self.sender_email = os.environ.get('EMAIL_SENDER', 'noreply@servonix.com')
        self.sender_password = os.environ.get('EMAIL_PASSWORD', '')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.development_mode = not bool(self.sender_password)
        
        if self.development_mode:
            logger.warning("Email service running in DEVELOPMENT MODE - emails will be logged to console and to file")
    
    def _send_email(self, to_email, subject, html_body):
        """Internal method to send email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"SERVONIX <{self.sender_email}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_body, 'html'))
            
            if self.development_mode:
                # Development mode: log to console and append to a local email log file
                logger.warning(f"[DEV MODE] Email to {to_email}: {subject}")
                print(f"\n{'='*80}\n📧 EMAIL (DEVELOPMENT MODE)\n{'-'*80}")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Body preview: {html_body[:200]}...")
                print(f"{'='*80}\n")
                try:
                    # Ensure logs directory exists
                    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                    os.makedirs(logs_dir, exist_ok=True)
                    log_path = os.path.join(logs_dir, 'email_dev.log')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n=== EMAIL [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===\nTo: {to_email}\nSubject: {subject}\n{html_body}\n=== END EMAIL ===\n")
                except Exception:
                    logger.exception('Failed to write dev email log')
                return True
            else:
                # Production mode: send via SMTP
                # Try STARTTLS (port 587) first, fall back to SSL (port 465)
                sent = False
                last_err = None
                # --- Attempt 1: STARTTLS on configured port (default 587) ---
                try:
                    with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20) as server:
                        server.starttls()
                        server.login(self.sender_email, self.sender_password)
                        server.send_message(msg)
                    sent = True
                except Exception as starttls_err:
                    last_err = starttls_err
                    logger.warning(f"STARTTLS failed ({self.smtp_port}): {starttls_err} — trying SSL:465")
                # --- Attempt 2: SMTP_SSL on port 465 ---
                if not sent:
                    try:
                        with smtplib.SMTP_SSL(self.smtp_server, 465, timeout=20) as server:
                            server.login(self.sender_email, self.sender_password)
                            server.send_message(msg)
                        sent = True
                    except Exception as ssl_err:
                        logger.error(f"SSL:465 also failed: {ssl_err} (original error: {last_err})")
                if sent:
                    logger.info(f"Email sent to {to_email}: {subject}")
                    return True
                raise last_err or Exception("All SMTP attempts failed")
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def send_otp_email(self, email, otp, user_name):
        """Send OTP for password reset - SECURE VERSION"""
        subject = '🔐 Password Reset OTP - SERVONIX'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                            <tr>
                                <td style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); padding: 40px 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">🔐 Password Reset</h1>
                                    <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 14px;">SERVONIX Complaint Management System</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="color: #1f2937; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                        Hello <strong>{user_name}</strong>,
                                    </p>
                                    <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;">
                                        We received a request to reset your password. Use the OTP code below:
                                    </p>
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                        <tr>
                                            <td align="center">
                                                <div style="display: inline-block; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 2px dashed #4f46e5; padding: 25px 50px; border-radius: 12px;">
                                                    <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #4f46e5; font-family: 'Courier New', monospace;">{otp}</div>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                        <tr>
                                            <td style="padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px;">
                                                <p style="color: #92400e; font-size: 13px; line-height: 1.8; margin: 0;">
                                                    <strong>⚠️ Security Notice:</strong><br>
                                                    • This OTP expires in <strong>5 minutes</strong><br>
                                                    • Can only be used <strong>once</strong><br>
                                                    • Never share this code with anyone<br>
                                                    • SERVONIX staff will never ask for your OTP
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    <p style="color: #6b7280; font-size: 13px; line-height: 1.6; margin: 20px 0 0 0;">
                                        If you didn't request this, please ignore this email.
                                    </p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                                        © 2024 SERVONIX. All rights reserved.<br>
                                        This is an automated email, please do not reply.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # In dev mode, also print OTP to console for easy testing
        if self.development_mode:
            print(f"\n{'='*80}\n📧 PASSWORD RESET OTP (SECURE)\n{'-'*80}\nEmail: {email}\nOTP: {otp}\nExpires: 5 minutes\n{'='*80}\n")
        
        return self._send_email(email, subject, html)
    
    def send_registration_otp_email(self, email, otp, user_name):
        """Send OTP for registration verification"""
        subject = '✉️ Verify Your Email - SERVONIX Registration'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                            <tr>
                                <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">✉️ Verify Your Email</h1>
                                    <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">Complete your SERVONIX registration</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="color: #1f2937; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                        Welcome <strong>{user_name}</strong>! 👋
                                    </p>
                                    <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;">
                                        Thank you for registering with SERVONIX. Please use the verification code below to complete your registration:
                                    </p>
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                        <tr>
                                            <td align="center">
                                                <div style="display: inline-block; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border: 2px dashed #10b981; padding: 25px 50px; border-radius: 12px;">
                                                    <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #059669; font-family: 'Courier New', monospace;">{otp}</div>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                        <tr>
                                            <td style="padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px;">
                                                <p style="color: #92400e; font-size: 13px; line-height: 1.8; margin: 0;">
                                                    <strong>⚠️ Important:</strong><br>
                                                    • This code expires in <strong>5 minutes</strong><br>
                                                    • Can only be used <strong>once</strong><br>
                                                    • If you didn't register, please ignore this email
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                                        © 2024 SERVONIX. All rights reserved.<br>
                                        This is an automated email, please do not reply.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # In dev mode, also print OTP to console for easy testing
        if self.development_mode:
            print(f"\n{'='*80}\n📧 REGISTRATION OTP\n{'-'*80}\nEmail: {email}\nName: {user_name}\nOTP: {otp}\nExpires: 5 minutes\n{'='*80}\n")
        
        return self._send_email(email, subject, html)
    
    def send_notification_email(self, email, subject, message, recipient_name=None):
        """Send general notification/message email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                            <tr>
                                <td style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">📧 {subject}</h1>
                                    <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 14px;">SERVONIX Notification</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    {f'<p style="color: #1f2937; font-size: 16px; margin: 0 0 20px 0;">Hello <strong>{recipient_name}</strong>,</p>' if recipient_name else ''}
                                    <p style="color: #1f2937; font-size: 15px; line-height: 1.8; margin: 0 0 20px 0; white-space: pre-wrap;">{message}</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                                        © 2024 SERVONIX. All rights reserved.<br>
                                        Complaint Management System
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return self._send_email(email, subject, html)
    
    def send_complaint_notification(self, email, complaint_id, complaint_type, status, recipient_name=None):
        """Send complaint status update notification"""
        subject = f'Complaint #{complaint_id} Update - {status.upper()}'
        
        status_colors = {
            'pending': '#f59e0b',
            'in-progress': '#3b82f6',
            'resolved': '#10b981',
            'rejected': '#ef4444'
        }
        
        color = status_colors.get(status, '#6b7280')
        
        message = f"""
Your complaint regarding "{complaint_type}" has been updated.

Complaint ID: #{complaint_id}
New Status: {status.upper()}

You will be notified of any further updates.
        """
        
        return self.send_notification_email(email, subject, message, recipient_name)
    
    def send_welcome_email(self, email, user_name):
        """Send welcome email to new users"""
        subject = 'Welcome to SERVONIX - Registration Successful'
        
        message = f"""
Thank you for registering with SERVONIX Complaint Management System!

Your account has been created successfully. You can now:
- Submit complaints about bus services
- Track your complaint status in real-time
- Receive updates and notifications
- View complaint history

If you have any questions, please don't hesitate to contact us.
        """
        
        return self.send_notification_email(email, subject, message, user_name)


# Create a singleton instance
email_service = EmailService()
