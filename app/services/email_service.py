#!/usr/bin/env python3

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from contextlib import contextmanager
from datetime import datetime

from app.config import email_config
from app.logger import logger


class EmailSender:
    COMPANY_NAME = "BiyoVes"
    CURRENT_YEAR = datetime.now().year

    def __init__(self):
        try:
            self.smtp_server = email_config.EMAIL_SMTP_SERVER
            self.smtp_port = email_config.EMAIL_SMTP_PORT
            self.email = email_config.EMAIL_USER
            self.password = email_config.EMAIL_PASSWORD
        except Exception as e:
            logger.exception("Email config yüklenemedi: %s", e)
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
            self.email = None
            self.password = None

    def is_available(self):
        return bool(self.email and self.password)

    @contextmanager
    def _get_smtp_connection(self):
        connection = None
        try:
            connection = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            connection.starttls()
            connection.login(self.email, self.password)
            yield connection
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication hatası: %s", e)
            raise Exception("Email giriş bilgileri hatalı")
        except smtplib.SMTPException as e:
            logger.error("SMTP hatası: %s", e)
            raise Exception("Email sunucusu hatası")
        except Exception as e:
            logger.exception("Email bağlantı hatası: %s", e)
            raise Exception("Email gönderilemedi")
        finally:
            if connection:
                try:
                    connection.quit()
                except Exception:
                    pass

    def _send_email(self, to_email, subject, html_content, text_content):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)

            with self._get_smtp_connection() as conn:
                result = conn.sendmail(self.email, to_email, msg.as_string())
                if result:
                    logger.warning("Email kısmen başarısız: %s", result)
                    return False
                return True
        except Exception as e:
            logger.exception("Email gönderimi başarısız (%s): %s", to_email, e)
            return False

    def send_verification_email(self, to_email, verification_code):
        if not self.is_available():
            logger.warning("Email config yapılandırılmamış")
            return False
        subject = f"{self.COMPANY_NAME} - Email Doğrulama Kodu"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.COMPANY_NAME} Email Doğrulama</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f8fafc;
                    color: #334155;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 480px;
                    margin: 40px auto;
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
                    padding: 32px 24px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    letter-spacing: -0.5px;
                }}
                .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                    font-weight: 400;
                }}
                .content {{
                    padding: 32px 24px;
                }}
                .code-section {{
                    background: #f1f5f9;
                    border-radius: 12px;
                    padding: 24px;
                    text-align: center;
                    margin: 24px 0;
                    border: 1px solid #e2e8f0;
                }}
                .code-label {{
                    font-size: 14px;
                    color: #64748b;
                    margin-bottom: 12px;
                    font-weight: 500;
                }}
                .verification-code {{
                    font-size: 32px;
                    font-weight: 700;
                    color: #1a73e8;
                    letter-spacing: 8px;
                    margin: 8px 0;
                    font-family: 'SF Mono', Monaco, monospace;
                }}
                .code-expiry {{
                    font-size: 13px;
                    color: #ef4444;
                    margin-top: 8px;
                    font-weight: 500;
                }}
                .footer {{
                    background: #f8fafc;
                    padding: 24px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer-text {{
                    font-size: 13px;
                    color: #64748b;
                }}
                .divider {{
                    height: 1px;
                    background: #e2e8f0;
                    margin: 16px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{self.COMPANY_NAME}</div>
                    <div class="subtitle">Email Doğrulama</div>
                </div>
                <div class="content">
                    <p style="font-size: 16px; margin-bottom: 8px;">Merhaba!</p>
                    <p style="color: #64748b; margin-bottom: 24px;">Hesabınızı aktifleştirmek için aşağıdaki kodu kullanın.</p>
                    <div class="code-section">
                        <div class="code-label">Doğrulama Kodu</div>
                        <div class="verification-code">{verification_code}</div>
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-text">
                        Bu email {self.COMPANY_NAME} tarafından otomatik gönderilmiştir.<br>
                        <div class="divider"></div>
                        © {self.CURRENT_YEAR} {self.COMPANY_NAME}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        {self.COMPANY_NAME} Email Doğrulama

        Merhaba!

        Hesabınızı aktifleştirmek için aşağıdaki kodu kullanın:

        Doğrulama Kodu: {verification_code}

        Bu email {self.COMPANY_NAME} tarafından otomatik gönderilmiştir.
        © {self.CURRENT_YEAR} {self.COMPANY_NAME}
        """
        return self._send_email(to_email, subject, html_content, text_content)

    def send_welcome_email(self, to_email, username):
        if not self.is_available():
            logger.warning("Email config yapılandırılmamış")
            return False
        subject = f"{self.COMPANY_NAME}'e Hoş Geldiniz!"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.COMPANY_NAME}'e Hoş Geldiniz</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f8fafc;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 16px;
                    padding: 32px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 32px;
                    font-weight: 700;
                    color: #1a73e8;
                    margin-bottom: 10px;
                }}
                .welcome {{
                    color: #34a853;
                    font-size: 24px;
                    margin: 20px 0;
                }}
                .content {{
                    color: #334155;
                    line-height: 1.6;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #64748b;
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{self.COMPANY_NAME}</div>
                    <div class="welcome">Hoş Geldiniz!</div>
                </div>
                <div class="content">
                    <p>Merhaba <strong>{username}</strong>!</p>
                    <p>{self.COMPANY_NAME}'e hoş geldiniz! Email adresinizi doğruladığınız için <strong>3 ücretsiz hak</strong> kazandınız.</p>
                    <p>Artık profesyonel biyometrik ve vesikalık fotoğraflarınızı kolayca oluşturabilirsiniz.</p>
                </div>
                <div class="footer">
                    <p>© {self.CURRENT_YEAR} {self.COMPANY_NAME}. Tüm hakları saklıdır.</p>
                </div>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        {self.COMPANY_NAME}'e Hoş Geldiniz!

        Merhaba {username}!

        {self.COMPANY_NAME}'e hoş geldiniz! Email adresinizi doğruladığınız için 3 ücretsiz hak kazandınız.

        Artık profesyonel biyometrik ve vesikalık fotoğraflarınızı kolayca oluşturabilirsiniz.

        © {self.CURRENT_YEAR} {self.COMPANY_NAME}. Tüm hakları saklıdır.
        """
        return self._send_email(to_email, subject, html_content, text_content)

    def send_password_reset_email(self, to_email, reset_code):
        if not self.is_available():
            logger.warning("Email config yapılandırılmamış")
            return False
        subject = f"{self.COMPANY_NAME} - Şifre Sıfırlama Kodu"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.COMPANY_NAME} Şifre Sıfırlama</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f8fafc;
                    color: #334155;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 480px;
                    margin: 40px auto;
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%);
                    padding: 32px 24px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    letter-spacing: -0.5px;
                }}
                .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                    font-weight: 400;
                }}
                .content {{
                    padding: 32px 24px;
                }}
                .code-section {{
                    background: #fef2f2;
                    border-radius: 12px;
                    padding: 24px;
                    text-align: center;
                    margin: 24px 0;
                    border: 1px solid #fecaca;
                }}
                .code-label {{
                    font-size: 14px;
                    color: #dc2626;
                    margin-bottom: 12px;
                    font-weight: 500;
                }}
                .reset-code {{
                    font-size: 32px;
                    font-weight: 700;
                    color: #dc2626;
                    letter-spacing: 8px;
                    margin: 8px 0;
                    font-family: 'SF Mono', Monaco, monospace;
                }}
                .code-expiry {{
                    font-size: 13px;
                    color: #dc2626;
                    margin-top: 8px;
                    font-weight: 500;
                }}
                .warning {{
                    background: #fef3cd;
                    border: 1px solid #fde68a;
                    border-radius: 8px;
                    padding: 16px;
                    margin: 20px 0;
                    color: #92400e;
                }}
                .footer {{
                    background: #f8fafc;
                    padding: 24px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer-text {{
                    font-size: 13px;
                    color: #64748b;
                }}
                .divider {{
                    height: 1px;
                    background: #e2e8f0;
                    margin: 16px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{self.COMPANY_NAME}</div>
                    <div class="subtitle">Şifre Sıfırlama</div>
                </div>
                <div class="content">
                    <p style="font-size: 16px; margin-bottom: 8px;">Merhaba!</p>
                    <p style="color: #64748b; margin-bottom: 24px;">Şifrenizi sıfırlamak için aşağıdaki kodu kullanın.</p>
                    <div class="code-section">
                        <div class="code-label">Şifre Sıfırlama Kodu</div>
                        <div class="reset-code">{reset_code}</div>
                    </div>
                    <div class="warning">
                        <strong>Güvenlik Uyarısı:</strong><br>
                        Bu kodu kimseyle paylaşmayın. Eğer bu işlemi siz yapmadıysanız, hesabınızı kontrol edin.
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-text">
                        Bu email {self.COMPANY_NAME} tarafından otomatik gönderilmiştir.<br>
                        <div class="divider"></div>
                        © {self.CURRENT_YEAR} {self.COMPANY_NAME}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        {self.COMPANY_NAME} Şifre Sıfırlama

        Merhaba!

        Şifrenizi sıfırlamak için aşağıdaki kodu kullanın:

        Şifre Sıfırlama Kodu: {reset_code}

        Güvenlik Uyarısı:
        Bu kodu kimseyle paylaşmayın. Eğer bu işlemi siz yapmadıysanız, hesabınızı kontrol edin.

        Bu email {self.COMPANY_NAME} tarafından otomatik gönderilmiştir.
        © {self.CURRENT_YEAR} {self.COMPANY_NAME}
        """
        return self._send_email(to_email, subject, html_content, text_content)


email_sender = EmailSender()
