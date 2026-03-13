"""
Email Manager Module for KumoClock
Handles email sending functionality for reports, notifications, and student communications
Version: 06.00.00
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional, List, Dict


class EmailManager:
    """Manages email sending operations"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None, 
                 sender_email: str = None, sender_password: str = None):
        """
        Initialize email manager with SMTP configuration
        
        Args:
            smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            sender_email: Sender email address
            sender_password: Sender email password or app-specific password
        """
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = sender_email or os.getenv('SENDER_EMAIL', '')
        self.sender_password = sender_password or os.getenv('SENDER_PASSWORD', '')
    
    def send_email(self, recipient_email: str, subject: str, body: str, 
                   html_body: Optional[str] = None, 
                   attachments: Optional[List[str]] = None,
                   no_reply: bool = False) -> Dict[str, any]:
        """
        Send an email
        
        Args:
            recipient_email: Recipient's email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML version of the email body
            attachments: Optional list of file paths to attach
            no_reply: If True, prevents recipients from replying (sets headers to block replies)
            
        Returns:
            Dictionary with 'success' status and 'message' or 'error'
        """
        try:
            # Validate configuration
            if not self.sender_email or not self.sender_password:
                return {
                    'success': False,
                    'error': 'Email configuration not set. Please configure SMTP settings.'
                }
            
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = recipient_email
            message['Subject'] = subject
            
            # Set no-reply headers if requested
            if no_reply:
                # Set Reply-To to empty (prevents replies in most email clients)
                message['Reply-To'] = ''
                # Prevent auto-replies from mail servers
                message['Precedence'] = 'bulk'
                # Hide unsubscribe option (professional approach)
                message['List-Unsubscribe'] = '<mailto:noreply@kumoclock.local>'
            
            # Attach plain text body
            part1 = MIMEText(body, 'plain')
            message.attach(part1)
            
            # Attach HTML body if provided
            if html_body:
                part2 = MIMEText(html_body, 'html')
                message.attach(part2)
            
            # Attach files if provided
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}',
                            )
                            message.attach(part)
            
            # Connect to server and send
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()  # Secure the connection
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            except smtplib.SMTPAuthenticationError:
                # Common issue: Gmail app passwords are often copied with spaces for readability.
                # Retry once with internal spaces removed.
                compact_password = (self.sender_password or '').replace(' ', '')
                if compact_password and compact_password != self.sender_password:
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.sender_email, compact_password)
                        server.send_message(message)
                else:
                    raise
            
            return {
                'success': True,
                'message': f'Email sent successfully to {recipient_email}'
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'error': 'Authentication failed. Please check SENDER_EMAIL/SENDER_PASSWORD (for Gmail app password, try without spaces).'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'error': f'SMTP error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error sending email: {str(e)}'
            }
    
    def send_report_card(self, student_name: str, recipient_email: str, 
                        report_data: Dict[str, any]) -> Dict[str, any]:
        """
        Send student report card via email
        
        Args:
            student_name: Student's full name
            recipient_email: Recipient's email address
            report_data: Dictionary containing report information
            
        Returns:
            Dictionary with 'success' status and 'message' or 'error'
        """
        subject = f"Student Report Card - {student_name}"
        
        # Create plain text body
        body = f"""
Dear Parent/Guardian,

Please find below the report card for {student_name}.

*** DO NOT REPLY TO THIS EMAIL ***

REPORT SUMMARY:
---------------
Subject: {report_data.get('subject', 'N/A')}
Date Range: {report_data.get('start_date', 'N/A')} to {report_data.get('end_date', 'N/A')}
Highest Worksheet Completed: {report_data.get('highest_ws_completed', 'N/A')}
Number of Worksheets: {report_data.get('num_ws', 'N/A')}
Study Days: {report_data.get('study_days', 'N/A')}
Cumulative Study Time: {report_data.get('cum_study_time', 'N/A')}
Current Subject Status: {report_data.get('current_subject_status', 'N/A')}

Best regards,
KumoClock Academic Management System
"""
        
        # Create HTML body
        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #0d6efd; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .report-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .report-table th, .report-table td {{ 
            border: 1px solid #ddd; padding: 12px; text-align: left; 
        }}
        .report-table th {{ background-color: #f2f2f2; font-weight: bold; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; 
                   color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🎓 Student Report Card</h2>
        <p>KumoClock Academic Management System</p>
    </div>
    <div class="content">
        <p>Dear Parent/Guardian,</p>
        <p>Please find below the report card for <strong>{student_name}</strong>.</p>
        <div style="padding:10px; background:#fff3cd; border:1px solid #ffeeba; border-radius:6px; color:#856404; margin-bottom:15px;">
            <strong>Do not reply:</strong> This mailbox is not monitored.
        </div>
        
        <table class="report-table">
            <tr>
                <th>Subject</th>
                <td>{report_data.get('subject', 'N/A')}</td>
            </tr>
            <tr>
                <th>Report Date Range</th>
                <td>{report_data.get('start_date', 'N/A')} to {report_data.get('end_date', 'N/A')}</td>
            </tr>
            <tr>
                <th>Highest Worksheet Completed</th>
                <td>{report_data.get('highest_ws_completed', 'N/A')}</td>
            </tr>
            <tr>
                <th>Number of Worksheets</th>
                <td>{report_data.get('num_ws', 'N/A')}</td>
            </tr>
            <tr>
                <th>Study Days</th>
                <td>{report_data.get('study_days', 'N/A')}</td>
            </tr>
            <tr>
                <th>Cumulative Study Time</th>
                <td>{report_data.get('cum_study_time', 'N/A')}</td>
            </tr>
            <tr>
                <th>Current Subject Status</th>
                <td>{report_data.get('current_subject_status', 'N/A')}</td>
            </tr>
        </table>
        
        <div class="footer">
            <p>This is an automated message from KumoClock Academic Management System. Please do not reply to this email.</p>
            <p>For any questions, please contact your institution.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Send as no-reply (prevents recipients from replying)
        return self.send_email(recipient_email, subject, body, html_body, no_reply=True)


def get_email_manager() -> EmailManager:
    """Factory function to get configured EmailManager instance"""
    return EmailManager()
