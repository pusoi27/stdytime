"""
WhatsApp Manager Module for KumoClock
Handles WhatsApp messaging functionality using Twilio API
Version: 01.00.00
"""

from twilio.rest import Client
import os
from typing import Optional, List, Dict


class WhatsAppManager:
    """Manages WhatsApp messaging operations using Twilio"""
    
    def __init__(self, account_sid: str = None, auth_token: str = None, 
                 twilio_whatsapp_number: str = None):
        """
        Initialize WhatsApp manager with Twilio configuration
        
        Args:
            account_sid: Twilio Account SID (from environment or parameter)
            auth_token: Twilio Auth Token (from environment or parameter)
            twilio_whatsapp_number: Twilio WhatsApp number (from environment or parameter)
                                  Format: "whatsapp:+1234567890"
        """
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN', '')
        self.twilio_whatsapp_number = twilio_whatsapp_number or os.getenv('TWILIO_WHATSAPP_NUMBER', '')
        
        # Initialize Twilio client only if credentials are provided
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                self.client = None
                print(f"Warning: Failed to initialize Twilio client: {str(e)}")
        else:
            self.client = None
            print("Warning: Twilio credentials not configured. WhatsApp messaging disabled.")
    
    def is_configured(self) -> bool:
        """Check if WhatsApp is properly configured"""
        return (self.client is not None and 
                bool(self.account_sid) and 
                bool(self.auth_token) and 
                bool(self.twilio_whatsapp_number))
    
    def send_message(self, recipient_whatsapp: str, message_body: str) -> Dict[str, any]:
        """
        Send a WhatsApp message
        
        Args:
            recipient_whatsapp: Recipient's WhatsApp number 
                              Format: "+1234567890" or "whatsapp:+1234567890"
            message_body: Message text to send
            
        Returns:
            Dictionary with 'success' status and 'message_sid' or 'error'
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'WhatsApp is not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_NUMBER in environment variables.'
            }
        
        try:
            # Normalize phone number format
            if not recipient_whatsapp.startswith('whatsapp:'):
                if not recipient_whatsapp.startswith('+'):
                    recipient_whatsapp = '+' + recipient_whatsapp
                recipient_whatsapp = f'whatsapp:{recipient_whatsapp}'
            
            # Send message via Twilio WhatsApp API
            message = self.client.messages.create(
                from_=self.twilio_whatsapp_number,
                to=recipient_whatsapp,
                body=message_body
            )
            
            return {
                'success': True,
                'message_sid': message.sid,
                'message': f'WhatsApp message sent successfully (SID: {message.sid})'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send WhatsApp message: {str(e)}'
            }
    
    def send_bulk_messages(self, recipients: List[Dict[str, str]], message_body: str) -> Dict[str, any]:
        """
        Send WhatsApp messages to multiple recipients
        
        Args:
            recipients: List of dictionaries with 'name' and 'whatsapp' keys
            message_body: Message text to send to all recipients
            
        Returns:
            Dictionary with 'success' status, counts, and 'results' list
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'WhatsApp is not configured.'
            }
        
        results = []
        successful = 0
        failed = 0
        
        for recipient in recipients:
            whatsapp_number = recipient.get('whatsapp', '').strip()
            name = recipient.get('name', 'Unknown')
            
            if not whatsapp_number:
                results.append({
                    'name': name,
                    'whatsapp': 'N/A',
                    'success': False,
                    'error': 'No WhatsApp number provided'
                })
                failed += 1
                continue
            
            # Send individual message
            result = self.send_message(whatsapp_number, message_body)
            
            if result['success']:
                results.append({
                    'name': name,
                    'whatsapp': whatsapp_number,
                    'success': True,
                    'message_sid': result.get('message_sid')
                })
                successful += 1
            else:
                results.append({
                    'name': name,
                    'whatsapp': whatsapp_number,
                    'success': False,
                    'error': result.get('error')
                })
                failed += 1
        
        return {
            'success': True,
            'total_sent': successful,
            'total_failed': failed,
            'results': results
        }
    
    def send_to_student(self, student_name: str, student_whatsapp: str, 
                       message_body: str) -> Dict[str, any]:
        """
        Send a WhatsApp message to a student
        
        Args:
            student_name: Student's name
            student_whatsapp: Student's WhatsApp number
            message_body: Message text
            
        Returns:
            Dictionary with 'success' status and 'message_sid' or 'error'
        """
        if not student_whatsapp or not student_whatsapp.strip():
            return {
                'success': False,
                'error': f'Student {student_name} does not have a WhatsApp number registered.'
            }
        
        return self.send_message(student_whatsapp, message_body)
    
    def send_to_staff(self, staff_name: str, staff_whatsapp: str, 
                     message_body: str) -> Dict[str, any]:
        """
        Send a WhatsApp message to a staff member
        
        Args:
            staff_name: Staff member's name
            staff_whatsapp: Staff member's WhatsApp number
            message_body: Message text
            
        Returns:
            Dictionary with 'success' status and 'message_sid' or 'error'
        """
        if not staff_whatsapp or not staff_whatsapp.strip():
            return {
                'success': False,
                'error': f'Staff member {staff_name} does not have a WhatsApp number registered.'
            }
        
        return self.send_message(staff_whatsapp, message_body)
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Basic validation for phone number format
        
        Args:
            phone_number: Phone number to validate (with or without +)
            
        Returns:
            True if number appears to be valid, False otherwise
        """
        # Remove common formatting characters
        clean = phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        # Should be 10-15 digits (E.164 standard)
        return clean.isdigit() and 10 <= len(clean) <= 15
