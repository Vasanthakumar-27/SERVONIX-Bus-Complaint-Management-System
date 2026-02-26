"""Email service for sending OTP, notifications, and messages"""
import os
import time
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
try:
    import requests as _requests
except ImportError:
    _requests = None

# Load .env explicitly from backend/ so this works regardless of CWD
_backend_dir = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(_backend_dir, '.env'))
logger = logging.getLogger(__name__)


class EmailService:
    """Handles all email sending functionality"""
    
    def __init__(self):
        self.sender_email = os.environ.get('EMAIL_SENDER', 'noreply@servonix.com')
        self.sender_password = os.environ.get('EMAIL_PASSWORD', '')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_timeout = int(os.environ.get('SMTP_TIMEOUT', '20'))
        # Optional display name shown in inbox (e.g. "SERVONIX Support")
        self.from_name = os.environ.get('EMAIL_FROM_NAME', 'SERVONIX')
        # Resend HTTPS API key (preferred on Render — bypasses blocked SMTP ports)
        # DISABLED: Only use Resend if explicitly configured with verified domain
        # Setting to empty to force SMTP/Gmail usage instead
        self.resend_api_key = ''  # os.environ.get('RESEND_API_KEY', '')
        # From address for Resend: override via RESEND_FROM env var.
        # Default is Resend's shared sandbox address (works without domain verify).
        self.resend_from = os.environ.get('RESEND_FROM', f'SERVONIX <onboarding@resend.dev>')
        # Development mode: no password AND no Resend key
        self.development_mode = not bool(self.sender_password) and not bool(self.resend_api_key)

        if self.resend_api_key:
            logger.info("Email service using Resend HTTPS API")
        elif self.sender_password:
            logger.info(f"Email service using SMTP ({self.smtp_server}:{self.smtp_port}) as {self.sender_email}")
        else:
            logger.warning("Email service running in DEVELOPMENT MODE - emails will be logged to console and to file")
    
    def _send_via_resend(self, to_email, subject, html_body):
        """Send email via Resend HTTPS API (works on Render free tier)"""
        if _requests is None:
            logger.error("requests library not installed - cannot use Resend API")
            return False
        # Resend sandbox (onboarding@resend.dev) can ONLY deliver to the Resend
        # account owner's verified address — treat any other recipient as a failure
        # so the frontend falls back to the inline OTP banner.
        if 'onboarding@resend.dev' in self.resend_from:
            logger.warning(
                f"[Resend] Sandbox sender detected (onboarding@resend.dev). "
                f"Emails are only delivered to the Resend account owner, NOT to {to_email}. "
                f"Set RESEND_FROM to a verified domain address to send to real users."
            )
            return False
        try:
            payload = {
                "from": self.resend_from,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            resp = _requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload),
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"[Resend] Email sent to {to_email}: {subject}")
                return True
            else:
                logger.error(f"[Resend] Failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"[Resend] Exception sending to {to_email}: {e}")
            return False

    def _send_email(self, to_email, subject, html_body):
        """Internal method to send email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg.attach(MIMEText(html_body, 'html'))

            # --- Priority 1: Resend HTTPS API (Render-compatible) ---
            if self.resend_api_key:
                return self._send_via_resend(to_email, subject, html_body)

            # --- Priority 2: Development mode (no credentials) ---
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
            # --- Priority 3: SMTP ---
            else:
                # Try SSL (port 465) FIRST — more reliable on cloud hosts (Render etc.)
                # because it opens a direct TLS connection without a STARTTLS handshake
                # that intermediate firewalls can block.
                sent = False
                last_err = None
                # --- Attempt 1: SMTP_SSL on port 465 ---
                try:
                    with smtplib.SMTP_SSL(self.smtp_server, 465, timeout=self.smtp_timeout) as server:
                        server.ehlo()
                        server.login(self.sender_email, self.sender_password)
                        server.send_message(msg)
                    sent = True
                    logger.info(f"[SMTP SSL:465] Email sent to {to_email}: {subject}")
                except Exception as ssl_err:
                    last_err = ssl_err
                    logger.warning(f"SSL:465 failed: {ssl_err} — trying STARTTLS:{self.smtp_port}")
                # --- Attempt 2: STARTTLS on configured port (default 587) ---
                if not sent:
                    try:
                        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout) as server:
                            server.ehlo()
                            server.starttls()
                            server.ehlo()
                            server.login(self.sender_email, self.sender_password)
                            server.send_message(msg)
                        sent = True
                        logger.info(f"[SMTP STARTTLS:{self.smtp_port}] Email sent to {to_email}: {subject}")
                    except Exception as starttls_err:
                        logger.error(f"STARTTLS:{self.smtp_port} also failed: {starttls_err} (SSL error: {last_err})")
                        last_err = starttls_err
                if sent:
                    return True
                raise last_err or Exception("All SMTP attempts failed")
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def get_status(self):
        """Return a safe dict describing the current email configuration (no passwords)."""
        if self.resend_api_key:
            sandbox = 'onboarding@resend.dev' in self.resend_from
            return {
                'mode': 'resend',
                'from': self.resend_from,
                'sandbox': sandbox,
                'warning': (
                    'Resend sandbox sender — emails only go to the Resend account owner. '
                    'Set RESEND_FROM to a verified domain address.'
                ) if sandbox else None,
            }
        if self.development_mode:
            return {'mode': 'development', 'note': 'No email credentials configured — OTP is logged only'}
        return {
            'mode': 'smtp',
            'server': self.smtp_server,
            'port': self.smtp_port,
            'sender': self.sender_email,
            'timeout': self.smtp_timeout,
        }

    def test_smtp_connection(self):
        """
        Test SMTP connectivity without sending an email.
        Returns (success: bool, message: str).
        """
        if self.resend_api_key:
            sandbox = 'onboarding@resend.dev' in self.resend_from
            if sandbox:
                return False, 'Resend sandbox — only delivers to account owner. Set RESEND_FROM to a verified domain.'
            # Test Resend API key validity with a dry-run request
            if _requests is None:
                return False, 'requests library not installed'
            try:
                resp = _requests.get(
                    'https://api.resend.com/domains',
                    headers={'Authorization': f'Bearer {self.resend_api_key}'},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return True, f'Resend API key valid. Domains: {[d.get("name") for d in resp.json().get("data", [])]}'
                return False, f'Resend API returned {resp.status_code}: {resp.text[:200]}'
            except Exception as e:
                return False, f'Resend API error: {e}'
        if self.development_mode:
            return False, 'Development mode — no credentials configured'
        # SMTP connection test — try SSL:465 first (same order as _send_email)
        try:
            with smtplib.SMTP_SSL(self.smtp_server, 465, timeout=self.smtp_timeout) as server:
                server.ehlo()
                server.login(self.sender_email, self.sender_password)
            return True, f'SMTP SSL:465 login to {self.smtp_server} as {self.sender_email} succeeded'
        except smtplib.SMTPAuthenticationError as e:
            return False, f'SMTP authentication failed on SSL:465 — check EMAIL_SENDER and EMAIL_PASSWORD (use Gmail App Password, not your account password): {e}'
        except Exception as ssl_err:
            pass  # fall through to STARTTLS
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender_email, self.sender_password)
            return True, f'SMTP STARTTLS:{self.smtp_port} login to {self.smtp_server} as {self.sender_email} succeeded'
        except smtplib.SMTPAuthenticationError as e:
            return False, f'SMTP authentication failed — check EMAIL_SENDER and EMAIL_PASSWORD (use Gmail App Password, not your account password): {e}'
        except smtplib.SMTPConnectError as e:
            return False, f'Cannot connect to {self.smtp_server} on ports 465 or {self.smtp_port} — both are blocked on this host. Use Resend API instead: {e}'
        except Exception as e:
            return False, f'SMTP error on both ports: {e}'

    # ------------------------------------------------------------------ #

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
