# Diploma Generator - Quick Start Guide

## Accessing the Diploma Generator

1. **From Navbar**: Click **Utilities** → **Diploma Generator**
2. **Direct URL**: Navigate to `http://localhost:5000/utilities/diploma-generator`

## Step-by-Step Usage

### Step 1: Select Diploma Type
Choose from three diploma types:
- **Certificate of Award** - For top performers
- **Certificate of Recognition** - For standard recognition
- **Certificate of Welcome** - For newcomers/participants

**Status Indicator**: Shows which templates are available (✓ = found, ✗ = missing)

### Step 2: Select Students
1. **Browse students** in the list
   - All students from your database appear sorted alphabetically
   - Each entry shows Name, Subject, and Level
   
2. **Search** (optional)
   - Type in the search box to filter students
   - Filters by name in real-time
   
3. **Select students**
   - Check the checkbox next to each student you want
   - Selected count appears at the bottom
   
4. **Use helpers**
   - **Select All**: Quickly check all visible students
   - **Clear All**: Uncheck all selected students

### Step 3: Configure Options
- **Convert to PDF**: Check this box if you want PDF files created automatically
  - Requires `docx2pdf` package (already installed)
  - PDFs saved to `/exports/diplomas_pdf`

### Step 4: Generate
1. Click **Generate Diplomas** button
2. Progress bar shows generation status
3. Results appear showing:
   - Number of DOCX files created
   - Number of PDF files created (if selected)
   - Output directory paths
   - List of successfully generated diplomas
   - Any errors or warnings

## Understanding the Results

### Success Message
```
DOCX Generated: 5 diplomas
PDF Generated: 5 files

Files saved to:
DOCX: c:\...\exports\diplomas_docx
PDF: c:\...\exports\diplomas_pdf
```

### Files Created
- **DOCX Format**: `StudentName - DiplomaType.docx`
  - Example: `John Smith - Certificate.docx`
  - Editable with Microsoft Word or LibreOffice
  - Contains replaced placeholders with actual data

- **PDF Format**: `StudentName - DiplomaType.pdf`
  - Example: `John Smith - Certificate.pdf`
  - Ready to print or email
  - Non-editable, professional appearance

## What Gets Filled In

### Student Information
- **Name**: From database (students.name)
- **Subject**: From database (students.subject)
- **Level**: From database (students.level)

### Formatted Text
- **Success Text**: Shows achievement
  - Award/Certificate: "Kumon Math Level F and Kumon Reading Level A"
  - Welcome: "Kumon Math F and Reading A Program"

### Metadata
- **Date**: Current date (e.g., "Dec 21, 2025")
- **Diploma Type**: Selected type (Award, Certificate, Welcome)

## Troubleshooting

### Problem: "No certificate templates found"
**Solution**: 
1. Download templates from GitHub:
   - https://github.com/pusoi27/award_ceremony_analysis/tree/main/data
2. Save these files to `/data` directory:
   - `Certificate of Award.docx`
   - `Certificate of Recognition.docx`
   - `Certificate of Welcome.docx`
3. Refresh the page - status should now show ✓

### Problem: "Required module not found: docx2pdf"
**Solution**:
```bash
# In terminal, run:
pip install docx2pdf
```

### Problem: "No students selected"
**Solution**: 
1. Check that students list loaded (page loads student names)
2. Click at least one checkbox
3. Check Selected count shows > 0

### Problem: PDF conversion failed
**Solution**:
1. Check DOCX files were created (should be in `/exports/diplomas_docx`)
2. Uncheck "Convert to PDF" and use DOCX files directly
3. If PDF needed, manually convert using:
   - Microsoft Word: File → Export as PDF
   - LibreOffice: File → Export as PDF
   - Online converter: www.zamzar.com (DOCX to PDF)

### Problem: Files not visible in Windows Explorer
**Solution**:
1. Check file path shown in results
2. Open folder path directly: Press `Ctrl+L` in File Explorer and paste path
3. Files are actually created but may need explorer refresh (`F5`)
4. Check `/exports/diplomas_docx` folder manually

## Advanced Tips

### Creating Custom Templates
1. Open existing template in Microsoft Word
2. Edit text, colors, fonts as desired
3. Keep placeholders:
   - `[[NAME]]` - for student name
   - `[[DATE]]` - for current date
   - `[[SUBJECTS]]` - for subjects list
   - `[[SUCCESS]]` - for achievement text
   - `[[DIPLOMA]]` - for diploma type
4. Save as DOCX in `/data` folder
5. Reload page - new template will appear

### Editing Generated Diplomas
All DOCX files are fully editable:
1. Find file in `/exports/diplomas_docx`
2. Open with Microsoft Word or LibreOffice
3. Edit any text, colors, formatting
4. Save changes
5. Convert to PDF if needed

### Batch Processing
The generator supports generating multiple diplomas at once:
- Select up to all students at once
- One click generates all
- Great for end-of-month or end-of-semester awards

### PDF Quality
If PDFs look blurry or have quality issues:
1. Check original DOCX templates
2. Ensure images in template are high resolution
3. Use "Print to PDF" instead of docx2pdf conversion:
   - Open DOCX in Word
   - File → Print
   - Select "Print to PDF"

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Search students | Click search box, start typing |
| Select all | Click "Select All" button |
| Clear all | Click "Clear All" button |
| Submit form | Click button or press Enter |

## Keyboard Navigation
- **Tab**: Move between fields
- **Space**: Toggle checkbox when focused
- **Enter**: Submit form when on button

## Common Use Cases

### Case 1: Monthly Achievement Certificates
1. Select diploma type: "Certificate of Recognition"
2. Select students from past month
3. Check "Convert to PDF"
4. Generate and print/email to parents

### Case 2: New Student Welcome
1. Select diploma type: "Certificate of Welcome"
2. Select all new students (from filter/search)
3. Generate DOCX for personalization
4. Print or email welcome certificates

### Case 3: Award Ceremony
1. Select diploma type: "Certificate of Award"
2. Select top-performing students
3. Check "Convert to PDF"
4. Frame PDFs for ceremony display
5. Print copies for student keepsakes

## FAQs

**Q: Can I edit diplomas after generation?**  
A: Yes! DOCX files are fully editable in Word or LibreOffice.

**Q: How many students can I select at once?**  
A: As many as you have in your database. The system processes them all.

**Q: Do I need Microsoft Word installed?**  
A: No! python-docx and LibreOffice work fine. Word only needed for advanced editing.

**Q: Can I use custom templates?**  
A: Yes! Replace templates in `/data` folder with your own. Keep the placeholders.

**Q: Where are my generated files?**  
A: Check results page for exact path, usually `/exports/diplomas_docx` and `/exports/diplomas_pdf`

**Q: Can I send diplomas via email?**  
A: Convert to PDF first, then attach to emails using your email client or system.

**Q: What happens if I select the same student twice?**  
A: Only one diploma is generated (database query returns unique names).

## Support

If you encounter issues:
1. Check the error message on the results page
2. Verify templates exist in `/data` folder (see "Templates found" indicator)
3. Check that students exist in database
4. Verify all required packages installed (see requirements below)
5. Check console for detailed error logs

## System Requirements

✅ **Already Installed**:
- Python 3.10+
- Flask
- python-docx
- docx2pdf
- pandas

**Optional**:
- Microsoft Word (for advanced template editing)
- LibreOffice (free alternative for DOCX editing)

---

**Last Updated**: December 21, 2025  
**Version**: Diploma Generator v1.0  
**Compatible with**: Stdytime v2.3.2+  
