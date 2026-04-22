"""One-time test email script."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env manually
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

smtp_server   = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
smtp_port     = int(os.getenv('SMTP_PORT', '587'))
sender_email  = os.getenv('SENDER_EMAIL', '')
sender_password = os.getenv('SENDER_PASSWORD', '')

print(f"SMTP : {smtp_server}:{smtp_port}")
print(f"FROM : {sender_email}")
print(f"PASS : {'(set)' if sender_password else '(MISSING)'}")

TO = 'octavian.iosup@gmail.com'

msg = MIMEMultipart('alternative')
msg['From']    = sender_email
msg['To']      = TO
msg['Subject'] = 'Stdytime - Email Delivery Test'
msg.attach(MIMEText('This is a test email from Stdytime to confirm email delivery is working.', 'plain'))
msg.attach(MIMEText(
    '<p>This is a <strong>test email</strong> from <b>Stdytime</b> to confirm email delivery is working.</p>',
    'html'
))

try:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
    print(f"\nSUCCESS: Email sent to {TO}")
except smtplib.SMTPAuthenticationError as e:
    print(f"\nERROR (authentication): {e}")
    print("Check SENDER_EMAIL and SENDER_PASSWORD in .env")
    print("If using Gmail, you need an App Password (not your regular password)")
    print("See: https://myaccount.google.com/apppasswords")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
