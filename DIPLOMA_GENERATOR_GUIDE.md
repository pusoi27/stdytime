# Diploma Generator Integration - Complete

## Overview
Successfully integrated diploma/certificate generation from the GitHub `award_ceremony_analysis` project into Stdytime. This includes DOCX template support, placeholder replacement, and PDF conversion functionality.

## What Was Added

### 1. New Module: `modules/diploma_generator.py`
Complete diploma generation system with:
- **generate_diplomas()** - Creates DOCX files from templates with placeholder replacement
- **convert_diplomas_to_pdf()** - Converts DOCX diplomas to PDF files
- **generate_and_convert_diplomas()** - Combined function for both operations

**Features:**
- Support for 3 diploma types: Award, Certificate of Recognition, Welcome
- Placeholder replacement: `[[NAME]]`, `[[DATE]]`, `[[SUBJECTS]]`, `[[SUCCESS]]`, `[[DIPLOMA]]`
- Automatic level completion calculation (e.g., F70 → E completed)
- Windows COM support for advanced shape/textbox replacement (optional)
- Handles locked files with unique naming
- Batch processing with error reporting

### 2. New Route Handler: `routes/utilities.py`
Added 3 new endpoints for diploma generation:

```python
@app.route('/utilities/diploma-generator')
def diploma_generator_page()  # Main UI page

@app.route('/api/utilities/diploma-generator/generate', methods=['POST'])
def api_generate_diplomas()  # Generate diplomas

@app.route('/api/utilities/diploma-generator/templates', methods=['GET'])
def api_get_diploma_templates()  # Check available templates
```

### 3. New Template: `templates/utilities/diploma_generator.html`
Professional web interface with:
- **Diploma Type Selection** - Award, Certificate, Welcome
- **Student Multi-Select** - With search and select-all features
- **Options** - PDF conversion checkbox
- **Results Display** - Progress tracking, file listing, error reporting
- **Responsive Design** - Bootstrap 5, works on desktop and mobile

### 4. Updated Navigation
Added "Diploma Generator" to Utilities menu in navbar.html

## How It Works

### Diploma Generation Workflow:
1. User selects diploma type (Award/Certificate/Welcome)
2. User selects students from list (searchable, multi-select)
3. Optionally check "Convert to PDF"
4. Click "Generate Diplomas"
5. System:
   - Reads from database (students table: name, subject, level)
   - Creates temporary CSV with selected students
   - Loads DOCX template from `/data` directory
   - Replaces placeholders with actual values
   - Saves DOCX files to `/exports/diplomas_docx`
   - Optionally converts to PDF in `/exports/diplomas_pdf`
6. Displays results with file paths and error reporting

### Placeholder Replacement:
- `[[NAME]]` → Student name
- `[[DATE]]` → Current date (e.g., "Dec 21, 2025")
- `[[SUBJECTS]]` → Comma-separated subject list
- `[[SUCCESS]]` → Level text formatted as "Kumon Math Level F and Kumon Reading Level A Program"
- `[[DIPLOMA]]` → Diploma type

### Level Formatting:
- **Award/Certificate diplomas**: Show "completed" level (one level behind current)
  - F70 → "Kumon Math Level E"
  - AI20 → "Kumon Reading Level A"
- **Welcome diplomas**: Show current level
  - F70 → "Kumon Math F"
  - AI20 → "Kumon Reading AI"

## Installation & Setup

### Required Packages (Already Installed):
```bash
pip install python-docx docx2pdf pywin32 pandas
```

### Certificate Templates Required:
Place these DOCX files in `/data` directory:
- `Certificate of Award.docx`
- `Certificate of Recognition.docx`
- `Certificate of Welcome.docx`

Download from GitHub project if needed:
- https://github.com/pusoi27/award_ceremony_analysis/tree/main/data

### Output Directories (Auto-created):
- `/exports/diplomas_docx` - Generated DOCX files
- `/exports/diplomas_pdf` - Generated PDF files (optional)

## API Endpoints

### GET `/utilities/diploma-generator`
Render the diploma generator page

### POST `/api/utilities/diploma-generator/generate`
**Request:**
```json
{
  "students": ["John Smith", "Jane Doe"],
  "diploma_type": "Certificate",
  "include_pdf": true
}
```

**Response:**
```json
{
  "success": true,
  "generated": 2,
  "pdf_generated": 2,
  "diplomas": [
    {"Full Name": "John Smith", "Diploma": "Certificate", "Certificate": "/exports/diplomas_docx/John Smith - Certificate.docx"},
    {"Full Name": "Jane Doe", "Diploma": "Certificate", "Certificate": "/exports/diplomas_docx/Jane Doe - Certificate.docx"}
  ],
  "output_dir": "/exports/diplomas_docx",
  "pdf_dir": "/exports/diplomas_pdf"
}
```

### GET `/api/utilities/diploma-generator/templates`
Check available templates

**Response:**
```json
{
  "templates": [
    {"type": "Award", "filename": "Certificate of Award.docx", "exists": false},
    {"type": "Certificate", "filename": "Certificate of Recognition.docx", "exists": true},
    {"type": "Welcome", "filename": "Certificate of Welcome.docx", "exists": true}
  ]
}
```

## File Structure
```
modules/
├── diploma_generator.py       # New: Diploma generation logic
├── award_ceremony.py          # Updated: Integrated with diplomas
└── database.py               # Unchanged: Used for student queries

routes/
├── utilities.py              # Updated: Added 3 diploma endpoints
└── __init__.py              # Unchanged

templates/utilities/
├── diploma_generator.html    # New: Diploma UI
├── report_card.html         # Unchanged
├── evaluation.html          # Unchanged
└── award_ceremony.html      # Unchanged

data/
├── grade_level_criteria.json      # Uses reading/math level hierarchy
├── award_rules.json               # Unchanged
└── *.docx                         # Certificate templates (upload here)

exports/
├── diplomas_docx/           # Auto-created: Generated DOCX files
├── diplomas_pdf/            # Auto-created: Generated PDF files
└── students_export.csv      # Unchanged

app.py                        # Unchanged (routes already registered)
```

## Features & Capabilities

✅ **Multi-Student Processing** - Generate diplomas for multiple students at once
✅ **Template Selection** - Choose between Award, Certificate, Welcome types
✅ **Placeholder Replacement** - Automatic text substitution in templates
✅ **PDF Conversion** - Optional one-click conversion to PDF
✅ **Error Handling** - Graceful handling of missing templates, locked files, failures
✅ **Search & Multi-Select** - Easy student selection with search filter
✅ **Progress Tracking** - Real-time generation feedback
✅ **Result Display** - Clear summary with file paths and error reporting
✅ **Windows Support** - Optional Microsoft Word COM integration for advanced replacement
✅ **Cross-Platform** - Works on Windows, Linux, macOS (without Word integration)

## Error Messages & Troubleshooting

### "Required module not found"
Install missing packages:
```bash
pip install python-docx docx2pdf
```

### "Certificate templates found: ✗"
Upload DOCX templates to `/data` directory:
- Download from GitHub project
- Or create your own with placeholders `[[NAME]]`, `[[DATE]]`, etc.

### "PDF conversion failed"
Either:
1. Install docx2pdf: `pip install docx2pdf`
2. Use LibreOffice/MS Word to convert manually
3. Skip PDF conversion, keep DOCX files

### "Permission denied" errors
Usually means a file is locked. The system automatically handles this with unique filenames using timestamps.

## Integration with Award Ceremony Analysis

This implementation follows the GitHub project structure:
- Uses same DOCX template format with identical placeholders
- Supports 3 diploma types (Award, Certificate, Welcome)
- Compatible with classified student CSV format
- Level completion calculation matches original algorithm
- PDF conversion using docx2pdf library

**GitHub Reference:**
- Main script: https://github.com/pusoi27/award_ceremony_analysis/blob/main/scripts/generate_all_diplomas.py
- Certificate module: https://github.com/pusoi27/award_ceremony_analysis/blob/main/src/award_ceremony/certificates.py

## Next Steps (Optional Enhancements)

1. **Upload Custom Templates** - Add UI to upload custom DOCX templates
2. **Batch Template Management** - Create/edit templates in web interface
3. **Student Filtering** - Filter by grade, subject, level for diploma generation
4. **Signature Fields** - Add digital signature support
5. **Email Integration** - Send diplomas directly to parents/students
6. **Template Preview** - Preview generated diplomas before conversion
7. **Bulk PDF Export** - Zip all PDFs for download

## Testing

### Manual Test Steps:
1. Navigate to Utilities → Diploma Generator
2. Select diploma type
3. Select 2-3 students
4. Check "Also convert to PDF"
5. Click "Generate Diplomas"
6. Verify files appear in `/exports` directories

### Check File Generation:
```powershell
# View generated DOCX
Get-ChildItem -Path "exports/diplomas_docx" | Format-Table Name, Length, LastWriteTime

# View generated PDF
Get-ChildItem -Path "exports/diplomas_pdf" | Format-Table Name, Length, LastWriteTime
```

## Configuration

### Modify Default Settings:
Edit `modules/diploma_generator.py`:

```python
# Change template names
TEMPLATE_MAP = {
    "Custom Award": "My_Award_Template.docx",
    "Certificate": "Recognition.docx",
    "Welcome": "Welcome.docx",
}

# Add new placeholders
PLACEHOLDERS = {
    "name": "[[NAME]]",
    "diploma": "[[DIPLOMA]]",
    "date": "[[DATE]]",
    "subjects": "[[SUBJECTS]]",
    "success": "[[SUCCESS]]",
    # Add custom ones:
    "signature": "[[SIGNATURE]]",
    "seal": "[[SEAL]]",
}
```

## Compatibility

- **Python**: 3.10+ (tested on 3.13.9)
- **Flask**: 3.0+
- **OS**: Windows (with optional Word COM), Linux, macOS
- **Database**: SQLite3
- **Templates**: Microsoft Word DOCX (.docx) format

## Dependencies Installed

| Package | Version | Purpose |
|---------|---------|---------|
| python-docx | Latest | Read/write DOCX files |
| docx2pdf | Latest | Convert DOCX to PDF |
| pywin32 | Latest | Windows COM integration (optional) |
| pandas | Latest | CSV handling |

## Related Files

- [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) - Overall integration summary
- [award_ceremony.py](modules/award_ceremony.py) - Award analysis logic
- [utilities.py](routes/utilities.py) - All utilities routes
- [grade_level_criteria.json](data/grade_level_criteria.json) - Level definitions

---

**Status**: ✅ Complete and Integrated
**Date**: December 21, 2025
**Version**: Stdytime v2.3.2 + Diploma Generator v1.0
