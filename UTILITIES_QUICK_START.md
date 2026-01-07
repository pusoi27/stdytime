# Quick Start: KumoClock Utilities

## What's New?

A new **Utilities** menu has been added to KumoClock with three powerful features for student analysis and awards management.

## Accessing the Features

In the main navigation bar, you'll see a new "**Utilities**" menu item between "Assistants on Duty" and "Instructor"

Click it to see three options:

### 1. Student Report Card
Generate attendance reports for individual students

**Quick Start:**
1. Click Utilities → Student Report Card
2. Select a student from the dropdown
3. View their attendance data
4. Click "Print" or "Export as PDF"

**What You'll See:**
- Student contact information
- Attendance summary (total, attended, percentage)
- Last 30 days of attendance history

---

### 2. Student Evaluation
Comprehensive performance evaluation for each student

**Quick Start:**
1. Click Utilities → Student Evaluation
2. Select a student from the dropdown
3. Review their performance score and metrics

**What You'll See:**
- Student photo
- Key metrics (sessions, days attended, attendance rate)
- Performance bars and visualizations
- Earned badges/achievements
- Overall evaluation score (0-100)

---

### 3. Award Ceremony
Analyze all students and determine awards

**Quick Start:**
1. Click Utilities → Award Ceremony
2. Click "Analyze Awards"
3. View results in the table

**What You'll See:**
- Total students and award winners count
- Summary statistics
- List of all students with their awards
- Export to CSV button

**Awards Given For:**
- ✓ Perfect Attendance (100%)
- ✓ High Attendance (95%+)
- ✓ Regular Participant (10+ days)
- ✓ Dedicated Student (20+ sessions)

---

## Default Behavior

**No configuration needed!** The features work immediately with your existing student and attendance data from KumoClock's database.

---

## Optional Configuration

### Customize Award Criteria

Edit `data/award_rules.json` to change award thresholds:

```json
{
  "awards": [
    {
      "name": "Perfect Attendance",
      "conditions": [{"field": "attendance_rate", "op": "==", "value": 100}]
    },
    {
      "name": "High Attendance",
      "conditions": [{"field": "attendance_rate", "op": ">=", "value": 95}]
    }
  ]
}
```

### Change Grade Level Hierarchy

Edit `data/grade_level_criteria.json` to customize grading (for future features)

---

## Common Tasks

### Export Student Attendance
1. Report Card → Select Student → Click "Export as PDF"
2. File downloads to your computer

### Print Student Evaluation
1. Evaluation → Select Student → Click "Print"
2. Configure printer settings and print

### Get Award Results
1. Award Ceremony → Click "Analyze Awards"
2. Click "Export as CSV" to download results
3. Open in Excel/Sheets for further analysis

### Find Students with Low Attendance
1. Award Ceremony → Analyze Awards
2. Look at the Attendance Rate column
3. Students with red progress bars have low attendance

---

## Keyboard Shortcuts

While viewing results:
- Press `Ctrl+P` to print
- Press `Ctrl+S` to save (print as PDF on most systems)

---

## Data Requirements

The utilities use data that KumoClock already collects:
- Student names and contact info
- Attendance records in session_log table
- Student photos (if uploaded)

No additional data entry needed!

---

## Troubleshooting

### "No results" appears when selecting a student
- The student may not have any attendance records
- Check that session records exist in the database
- Add a session entry for the student first

### Award analysis shows unexpected results
- Check the attendance calculation (Sessions Attended / Total Sessions)
- Verify award_rules.json has correct criteria values
- Ensure sessions are properly marked as attended/absent

### Report not generating
- Make sure you selected a student from the dropdown
- Check browser console (F12) for error messages
- Try refreshing the page

---

## Need More Details?

For complete documentation, see:
- **UTILITIES_README.md** - Full feature documentation
- **INTEGRATION_SUMMARY.md** - Technical integration details

---

## Tips & Tricks

💡 **Quick Comparison:**
- Use Student Evaluation for one-to-one assessment
- Use Award Ceremony to see all students at once

💡 **Data Export:**
- Export Award results as CSV for use in Excel
- Print reports for physical records

💡 **Performance Tracking:**
- Check evaluation score to see overall student performance
- Use badges to quickly identify high-achievers

💡 **Award Planning:**
- Run award analysis before ceremonies
- Use CSV export to prepare certificates

---

## What's Next?

Planned enhancements:
- Automatic PDF certificate generation
- Email award notifications
- Historical award tracking
- Advanced filtering options
- Custom award templates

---

**Enjoy using the new Utilities menu!** 🎉
