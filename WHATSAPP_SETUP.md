# WhatsApp Integration Guide for KumoClock

## Overview

WhatsApp integration has been successfully added to KumoClock! The system now allows you to:

- **Send direct messages** to individual students and staff members
- **Broadcast messages** to multiple recipients at once
- **Manage WhatsApp contact numbers** for students and staff
- **Track message delivery** with Twilio message IDs

## Prerequisites

You need a **Twilio account** to use WhatsApp messaging:
- Visit: https://www.twilio.com
- Sign up for a free trial account
- Get your WhatsApp credentials

## Setup Instructions

### Step 1: Get Twilio Credentials

1. Sign up for a Twilio account: https://www.twilio.com/try-twilio
2. Go to the Twilio Console: https://console.twilio.com
3. Find your credentials in **Account Info**:
   - **Account SID** (starts with "AC")
   - **Auth Token** (long alphanumeric string)
4. Set up WhatsApp integration:
   - Go to: https://console.twilio.com/us/develop/sms/try-it-out/whatsapp-learn
   - Follow the setup wizard to get your **WhatsApp number**
   - The number will be in format: `whatsapp:+1234567890`

### Step 2: Configure Environment Variables

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your Twilio credentials:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
   ```

3. Save the file

### Step 3: Restart the Application

After updating the `.env` file, restart KumoClock:
```bash
python app.py
```

The application will automatically:
- Initialize the database with WhatsApp contact fields
- Verify your Twilio credentials
- Enable WhatsApp messaging features

## Usage

### Accessing WhatsApp Features

1. Open the KumoClock dashboard
2. Look for the **WhatsApp** menu item in the navigation
3. You'll see three options:
   - **Send to Students** - Send messages to individual students
   - **Send to Staff** - Send messages to staff members
   - **Broadcast Messages** - Send to multiple recipients at once

### Sending Messages to Students

1. Click **Send to Students**
2. Select a student from the dropdown
3. If the student doesn't have a WhatsApp number:
   - Check the "Update WhatsApp Number" checkbox
   - Enter their WhatsApp number (include country code: +1, +44, etc.)
4. Type your message
5. Click **Send WhatsApp**
6. You'll see a confirmation with the message ID

### Sending Messages to Staff

1. Click **Send to Staff**
2. Select a staff member
3. Update their WhatsApp number if needed (same format as students)
4. Type your message
5. Click **Send WhatsApp**

### Broadcasting Messages

1. Click **Broadcast Messages**
2. Choose recipient type (Students or Staff)
3. Select multiple recipients (hold Ctrl/Cmd to multi-select)
4. Type your message
5. Click **Send Broadcast**
6. View detailed delivery results

## Database Changes

The following columns have been automatically added:

**students table:**
- `whatsapp TEXT` - Student's WhatsApp number

**staff table:**
- `whatsapp TEXT` - Staff member's WhatsApp number

## API Endpoints

All messaging operations are available via REST API:

### Check Configuration Status
```
GET /api/whatsapp/status
```

### Send to Student
```
POST /api/whatsapp/send-to-student
Content-Type: application/json

{
  "student_id": 1,
  "message": "Hello Student!"
}
```

### Send to Staff
```
POST /api/whatsapp/send-to-staff
Content-Type: application/json

{
  "staff_id": 1,
  "message": "Hello Staff Member!"
}
```

### Broadcast to Students
```
POST /api/whatsapp/broadcast-students
Content-Type: application/json

{
  "student_ids": [1, 2, 3],
  "message": "Important announcement!"
}
```

### Broadcast to Staff
```
POST /api/whatsapp/broadcast-staff
Content-Type: application/json

{
  "staff_ids": [1, 2],
  "message": "Important announcement!"
}
```

### Update Student WhatsApp Number
```
POST /api/whatsapp/update-student-whatsapp
Content-Type: application/json

{
  "student_id": 1,
  "whatsapp": "+1234567890"
}
```

### Update Staff WhatsApp Number
```
POST /api/whatsapp/update-staff-whatsapp
Content-Type: application/json

{
  "staff_id": 1,
  "whatsapp": "+1234567890"
}
```

## Twilio Sandbox vs Production

### Sandbox Mode (Free Trial)
- Good for testing
- Messages only work with pre-approved numbers
- You must send a message to your Twilio WhatsApp number first
- No cost, but limited to 100 messages/day

### Production Mode
- After upgrading your account
- Can message any WhatsApp number
- Requires approval from Meta/Facebook
- Costs vary based on message volume
- Recommended for live deployments

## Phone Number Format

WhatsApp numbers should include:
- **Country code** (e.g., +1 for USA, +44 for UK, +91 for India)
- **Area code and number** (e.g., +1-555-123-4567)

Examples of valid formats:
- `+1234567890`
- `+44-20-7946-0958`
- `+91-9876543210`

## Troubleshooting

### "WhatsApp is not configured"
- Check that `.env` file exists with Twilio credentials
- Verify credentials are correct in Twilio Console
- Restart the application
- Check console for specific error messages

### "Invalid phone number format"
- Ensure number includes country code (starts with +)
- Remove any spaces or special characters
- Number should be 10-15 digits (including country code)

### Messages not sending
- Confirm recipient's number is in Twilio's WhatsApp sandbox
- In sandbox mode, contact Twilio support to add numbers
- Check Twilio Console for message logs and error details
- Verify WhatsApp account has internet connectivity

### "Student/Staff not found"
- Verify the ID exists in the database
- Check that the student/staff member is in the active list

## Security Considerations

1. **Never commit `.env` file to version control**
   - Add `.env` to `.gitignore`
   - Only commit `.env.example`

2. **Protect your credentials**
   - Never share your Auth Token
   - If compromised, regenerate immediately in Twilio Console

3. **Message Privacy**
   - Messages are sent directly to Twilio servers
   - Twilio logs message metadata
   - Personal contact numbers are stored in KumoClock database

## Support & Resources

- **Twilio Documentation**: https://www.twilio.com/docs/whatsapp
- **Twilio WhatsApp API**: https://www.twilio.com/docs/whatsapp/api
- **Twilio Console**: https://console.twilio.com
- **Pricing Calculator**: https://www.twilio.com/pricing/messaging

## Files Added/Modified

### New Files:
- `modules/whatsapp_manager.py` - WhatsApp messaging logic
- `routes/whatsapp.py` - WhatsApp web routes and API endpoints
- `templates/whatsapp/dashboard.html` - WhatsApp main dashboard
- `templates/whatsapp/students.html` - Send to students form
- `templates/whatsapp/staff.html` - Send to staff form
- `templates/whatsapp/broadcast.html` - Broadcast message form

### Modified Files:
- `modules/database.py` - Added WhatsApp columns to database schema
- `app.py` - Registered WhatsApp routes
- `.env.example` - Added Twilio configuration template

### Dependencies Added:
- `twilio` - Official Twilio Python SDK

## Next Steps

1. **Set up Twilio account**: Visit https://www.twilio.com
2. **Add Twilio credentials** to `.env` file
3. **Restart the application**
4. **Test sending a message** to yourself or a team member
5. **Add WhatsApp numbers** to student/staff profiles
6. **Start using** for announcements and communications

## Example Use Cases

- **Emergency Alerts**: Notify students/parents of school closures
- **Assignment Reminders**: Remind students about upcoming deadlines
- **Progress Updates**: Send performance reports to parents
- **Event Announcements**: Notify about field trips, assemblies, etc.
- **Staff Coordination**: Quick messages to coordinate activities
- **Appointment Reminders**: Alert students about meetings or sessions

Enjoy your new WhatsApp integration! 🚀
