# KumoClock Utilities Module

This document describes the new Utilities menu and its features integrated into KumoClock.

## Features

### 1. Student Report Card
**Location:** Utilities → Student Report Card

Generate detailed attendance and performance reports for individual students.

**Features:**
- View student information (name, email, phone)
- View attendance summary (total sessions, attended, attendance rate)
- Display recent attendance history (last 30 days)
- Export as PDF
- Print functionality

**Data displayed:**
- Student personal information
- Total sessions logged
- Sessions attended
- Attendance rate percentage
- Date-by-date attendance records

---

### 2. Student Evaluation
**Location:** Utilities → Student Evaluation

Comprehensive performance evaluation and progress tracking for each student.

**Features:**
- Student photo display
- Key metrics: Total sessions, attended, days attended, attendance rate
- Performance bars (consistency and frequency)
- Overall evaluation score (0-100)
- Performance badges (Perfect Attendance, Consistent Participant, Active Student)
- Detailed evaluation report
- Download and print functionality

**Evaluation Metrics:**
- Attendance rate analysis
- Participation consistency
- Session frequency
- Overall score calculation

**Badges awarded:**
- **Perfect Attendance:** 95%+ attendance rate
- **Consistent Participant:** 20+ days attended
- **Active Student:** 15+ sessions attended

---

### 3. Award Ceremony Analysis
**Location:** Utilities → Award Ceremony

Analyze student performance and determine awards based on configurable criteria.

**Features:**
- Customizable award criteria (minimum attendance %, minimum sessions)
- Award analysis for all students
- Summary statistics
- Award results table with progress bars
- Export results as CSV
- Certificate generation (coming soon)
- Print functionality

**Default Awards:**
- **Perfect Attendance:** 100% attendance rate
- **High Attendance:** 95%+ attendance rate
- **Regular Participant:** 10+ days attended
- **Dedicated Student:** 20+ sessions attended

**Award Summary Shows:**
- Total students analyzed
- Number of award winners
- Total awards earned
- Average attendance percentage

---

## Configuration Files

### Award Rules Configuration
**File:** `data/award_rules.json`

Defines award criteria using a rule-based system:

```json
{
  "id_field": "StudentID",
  "name_field": "Name",
  "awards": [
    {
      "name": "Perfect Attendance",
      "conditions": [
        {"field": "attendance_rate", "op": "==", "value": 100}
      ]
    }
  ]
}
```

**Operators:** `==`, `!=`, `>`, `>=`, `<`, `<=`, `exists`

### Grade Level Criteria
**File:** `data/grade_level_criteria.json`

Defines grade level hierarchy and thresholds:

```json
{
  "level_hierarchy": ["L", "K", "J", "...", "7A"],
  "above_threshold": 200,
  "below_threshold": -200
}
```

---

## API Endpoints

### Student Report Card
- `GET /utilities/report-card` - Display report card page
- `GET /api/utilities/report-card/<student_id>` - Get student report data
- `GET /api/utilities/report-card/export/<student_id>` - Export report

### Student Evaluation
- `GET /utilities/evaluation` - Display evaluation page
- `GET /api/utilities/evaluation/<student_id>` - Get evaluation data

### Award Ceremony
- `GET /utilities/award-ceremony` - Display award ceremony page
- `POST /api/utilities/award-ceremony/analyze` - Analyze awards
- `POST /api/utilities/award-ceremony/export` - Export awards

---

## Module: Award Ceremony

**File:** `modules/award_ceremony.py`

### Classes

#### AwardAnalyzer
Analyzes student performance and determines awards.

```python
from modules.award_ceremony import AwardAnalyzer

analyzer = AwardAnalyzer()
result = analyzer.analyze_student({
    'id': 1,
    'name': 'John Doe',
    'total_sessions': 20,
    'attended': 19,
    'days_attended': 15
})
```

**Methods:**
- `analyze_student(student_data)` - Analyze single student
- `analyze_cohort(students)` - Analyze multiple students
- `get_award_summary(analyses)` - Get summary statistics

#### GradeLevelClassifier
Classifies students by grade level.

```python
from modules.award_ceremony import GradeLevelClassifier

classifier = GradeLevelClassifier()
classification = classifier.classify('F80', 'D35')
# Returns: 'ABOVE GRADE LEVEL'
```

**Methods:**
- `classify(student_level, expected_level)` - Classify student

#### CertificateGenerator
Generates certificate data for award ceremony.

```python
from modules.award_ceremony import CertificateGenerator

cert_data = CertificateGenerator.generate_certificate_data(analysis)
```

---

## Integration with GitHub Repository

This module integrates functionality from:
**https://github.com/pusoi27/award_ceremony_analysis**

Key features from that project that are implemented:
- Award rules engine
- Grade-level classification system
- Certificate generation (enhanced)
- CSV data processing

The KumoClock implementation adapts these features for the web-based student management system.

---

## How to Use

### 1. Generate Student Report Card
1. Go to Utilities → Student Report Card
2. Select a student from the dropdown
3. View attendance data and summary
4. Click "Export as PDF" or "Print"

### 2. View Student Evaluation
1. Go to Utilities → Student Evaluation
2. Select a student from the dropdown
3. Review performance metrics and overall score
4. Check earned badges
5. Download or print the evaluation

### 3. Run Award Ceremony Analysis
1. Go to Utilities → Award Ceremony
2. (Optional) Adjust award criteria settings
3. Click "Analyze Awards"
4. Review results showing students and their awards
5. Export results as CSV
6. (Coming soon) Generate certificates for winners

---

## Customization

### Add Custom Awards

Edit `data/award_rules.json` to add new awards:

```json
{
  "name": "Top Performer",
  "conditions": [
    {"field": "attendance_rate", "op": ">=", "value": 90},
    {"field": "total_sessions", "op": ">=", "value": 15}
  ]
}
```

### Modify Award Criteria

Edit `data/award_rules.json` to change thresholds:
- Change `"value": 95` to require different attendance percentage
- Change `"value": 10` to require different number of sessions

### Adjust Grade Level Thresholds

Edit `data/grade_level_criteria.json`:
- Modify `"above_threshold"` and `"below_threshold"` values
- Update `"level_hierarchy"` to match your grading system

---

## Future Enhancements

- [ ] PDF certificate generation with templates
- [ ] Batch certificate creation for all award winners
- [ ] Email award notifications to students/parents
- [ ] Historical award tracking
- [ ] Custom award templates
- [ ] Award ceremony event scheduling
- [ ] Student comparison reports
- [ ] Advanced filtering and search in results

---

## Troubleshooting

### Report card shows no data
- Ensure student has session records in the database
- Check that session_log table has entries for the student

### Award analysis returns no awards
- Verify award_rules.json criteria match your data
- Check that students meet the minimum session requirements
- Review the attendance rate calculations

### Evaluation badges not showing
- Verify the metrics thresholds in the evaluation code
- Check that student has sufficient days attended

---

## Support

For issues or questions about the Utilities module, please refer to:
- The inline code documentation
- Configuration file examples
- The GitHub repository: https://github.com/pusoi27/award_ceremony_analysis
