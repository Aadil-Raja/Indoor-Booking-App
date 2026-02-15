from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import get_settings
from typing import List

settings = get_settings()

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=settings.use_credentials,
    VALIDATE_CERTS=settings.validate_certs
)

fm = FastMail(conf)


async def send_otp_email(email: str, code: str, purpose: str = "verification"):
    """
    Send OTP code via email.
    
    Args:
        email: Recipient email address
        code: 6-digit OTP code
        purpose: Either 'verification' (signup) or 'login'
    """
    if purpose == "verification":
        subject = "Verify Your Email Address"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Welcome to Our App!</h2>
                    <p>Thank you for signing up. Please verify your email address using the code below:</p>
                    
                    <div style="background-color: #F3F4F6; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                        <h1 style="font-size: 36px; letter-spacing: 8px; color: #4F46E5; margin: 0;">
                            {code}
                        </h1>
                    </div>
                    
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 30px 0;">
                    <p style="font-size: 12px; color: #6B7280;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
    else:  # login
        subject = "Your Login Code"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Login Verification</h2>
                    <p>Here's your login verification code:</p>
                    
                    <div style="background-color: #F3F4F6; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                        <h1 style="font-size: 36px; letter-spacing: 8px; color: #4F46E5; margin: 0;">
                            {code}
                        </h1>
                    </div>
                    
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <p>If you didn't request this code, please secure your account immediately.</p>
                    
                    <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 30px 0;">
                    <p style="font-size: 12px; color: #6B7280;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )

    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"Error sending email to {email}: {str(e)}")
        return False


async def send_welcome_email(email: str, name: str = ""):
    """
    Send welcome email after successful verification.
    """
    subject = "Welcome to Our App!"
    display_name = name if name else "there"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Welcome aboard, {display_name}! 🎉</h2>
                <p>Your email has been successfully verified.</p>
                <p>We're excited to have you with us. You can now access all features of our platform.</p>
                
                <div style="margin: 30px 0;">
                    <a href="YOUR_APP_URL" 
                       style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Get Started
                    </a>
                </div>
                
                <p>If you have any questions, feel free to reach out to our support team.</p>
                
                <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 30px 0;">
                <p style="font-size: 12px; color: #6B7280;">
                    This is an automated message, please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )

    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"Error sending welcome email to {email}: {str(e)}")
        return False
    

    
async def send_password_reset_email(email: str, link: str, name: str | None = None, expires_minutes: int = 60):
    """
    Send a password reset email with a secure link.
    - email: recipient
    - link: full reset URL incl. token (e.g. https://app/reset-password?token=...)
    - name: optional display name
    - expires_minutes: token validity hint for the user
    """
    subject = "Reset your password"
    display_name = name or "there"

    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #111;">
        <div style="max-width:600px;margin:0 auto;padding:24px;">
          <h2 style="color:#4F46E5;margin:0 0 12px;">Password reset request</h2>
          <p>Hi {display_name},</p>
          <p>We received a request to reset your password. Click the button below to choose a new one.</p>

          <div style="margin:24px 0;text-align:center;">
            <a href="{link}"
               style="background:#4F46E5;color:#fff;text-decoration:none;padding:12px 20px;border-radius:6px;display:inline-block;">
               Reset Password
            </a>
          </div>

          <p>If the button doesn’t work, copy and paste this link into your browser:</p>
          <p style="word-break:break-all;"><a href="{link}">{link}</a></p>

          <p style="margin-top:16px;">This link will expire in <strong>{expires_minutes} minutes</strong>. 
          If you didn’t request a password reset, you can safely ignore this email.</p>

          <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
          <p style="font-size:12px;color:#6b7280;">This is an automated message; please don’t reply.</p>
        </div>
      </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html,
    )

    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        # Keep failures non-fatal to callers; log as needed
        print(f"Error sending password reset email to {email}: {e}")
        return False