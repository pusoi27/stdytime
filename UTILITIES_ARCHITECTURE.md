# KumoClock Utilities Structure

## Navigation Flow

```
KumoClock Dashboard
    │
    ├── Students
    │   ├── Add Student
    │   └── View / Edit / Delete
    │
    ├── Library Books
    │   ├── Add Book
    │   ├── Modify Book
    │   └── Delete Book
    │
    ├── Assistants on Duty
    │   └── [Loaded from DB]
    │
    ├── Utilities  ← NEW!
    │   ├── Student Report Card
    │   ├── Student Evaluation
    │   └── Award Ceremony
    │
    ├── Instructor
    │   ├── Reports
    │   │   ├── Payroll Staff Hours
    │   │   ├── Class Attendance
    │   │   ├── Student Attendance
    │   │   └── Loaned Books
    │   ├── Manage Assistants
    │   └── Settings
    │       └── QR Code
    │
    └── Exit
```

---

## Module Architecture

```
KumoClock/
├── app.py (Main Flask app)
│   └── imports utilities routes
│
├── routes/
│   └── utilities.py (NEW)
│       ├── register_utilities_routes()
│       ├── @app.route('/utilities') → index page
│       ├── @app.route('/utilities/report-card') → report card page
│       ├── @app.route('/utilities/evaluation') → evaluation page
│       └── @app.route('/utilities/award-ceremony') → award ceremony page
│
├── modules/
│   ├── database.py (existing)
│   ├── utils.py (existing)
│   ├── award_ceremony.py (NEW)
│   │   ├── AwardAnalyzer class
│   │   ├── GradeLevelClassifier class
│   │   ├── CertificateGenerator class
│   │   └── Helper functions
│   └── [other existing modules]
│
├── templates/
│   ├── navbar.html (modified)
│   │   └── Added Utilities menu dropdown
│   │
│   └── utilities/ (NEW folder)
│       ├── index.html (Utilities home page)
│       ├── report_card.html (Report card view)
│       ├── evaluation.html (Evaluation view)
│       └── award_ceremony.html (Award analysis view)
│
├── data/ (configurations)
│   ├── award_rules.json (NEW)
│   │   └── Award criteria definitions
│   │
│   └── grade_level_criteria.json (NEW)
│       └── Grade level hierarchy
│
├── static/ (existing)
└── UTILITIES_README.md (NEW)
```

---

## Data Flow: Report Card

```
User selects student
        ↓
JavaScript fetch()
        ↓
GET /api/utilities/report-card/<id>
        ↓
routes/utilities.py → api_get_report_card()
        ↓
Query database:
├── students table (for info)
└── session_log table (for attendance)
        ↓
Return JSON with:
├── Student info
└── Attendance records
        ↓
JavaScript receives JSON
        ↓
Populate HTML table
        ↓
Display to user
```

---

## Data Flow: Award Analysis

```
User clicks "Analyze Awards"
        ↓
JavaScript fetch POST
        ↓
POST /api/utilities/award-ceremony/analyze
        ↓
routes/utilities.py → api_analyze_awards()
        ↓
Query all students with metrics
        ↓
For each student:
├── Calculate attendance rate
├── Check award criteria
└── Build awards list
        ↓
Return JSON with results
        ↓
JavaScript receives JSON
        ↓
Display in table
        ↓
Update summary cards
```

---

## Class Hierarchy: Award Analyzer

```
AwardAnalyzer
├── __init__(criteria_config)
│   └── self.criteria (award thresholds)
│
├── analyze_student(student_data) → dict
│   ├── Calculate metrics
│   │   ├── attendance_rate
│   │   ├── consistency
│   │   └── overall_score
│   │
│   └── Check awards
│       ├── Perfect Attendance?
│       ├── High Attendance?
│       ├── Regular Participant?
│       └── Dedicated Student?
│
├── analyze_cohort(students) → list
│   └── Run analyze_student() for each
│
└── get_award_summary(analyses) → dict
    └── Calculate statistics
        ├── total_students
        ├── students_with_awards
        ├── total_awards
        └── award_distribution
```

---

## Database Tables Used

```
students
├── id (PK)
├── name
├── email
├── phone
├── photo
└── [other fields]

session_log
├── id (PK)
├── student_id (FK)
├── session_start (timestamp)
├── session_end (timestamp)
├── checked_out (boolean)
└── [other fields]
```

---

## API Endpoints Overview

```
UTILITIES ROUTES:
├── GET /utilities
│   └── Display main utilities page
│
├── GET /utilities/report-card
│   └── Display report card page
│
├── GET /api/utilities/report-card/<id>
│   └── Get report data JSON
│
├── GET /api/utilities/report-card/export/<id>
│   └── Prepare export
│
├── GET /utilities/evaluation
│   └── Display evaluation page
│
├── GET /api/utilities/evaluation/<id>
│   └── Get evaluation data JSON
│
├── GET /utilities/award-ceremony
│   └── Display award ceremony page
│
├── POST /api/utilities/award-ceremony/analyze
│   └── Run award analysis
│
└── POST /api/utilities/award-ceremony/export
    └── Export awards as CSV
```

---

## Configuration File Structure

### award_rules.json

```json
{
  "id_field": "StudentID",
  "name_field": "Name",
  "awards": [
    {
      "name": "Award Name",
      "conditions": [
        {
          "field": "metric_name",
          "op": "operator",
          "value": threshold
        }
      ]
    }
  ]
}
```

**Operators:** ==, !=, >, >=, <, <=, exists

### grade_level_criteria.json

```json
{
  "level_hierarchy": ["L", "K", "J", ..., "7A"],
  "grade_levels": {
    "Grade 1": {"math": "B", "reading": "A"},
    ...
  },
  "above_threshold": 200,
  "below_threshold": -200
}
```

---

## Feature Checklist

### Student Report Card
- [x] Page display
- [x] Student selection dropdown
- [x] Attendance summary
- [x] Attendance table (last 30 days)
- [x] Print functionality
- [x] Export button (placeholder)

### Student Evaluation
- [x] Page display
- [x] Student selection dropdown
- [x] Photo display
- [x] Performance metrics
- [x] Progress bars
- [x] Overall score calculation
- [x] Badge display
- [x] Evaluation report
- [x] Print functionality
- [x] Download button (placeholder)

### Award Ceremony
- [x] Page display
- [x] Customizable criteria inputs
- [x] Award analysis algorithm
- [x] Summary statistics
- [x] Results table
- [x] Progress bar visualization
- [x] Badge display
- [x] CSV export
- [x] Print functionality
- [ ] Certificate generation (future)

---

## File Size Summary

```
routes/utilities.py           ~280 lines
modules/award_ceremony.py     ~330 lines
templates/utilities/index.html    ~50 lines
templates/utilities/report_card.html  ~200 lines
templates/utilities/evaluation.html   ~250 lines
templates/utilities/award_ceremony.html ~280 lines
data/award_rules.json         ~25 lines
data/grade_level_criteria.json ~25 lines
templates/navbar.html         (modified, +15 lines)
app.py                        (modified, +3 lines)

TOTAL NEW CODE: ~1,550 lines
```

---

## Browser Compatibility

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires JavaScript enabled for interactive features.

---

## Performance Considerations

- Report card queries optimized with date filtering (last 30 days)
- Award analysis efficient for cohorts up to 500+ students
- No pagination needed for typical use cases
- CSV export handled client-side (no server processing)

---

## Security Notes

- All routes check database access
- Input validation on student selection
- No direct SQL exposure
- HTML escaping in templates
- CSRF protection via Flask

---

## Integration Points

```
External Dependencies
├── Flask (existing)
├── Jinja2 (existing)
├── Bootstrap 5 (existing)
├── SQLite (existing)
└── pandas (optional, graceful fallback)

Internal Dependencies
├── modules.database
├── modules.utils
└── Existing route modules
```

**No breaking changes to existing code!**
