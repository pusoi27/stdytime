# Email Configuration Setup Guide for Stdytime

## Quick Setup

### Option 1: Gmail (Recommended)

1. **Enable 2-Factor Authentication**:
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Google will generate a 16-character password

3. **Update .env file**:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

### Option 2: Outlook / Office 365

```
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SENDER_EMAIL=your-email@outlook.com
SENDER_PASSWORD=your-password
```

### Option 3: Yahoo Mail

```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SENDER_EMAIL=your-email@yahoo.com
SENDER_PASSWORD=your-app-specific-password
```

Note: Yahoo requires an app-specific password from https://login.yahoo.com/account/security

### Option 4: Other SMTP Provider

Contact your email provider for SMTP settings.

## Testing the Configuration

After configuring .env, restart the Flask app:

```powershell
cd c:\Users\octav\AppData\Local\Programs\Python\Python312\005_Stdytime
.venv\Scripts\python.exe app.py
```

Then try sending a test email from the Student Report Card page.

## Important Notes

- ⚠️ **Never** commit the `.env` file to Git (it's in .gitignore)
- Keep your app-specific password secure
- For Gmail, regular account passwords won't work - you must use app-specific password
- The SENDER_EMAIL will appear as the "From" address in emails

## Troubleshooting

**Error: "Authentication failed"**
- Verify credentials are correct in .env
- For Gmail: ensure you're using app-specific password, not account password
- Check that 2-Factor Authentication is enabled

**Error: "SMTP error: [SSL: CERTIFICATE_VERIFY_FAILED]"**
- This is a TLS/SSL issue
- Make sure SMTP_PORT is 587 (not 465 for standard TLS)

**Error: "Connection refused"**
- Verify SMTP_SERVER and SMTP_PORT are correct
- Check internet connectivity
- Ensure firewall isn't blocking port 587
