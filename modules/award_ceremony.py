"""
Award Ceremony Analysis Module
Integrates award ceremony analysis functionality into Stdytime

This module provides utilities for:
- Analyzing student performance
- Determining awards based on configurable criteria
- Generating certificates
- Grade-level classification
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

# Re-export advanced award/rules utilities from the upstream award_ceremony_analysis project
from modules.award_rules_engine import (
    classify_grade_level,
    process_awards,
    classify_student_list_by_subject,
    build_level_index_mapping,
    normalize_level,
    extract_level_parts,
    get_worksheets_per_day,
)
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class AwardAnalyzer:
    """Analyze student performance and determine awards"""
    
    def __init__(self, criteria_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the award analyzer with optional criteria configuration
        
        Args:
            criteria_config: Dictionary with award criteria
        """
        self.criteria = criteria_config or self._default_criteria()
    
    def _default_criteria(self) -> Dict[str, Any]:
        """Get default award criteria"""
        return {
            'perfect_attendance_threshold': 100,
            'high_attendance_threshold': 95,
            'regular_participant_sessions': 10,
            'dedicated_student_sessions': 20,
            'consistency_threshold': 0.9,
        }
    
    def analyze_student(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single student and determine awards
        
        Args:
            student_data: Dictionary with student metrics
                {
                    'id': student_id,
                    'name': student_name,
                    'total_sessions': int,
                    'attended': int,
                    'days_attended': int
                }
        
        Returns:
            Dictionary with analysis results including awards
        """
        awards = []
        metrics = self._calculate_metrics(student_data)
        
        # Check award criteria
        if metrics['attendance_rate'] == 100:
            awards.append('Perfect Attendance')
        elif metrics['attendance_rate'] >= self.criteria['high_attendance_threshold']:
            awards.append('High Attendance')
        
        if student_data['total_sessions'] >= self.criteria['dedicated_student_sessions']:
            awards.append('Dedicated Student')
        
        if student_data['days_attended'] >= self.criteria['regular_participant_sessions']:
            awards.append('Regular Participant')
        
        return {
            'student': student_data,
            'metrics': metrics,
            'awards': awards,
            'score': self._calculate_overall_score(metrics)
        }
    
    def _calculate_metrics(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for a student"""
        total = student_data.get('total_sessions', 0) or 0
        attended = student_data.get('attended', 0) or 0
        days = student_data.get('days_attended', 0) or 0
        
        attendance_rate = (attended / total * 100) if total > 0 else 0
        
        return {
            'attendance_rate': round(attendance_rate, 2),
            'sessions_attended': attended,
            'total_sessions': total,
            'days_attended': days,
            'consistency': round(attendance_rate / 100, 2) if total > 0 else 0
        }
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        # Score based on attendance rate (0-100)
        return metrics['attendance_rate']
    
    def analyze_cohort(self, students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze multiple students
        
        Args:
            students: List of student data dictionaries
        
        Returns:
            List of analysis results
        """
        results = []
        for student in students:
            results.append(self.analyze_student(student))
        return results
    
    def get_award_summary(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for award analysis
        
        Args:
            analyses: List of analysis results
        
        Returns:
            Summary statistics
        """
        total_students = len(analyses)
        students_with_awards = sum(1 for a in analyses if a['awards'])
        total_awards = sum(len(a['awards']) for a in analyses)
        
        avg_attendance = sum(a['metrics']['attendance_rate'] for a in analyses) / total_students if total_students > 0 else 0
        
        award_counts = {}
        for analysis in analyses:
            for award in analysis['awards']:
                award_counts[award] = award_counts.get(award, 0) + 1
        
        return {
            'total_students': total_students,
            'students_with_awards': students_with_awards,
            'total_awards': total_awards,
            'average_attendance': round(avg_attendance, 2),
            'award_distribution': award_counts
        }


class GradeLevelClassifier:
    """Classify students by grade level based on worksheet levels"""
    
    def __init__(self, criteria_config: Optional[Dict[str, Any]] = None):
        """
        Initialize classifier with optional criteria
        
        Args:
            criteria_config: Dictionary with grade level criteria
        """
        self.criteria = criteria_config or self._default_criteria()
        self._build_level_hierarchy()
    
    def _default_criteria(self) -> Dict[str, Any]:
        """Get default grade level criteria"""
        return {
            'above_threshold': 200,  # page_index difference for above
            'below_threshold': -200,  # page_index difference for below
        }
    
    def _build_level_hierarchy(self):
        """Build level hierarchy from criteria"""
        # Reading level progression: from least advanced (7A) to most advanced (L)
        self.reading_level_order = [
            "7A", "6A", "5A", "4A", "3A", "2A", "AI", "AII",
            "BI", "BII", "CI", "CII", "DI", "DII", "EI", "EII", "FI", "FII", "GI", "GII", "HI",
            "HII", "II", "III", "J", "K", "L"
        ]
        
        # Math level progression: from least advanced (6A) to most advanced (L)
        self.math_level_order = [
            "6A", "5A", "4A", "3A", "2A", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"
        ]
        
        # Default to reading levels if not specified
        self.level_order = self.reading_level_order
    
    def classify(self, student_level: Optional[str], expected_level: Optional[str], subject: Optional[str] = None) -> str:
        """
        Classify student relative to expected level
        
        Args:
            student_level: Student's current level (e.g., 'F80')
            expected_level: Expected level for grade/subject (e.g., 'D35')
            subject: Subject type ('reading' or 'math') to use correct level hierarchy
        
        Returns:
            Classification: 'ABOVE GRADE LEVEL', 'AT GRADE LEVEL', or 'BELOW GRADE LEVEL'
        """
        if not student_level or not expected_level:
            return 'UNCLASSIFIED'
        
        # Select appropriate level order based on subject
        if subject and subject.lower() == 'math':
            self.level_order = self.math_level_order
        else:
            self.level_order = self.reading_level_order
        
        student_base = self._extract_base_level(student_level)
        expected_base = self._extract_base_level(expected_level)
        
        student_idx = self._get_level_index(student_base)
        expected_idx = self._get_level_index(expected_base)
        
        if student_idx is None or expected_idx is None:
            return 'UNCLASSIFIED'
        
        diff = student_idx - expected_idx
        
        if diff > 0:
            return 'ABOVE GRADE LEVEL'
        elif diff < 0:
            return 'BELOW GRADE LEVEL'
        else:
            return 'AT GRADE LEVEL'
    
    def _extract_base_level(self, level: str) -> str:
        """Extract base level from full level string"""
        if not level:
            return ''
        # e.g., 'F80' -> 'F', '3A20' -> '3A'
        s = str(level).strip().upper().replace(' ', '')
        # Find where digits start
        i = 0
        while i < len(s) and not s[i].isdigit():
            i += 1
        return s[:i]
    
    def _get_level_index(self, level: str) -> Optional[int]:
        """Get index of level in hierarchy (lower index = more advanced)"""
        if not level:
            return None
        level = str(level).strip().upper()
        try:
            return self.level_order.index(level)
        except ValueError:
            return None


class CertificateGenerator:
    """Generate certificates for award ceremony"""
    
    @staticmethod
    def generate_certificate_data(student_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate certificate data for a student
        
        Args:
            student_analysis: Analysis result with awards
        
        Returns:
            Dictionary with certificate content
        """
        student = student_analysis['student']
        awards = student_analysis['awards']
        
        # Determine certificate type
        if not awards:
            cert_type = 'Participation'
        elif 'Perfect Attendance' in awards or 'High Attendance' in awards:
            cert_type = 'Achievement'
        else:
            cert_type = 'Recognition'
        
        return {
            'type': cert_type,
            'name': student['name'],
            'awards': '; '.join(awards) if awards else 'Participation',
            'date': datetime.now().strftime('%B %d, %Y'),
            'achievements': awards
        }
    
    @staticmethod
    def format_certificate_text(cert_data: Dict[str, str]) -> str:
        """Format certificate data as readable text"""
        text = f"""
=== CERTIFICATE OF {cert_data['type'].upper()} ===

This is to certify that

{cert_data['name']}

Has demonstrated excellence in:
"""
        for achievement in cert_data['achievements']:
            text += f"\n  • {achievement}"
        
        text += f"""

Issued on {cert_data['date']}

Congratulations on your outstanding performance!
"""
        return text


def load_award_config(config_path: str) -> Dict[str, Any]:
    """
    Load award configuration from JSON file
    
    Args:
        config_path: Path to configuration JSON file
    
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return {}


def save_awards_to_csv(analyses: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save award analysis results to CSV file
    
    Args:
        analyses: List of analysis results
        output_path: Path to write CSV file
    """
    if not HAS_PANDAS:
        # Fallback without pandas
        with open(output_path, 'w') as f:
            f.write('StudentID,Name,Total_Sessions,Sessions_Attended,Attendance_Rate,Days_Attended,Awards\n')
            for analysis in analyses:
                student = analysis['student']
                metrics = analysis['metrics']
                awards = '; '.join(analysis['awards']) if analysis['awards'] else 'No Awards'
                f.write(f"{student.get('id')},{student.get('name')},{metrics['total_sessions']},{metrics['sessions_attended']},{metrics['attendance_rate']}%,{metrics['days_attended']},\"{awards}\"\n")
    else:
        rows = []
        for analysis in analyses:
            student = analysis['student']
            metrics = analysis['metrics']
            awards = '; '.join(analysis['awards']) if analysis['awards'] else 'No Awards'
            
            rows.append({
                'StudentID': student.get('id'),
                'Name': student.get('name'),
                'Total_Sessions': metrics['total_sessions'],
                'Sessions_Attended': metrics['sessions_attended'],
                'Attendance_Rate': f"{metrics['attendance_rate']}%",
                'Days_Attended': metrics['days_attended'],
                'Awards': awards
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
    
    print(f"Award results saved to {output_path}")


# Export main classes
__all__ = [
    'AwardAnalyzer',
    'GradeLevelClassifier',
    'CertificateGenerator',
    'load_award_config',
    'save_awards_to_csv',
    # Upstream award_ceremony_analysis integrations
    'classify_grade_level',
    'process_awards',
    'classify_student_list_by_subject',
    'build_level_index_mapping',
    'normalize_level',
    'extract_level_parts',
    'get_worksheets_per_day',
]
