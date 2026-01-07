from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Callable, Optional
from pathlib import Path
from datetime import datetime

import pandas as pd


OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: (a is not None and b is not None and a > b),
    ">=": lambda a, b: (a is not None and b is not None and a >= b),
    "<": lambda a, b: (a is not None and b is not None and a < b),
    "<=": lambda a, b: (a is not None and b is not None and a <= b),
}


MONTH_MAP = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sept",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


# Worksheets per day mapping (from Levels_Index.xlsx)
WORKSHEETS_PER_DAY_STATIC: Dict[str, int] = {
    # Reading
    "7A": 10,
    "6A": 10,
    "5A": 10,
    "4A": 10,
    "3A": 10,
    "2A": 10,
    "AI": 10,
    "AII": 10,
    "BI": 8,
    "BII": 8,
    "CI": 5,
    "CII": 5,
    "DI": 4,
    "DII": 4,
    "EI": 3,
    "EII": 3,
    "FI": 3,
    "FII": 3,
    "GI": 2,
    "GII": 2,
    "HI": 2,
    "HII": 2,
    "II": 1,
    "III": 1,
    "J_reading": 1,
    "K_reading": 1,
    "L_reading": 1,
    # Math
    "6A_math": 10,
    "5A_math": 10,
    "4A_math": 10,
    "3A_math": 10,
    "2A_math": 10,
    "A": 8,
    "B": 5,
    "C": 4,
    "D": 3,
    "E": 2,
    "F": 2,
    "G": 2,
    "H": 2,
    "I": 1,
    "J_math": 1,
    "K_math": 1,
    "L_math": 1,
}


# Static reading page-index mapping (from Levels_By_grade.xlsx)
READING_PAGE_INDEX_STATIC: Dict[str, int] = {
    "7A40": 40,
    "7A80": 80,
    "7A120": 120,
    "7A160": 160,
    "6A1": 201,
    "6A40": 240,
    "6A80": 280,
    "6A120": 320,
    "6A160": 360,
    "6A200": 400,
    "5A40": 440,
    "5A80": 480,
    "5A120": 520,
    "5A160": 560,
    "4A1": 601,
    "4A40": 640,
    "4A80": 680,
    "4A120": 720,
    "4A160": 760,
    "4A200": 800,
    "3A20": 820,
    "3A40": 840,
    "3A80": 880,
    "3A120": 920,
    "3A160": 960,
    "2A1": 1001,
    "2A40": 1040,
    "2A80": 1080,
    "2A120": 1120,
    "2A160": 1160,
    "2A200": 1200,
    "AI40": 1240,
    "AI80": 1280,
    "AI120": 1320,
    "AI160": 1360,
    "AII1": 1401,
    "AII40": 1440,
    "AII80": 1480,
    "AII120": 1520,
    "AII160": 1560,
    "AII200": 1600,
    "BI1": 1601,
    "BI10": 1625,
    "BI40": 1640,
    "BI80": 1680,
    "BI120": 1720,
    "BI160": 1760,
    "BII1": 1801,
    "BII40": 1840,
    "BII80": 1880,
    "BII120": 1920,
    "BII160": 1960,
    "BII200": 2000,
    "CI40": 2040,
    "CI80": 2080,
    "CI120": 2120,
    "CI160": 2160,
    "CII1": 2201,
    "CII40": 2240,
    "CII80": 2280,
    "CII120": 2320,
    "CII160": 2360,
    "CII200": 2400,
    "DI40": 2440,
    "DI80": 2480,
    "DI120": 2520,
    "DI160": 2560,
    "DII1": 2601,
    "DII40": 2640,
    "DII80": 2680,
    "DII120": 2720,
    "DII160": 2760,
    "DII200": 2800,
    "EI40": 2840,
    "EI80": 2880,
    "EI120": 2920,
    "EI160": 2960,
    "EII1": 3001,
    "EII40": 3040,
    "EII80": 3080,
    "EII120": 3120,
    "EII160": 3160,
    "EII200": 3200,
    "FI40": 3240,
    "FI80": 3280,
    "FI120": 3320,
    "FI160": 3360,
    "FII1": 3401,
    "FII40": 3440,
    "FII80": 3480,
    "FII120": 3520,
    "FII160": 3560,
    "FII200": 3600,
    "GI40": 3640,
    "GI80": 3680,
    "GI120": 3720,
    "GI160": 3760,
    "GII1": 3801,
    "GII40": 3840,
    "GII80": 3880,
    "GII120": 3920,
    "GII160": 3960,
    "GII200": 4000,
    "HI40": 4040,
    "HI80": 4080,
    "HI120": 4120,
    "HI160": 4160,
    "HII1": 4201,
    "HII40": 4240,
    "HII80": 4280,
    "HII120": 4320,
    "HII160": 4360,
    "HII200": 4400,
    "II40": 4440,
    "II80": 4480,
    "II120": 4520,
    "II160": 4560,
    "III1": 4601,
    "III40": 4640,
    "III80": 4680,
    "III120": 4720,
    "III160": 4760,
    "III200": 4800,
    "J20": 4820,
    "J40": 4840,
    "J60": 4860,
    "J80": 4880,
    "J100": 4900,
    "J120": 4920,
    "J140": 4940,
    "J160": 4960,
    "J180": 4980,
    "J200": 5000,
    "K20": 5020,
    "K40": 5040,
    "K60": 5060,
    "K80": 5080,
    "K100": 5100,
    "K120": 5120,
    "K140": 5140,
    "K160": 5160,
    "K180": 5180,
    "K200": 5200,
    "L20": 5220,
    "L40": 5240,
    "L60": 5260,
    "L80": 5280,
    "L100": 5300,
    "L120": 5320,
    "L140": 5340,
    "L160": 5360,
    "L180": 5380,
    "L200": 5400,
}


# Static math page-index mapping (from Levels_By_grade.xlsx)
MATH_PAGE_INDEX_STATIC: Dict[str, int] = {
    "6A40": 40,
    "6A80": 80,
    "6A120": 120,
    "6A160": 160,
    "5A1": 201,
    "5A40": 240,
    "5A80": 280,
    "5A120": 320,
    "5A160": 360,
    "5A200": 400,
    "4A40": 440,
    "4A80": 480,
    "4A120": 520,
    "4A160": 560,
    "3A1": 601,
    "3A40": 640,
    "3A80": 680,
    "3A120": 720,
    "3A160": 760,
    "3A200": 800,
    "2A20": 820,
    "2A40": 840,
    "2A60": 860,
    "2A80": 880,
    "2A100": 900,
    "2A120": 920,
    "2A140": 940,
    "2A160": 960,
    "2A180": 980,
    "2A200": 1000,
    "A20": 1020,
    "A40": 1040,
    "A60": 1060,
    "A80": 1080,
    "A100": 1100,
    "A120": 1120,
    "A140": 1140,
    "A160": 1160,
    "A180": 1180,
    "A200": 1200,
    "B20": 1220,
    "B40": 1240,
    "B60": 1260,
    "B80": 1280,
    "B100": 1300,
    "B120": 1320,
    "B140": 1340,
    "B160": 1360,
    "B180": 1380,
    "B200": 1400,
    "C20": 1420,
    "C40": 1440,
    "C60": 1460,
    "C80": 1480,
    "C100": 1500,
    "C120": 1520,
    "C140": 1540,
    "C160": 1560,
    "C180": 1580,
    "C200": 1600,
    "D20": 1620,
    "D40": 1640,
    "D60": 1660,
    "D80": 1680,
    "D100": 1700,
    "D120": 1720,
    "D140": 1740,
    "D160": 1760,
    "D180": 1780,
    "D200": 1800,
    "E20": 1820,
    "E40": 1840,
    "E60": 1860,
    "E80": 1880,
    "E100": 1900,
    "E120": 1920,
    "E140": 1940,
    "E160": 1960,
    "E180": 1980,
    "E200": 2000,
    "F20": 2020,
    "F40": 2040,
    "F60": 2060,
    "F80": 2080,
    "F100": 2100,
    "F120": 2120,
    "F140": 2140,
    "F160": 2160,
    "F180": 2180,
    "F200": 2200,
    "G20": 2220,
    "G40": 2240,
    "G60": 2260,
    "G80": 2280,
    "G100": 2300,
    "G120": 2320,
    "G140": 2340,
    "G160": 2360,
    "G180": 2380,
    "G200": 2400,
    "H20": 2420,
    "H40": 2440,
    "H60": 2460,
    "H80": 2480,
    "H100": 2500,
    "H120": 2520,
    "H140": 2540,
    "H160": 2560,
    "H180": 2580,
    "H200": 2600,
    "I20": 2620,
    "I40": 2640,
    "I60": 2660,
    "I80": 2680,
    "I100": 2700,
    "I120": 2720,
    "I140": 2740,
    "I160": 2760,
    "I180": 2780,
    "I200": 2800,
    "J20": 2820,
    "J40": 2840,
    "J60": 2860,
    "J80": 2880,
    "J100": 2900,
    "J120": 2920,
    "J140": 2940,
    "J160": 2960,
    "J180": 2980,
    "J200": 3000,
    "K20": 3020,
    "K40": 3040,
    "K60": 3060,
    "K80": 3080,
    "K100": 3100,
    "K120": 3120,
    "K140": 3140,
    "K160": 3160,
    "K180": 3180,
    "K200": 3200,
    "L20": 3220,
    "L40": 3240,
    "L60": 3260,
    "L80": 3280,
    "L100": 3300,
    "L120": 3320,
    "L140": 3340,
    "L160": 3360,
    "L180": 3380,
    "L200": 3400,
}


def current_month_label() -> str:
    """Return the link_table month label for the current calendar month."""
    return MONTH_MAP.get(datetime.now().month, "Dec")


def get_worksheets_per_day(level: Optional[str], subject: Optional[str] = None) -> Optional[int]:
    """
    Get worksheets per day for a level.
    Uses the static WORKSHEETS_PER_DAY_STATIC mapping from Levels_Index.xlsx.
    Extracts letter prefix from level (e.g., 'BI160' -> 'BI').
    """
    if not level:
        return None
    
    # Normalize level first
    normalized = normalize_level(level)
    if not normalized:
        return None
    
    # Extract letter prefix (e.g., 'BI160' -> 'BI')
    letter_part, _ = extract_level_parts(normalized)
    if not letter_part:
        return None
    
    # Try direct lookup, then with subject suffix for J/K/L which appear in both
    if subject == "reading" and letter_part in {"J", "K", "L"}:
        key = f"{letter_part}_reading"
        return WORKSHEETS_PER_DAY_STATIC.get(key)
    elif subject == "math" and letter_part in {"J", "K", "L"}:
        key = f"{letter_part}_math"
        return WORKSHEETS_PER_DAY_STATIC.get(key)
    elif subject == "math" and letter_part in {"6A", "5A", "4A", "3A", "2A"}:
        key = f"{letter_part}_math"
        return WORKSHEETS_PER_DAY_STATIC.get(key)
    
    # Default lookup (works for most levels)
    return WORKSHEETS_PER_DAY_STATIC.get(letter_part)



def _safe_get(row: pd.Series, field: str) -> Any:
    try:
        val = row.get(field, None)
        # Normalize pandas NaN to None for comparisons
        if pd.isna(val):
            return None
        return val
    except Exception:
        return None


def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_grade_criteria(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_level_index_mapping(levels_excel: Optional[str]) -> Dict[str, Dict[str, int]]:
    """
    Build a mapping of (subject, level) -> page_index from the Excel file.
    The page_index represents the absolute ordering from lowest (beginning) to highest (advanced).
    Returns: {"math": {"D80": 1680, "F80": 2080, ...}, "reading": {...}}
    """
    level_index: Dict[str, Dict[str, int]] = {
        "reading": dict(READING_PAGE_INDEX_STATIC),
        "math": dict(MATH_PAGE_INDEX_STATIC),
    }

    if not levels_excel:
        return level_index
    
    try:
        levels_df = pd.read_excel(levels_excel, sheet_name="grade_table")
        # Group by subject and create a mapping of level -> page_index
        for subject in levels_df["subject"].unique():
            subject_data = levels_df[levels_df["subject"] == subject]
            level_mapping = {}
            for _, row in subject_data.iterrows():
                level = row["level"]
                page_index = row["page_index"]
                # Only store if not already present (take the first occurrence)
                if level not in level_mapping:
                    level_mapping[level] = page_index
            # Merge Excel-derived mapping with existing static mapping; keep static as authoritative
            existing = level_index.get(subject, {})
            merged = dict(existing)
            for lvl, idx in level_mapping.items():
                if lvl not in merged:
                    merged[lvl] = idx
            level_index[subject] = merged
    except Exception as e:
        print(f"Warning: Could not build level index mapping: {e}")

    return level_index


def normalize_level(level_str: Optional[str]) -> Optional[str]:
    """
    Normalize level strings by:
    - Converting Roman numeral Ⅱ to II
    - Removing all spaces
    - Converting to uppercase
    Examples: "CⅡ 40" -> "CII40", "C II 40" -> "CII40", "CII 40" -> "CII40"
    """
    if level_str is None:
        return None
    
    # Convert to string and strip
    normalized = str(level_str).strip()
    
    # Replace Roman numeral variants (Ⅱ, Ⅰ, Ⅲ, etc.)
    normalized = normalized.replace('Ⅱ', 'II')
    normalized = normalized.replace('Ⅰ', 'I')
    normalized = normalized.replace('Ⅲ', 'III')
    normalized = normalized.replace('Ⅳ', 'IV')
    normalized = normalized.replace('Ⅴ', 'V')
    
    # Remove all spaces
    normalized = normalized.replace(' ', '')
    
    # Convert to uppercase
    normalized = normalized.upper()
    
    return normalized


def extract_level_parts(level_str: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    """
    Extract letter prefix and numeric value from level strings like 'F80', 'D35', '2A80'.
    Normalizes the input first (handles "CⅡ 40", "C II 40", etc.)
    Returns (letter_part, numeric_part) or (None, None) if parsing fails.
    """
    if level_str is None:
        return None, None
    
    # Normalize the level string first
    normalized = normalize_level(level_str)
    if normalized is None:
        return None, None
    
    match = re.match(r'^([A-Z0-9]+?)(\d+)$', normalized)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def build_letter_order_from_criteria(grade_criteria: Dict[str, Any], subject: Optional[str] = None) -> Dict[str, int]:
    """
    Build letter_order dictionary from grade_criteria lists.
    Maps each level string to its position index (0=lowest, n=highest).
    If subject is provided, uses subject-specific list; otherwise tries to infer.
    """
    letter_order = {}
    
    if subject == "reading" and "reading_levels" in grade_criteria:
        levels = grade_criteria["reading_levels"]
    elif subject == "math" and "math_levels" in grade_criteria:
        levels = grade_criteria["math_levels"]
    elif "reading_levels" in grade_criteria:
        # Default to reading if not specified
        levels = grade_criteria["reading_levels"]
    else:
        # Fallback: build from available keys
        levels = []
    
    for i, level in enumerate(levels):
        letter_order[level] = i

    return letter_order


def interpolate_missing_level(
    missing_level: str,
    known_levels: Dict[str, int],
    level_hierarchy: List[str],
) -> Optional[int]:
    """
    Interpolate the position of a missing level between known levels.
    Handles levels with numeric suffixes (e.g., B80, D35) by matching against base level (B, D).
    Returns the interpolated index or None if interpolation not possible.
    """
    if not missing_level:
        return None
    
    # Check exact match first
    if missing_level in known_levels:
        return known_levels[missing_level]
    
    letter, num = extract_level_parts(missing_level)
    if letter is None:
        return None
    
    # If just the letter exists (without numeric suffix), use its index
    if letter in known_levels:
        return known_levels[letter]
    
    # If numeric suffix exists, try to interpolate
    if num is not None:
        lower_level = None
        upper_level = None
        lower_index = None
        upper_index = None
        
        # First try within same letter prefix
        for level_str, idx in known_levels.items():
            level_letter, level_num = extract_level_parts(level_str)
            if level_letter == letter:
                if level_num is not None:
                    if level_num < num and (lower_index is None or level_num > (extract_level_parts(lower_level)[1] or 0)):
                        lower_level = level_str
                        lower_index = idx
                    if level_num > num and (upper_index is None or level_num < (extract_level_parts(upper_level)[1] or 0)):
                        upper_level = level_str
                        upper_index = idx
        
        # If no upper bound with same letter, look for next level in hierarchy
        if lower_index is not None and upper_index is None:
            # Find the immediate next level by page index
            for level_str, idx in known_levels.items():
                if idx > lower_index and (upper_index is None or idx < upper_index):
                    upper_level = level_str
                    upper_index = idx
        
        # Linear interpolation between adjacent known levels
        if lower_index is not None and upper_index is not None:
            _, lower_num = extract_level_parts(lower_level)
            _, upper_num = extract_level_parts(upper_level)
            level_letter_lower, _ = extract_level_parts(lower_level)
            level_letter_upper, _ = extract_level_parts(upper_level)
            # Allow interpolation if same letter prefix and lower < upper, OR different prefixes
            if lower_num is not None and upper_num is not None:
                if (level_letter_lower == level_letter_upper and lower_num < upper_num) or (level_letter_lower != level_letter_upper):
                    ratio = (num - lower_num) / (upper_num - lower_num)
                    interpolated = lower_index + ratio * (upper_index - lower_index)
                    return interpolated
            # Fallback: simple mid-point if numeric parts unavailable
            if lower_num is not None:
                ratio = (num - lower_num) / (upper_num - lower_num)
                interpolated = lower_index + ratio * (upper_index - lower_index)
                return interpolated
    
    return None


def classify_grade_level(
    student_level: Optional[str],
    expected_level: Optional[str],
    grade_criteria: Dict[str, Any],
    level_index: Optional[Dict[str, int]] = None,
    subject: Optional[str] = None,
) -> str:
    """
    Classify student's worksheet level vs. expected level.
     1) Page-index comparison (Excel link_table) with labels:
       - KIS (at grade level): Math -40 to +199, Reading -80 to +399
       - Below: diff less than KIS lower bound
         - Math above-grade tiers: diff ≈ +200 -> ASHR1, +400 -> ASHR2, +600 -> ASHR3
         - Reading above-grade tiers: diff ≈ +400 -> ASHR1, +800 -> ASHR2, +1200 -> ASHR3
         - Otherwise positive diff -> ABOVE GRADE LEVEL
    2) Fallback to letter hierarchy with interpolation for missing levels (returns ABOVE/AT/BELOW GRADE LEVEL)
    """
    if not student_level or not expected_level:
        return ""
    
    # Normalize levels before comparison
    student_level = normalize_level(student_level)
    expected_level = normalize_level(expected_level)
    
    if not student_level or not expected_level:
        return ""

    # Helper to fetch page index with interpolation
    def _get_page_index(level: str) -> Optional[float]:
        if level_index and isinstance(level_index, dict):
            idx = level_index.get(level)
            if idx is not None:
                return idx
            if subject:
                subject_levels = grade_criteria.get(f"{subject}_levels", [])
                return interpolate_missing_level(level, level_index, subject_levels)
        return None

    # Page-index-based comparison with new labels
    student_idx = _get_page_index(student_level)
    expected_idx = _get_page_index(expected_level)

    if student_idx is not None and expected_idx is not None:
        diff = student_idx - expected_idx

        # KIS: subject-specific ranges
        # Students must be within the tight window to be considered at grade level
        if subject == "math":
            # Math: -40 to +199 (KIS range)
            if -40 <= diff <= 199:
                return "KIS"
            if diff < -40:
                return "Below"
        elif subject == "reading":
            # Reading: -80 to +399 (KIS range)
            # Students significantly behind expected level are BELOW
            if -80 <= diff <= 399:
                return "KIS"
            if diff < -80:
                return "Below"
        else:
            # Fallback for unknown subjects
            if -40 <= diff <= 199:
                return "KIS"
            if diff < -40:
                return "Below"

        # Above-grade interpolation buckets (200-page steps)
        # Use floor to place the student level within provided page indices.
        bucket = int(diff // 200)  # e.g., 720 -> 3 (≈ +600)

        if subject == "math":
            # Map buckets to ASHR tiers (math-only redefinition):
            # +200 -> bucket 1 => ASHR1
            # +400 -> bucket 2 => ASHR2
            # +600 -> bucket 3 => ASHR3
            if bucket == 3:
                return "ASHR3"
            if bucket == 2:
                return "ASHR2"
            if bucket == 1:
                return "ASHR1"
            # For buckets not covered (diff > 40 but not 200/400/600), default to ABOVE
            if diff > 40:
                return "ABOVE GRADE LEVEL"
        elif subject == "reading":
            # Reading tiers on +400/+800/+1200
            if bucket >= 6:
                return "ASHR3"
            if bucket >= 4:
                return "ASHR2"
            if bucket >= 2:
                return "ASHR1"
            if diff > 40:
                return "ABOVE GRADE LEVEL"

    # Fallback to letter hierarchy with interpolation
    letter_order = build_letter_order_from_criteria(grade_criteria, subject)
    
    student_idx = letter_order.get(student_level)
    expected_idx = letter_order.get(expected_level)
    
    # Try interpolation if either is missing
    if student_idx is None:
        student_idx = interpolate_missing_level(student_level, letter_order, 
                                                grade_criteria.get(f"{subject}_levels", []))
    if expected_idx is None:
        expected_idx = interpolate_missing_level(expected_level, letter_order,
                                                 grade_criteria.get(f"{subject}_levels", []))
    
    if student_idx is None or expected_idx is None:
        return ""
    
    if student_idx > expected_idx:
        return "ABOVE GRADE LEVEL"
    elif student_idx < expected_idx:
        return "BELOW GRADE LEVEL"
    else:
        return "AT GRADE LEVEL"


def aggregate_secondary(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """
    Reduce the secondary dataset to one row per student by aggregating:
    - numeric columns: max
    - non-numeric columns: first
    """
    if df.empty:
        return df
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]
    agg: Dict[str, Any] = {key_col: "first"}
    for c in numeric_cols:
        if c != key_col:
            agg[c] = "max"
    for c in non_numeric_cols:
        if c != key_col:
            agg[c] = "first"
    grouped = df.groupby(key_col, as_index=False).agg(agg)
    return grouped


def merge_datasets(
    students_df: pd.DataFrame,
    activities_df: Optional[pd.DataFrame],
    key_col: str,
) -> pd.DataFrame:
    if activities_df is not None and not activities_df.empty:
        activities_agged = aggregate_secondary(activities_df, key_col)
        merged = pd.merge(students_df, activities_agged, on=key_col, how="left")
    else:
        merged = students_df.copy()
    return merged


def evaluate_condition(row: pd.Series, cond: Dict[str, Any]) -> bool:
    field = cond.get("field")
    op = cond.get("op")
    value = cond.get("value")
    if field is None or op is None:
        return False
    left = _safe_get(row, field)
    if op == "exists":
        return left is not None
    func = OPERATORS.get(op)
    if func is None:
        return False
    return bool(func(left, value))


def evaluate_awards(row: pd.Series, rules: Dict[str, Any]) -> List[str]:
    awards: List[str] = []
    for award in rules.get("awards", []):
        name = award.get("name")
        conditions = award.get("conditions", [])
        if not name:
            continue
        if all(evaluate_condition(row, cond) for cond in conditions):
            awards.append(name)
    return awards


def process_awards(
    students_csv: str,
    activities_csv: Optional[str],
    rules_json: str,
    grade_criteria_json: Optional[str] = None,
    levels_excel: Optional[str] = None,
) -> pd.DataFrame:
    rules = load_rules(rules_json)
    id_field = rules.get("id_field", "StudentID")
    name_field = rules.get("name_field")

    # Load grade criteria for level classification
    grade_criteria = {}
    if grade_criteria_json:
        grade_criteria = load_grade_criteria(grade_criteria_json)

    # Build page_index mapping from Excel for accurate level comparison
    level_index = build_level_index_mapping(levels_excel)

    # Load the levels lookup table from Excel if provided
    levels_lookup = {}
    if levels_excel:
        try:
            levels_df = pd.read_excel(levels_excel, sheet_name="grade_table")
            for _, row in levels_df.iterrows():
                key = (row["grade"], row["subject"], row["month"])
                levels_lookup[key] = row["level"]
        except Exception as e:
            print(f"Warning: Could not load levels Excel: {e}")

    students_df = pd.read_csv(students_csv)
    activities_df = pd.read_csv(activities_csv) if activities_csv else None

    if id_field not in students_df.columns:
        raise ValueError(f"id_field '{id_field}' not found in students CSV")

    merged = merge_datasets(students_df, activities_df, id_field)

    # Compute awards per row
    result_rows: List[Dict[str, Any]] = []
    for _, row in merged.iterrows():
        award_list = evaluate_awards(row, rules)
        out: Dict[str, Any] = {
            id_field: _safe_get(row, id_field),
            "Awards": "; ".join(award_list) if award_list else "",
        }
        if name_field and name_field in merged.columns:
            out[name_field] = _safe_get(row, name_field)

        # Add grade-level classification if we have the necessary fields
        if (
            grade_criteria
            and levels_lookup
            and "Grade" in merged.columns
            and "Subject" in merged.columns
            and "Month" in merged.columns
            and "WorksheetLevel" in merged.columns
        ):
            grade = _safe_get(row, "Grade")
            subject = _safe_get(row, "Subject")
            month = _safe_get(row, "Month")
            student_level = _safe_get(row, "WorksheetLevel")
            expected_level = levels_lookup.get((grade, subject, month))
            
            # Use page_index-based comparison if available
            subject_levels = level_index.get(subject) if level_index else None
            classification = classify_grade_level(
                student_level,
                expected_level,
                grade_criteria,
                level_index=subject_levels,
                subject=subject,
            )
            out["GradeLevel_Classification"] = classification

        result_rows.append(out)

    return pd.DataFrame(result_rows)


def classify_student_list_by_subject(
    input_csv: str,
    levels_excel: str,
    grade_criteria_json: str,
    output_csv: Optional[str] = None,
    month_label: Optional[str] = None,
) -> pd.DataFrame:
    """
    Read a Student_List_by_Subject.csv-like file, compute the page-index based
    classification for the current calendar month (or provided month_label),
    and write back a new CSV with an added 'LevelClassification' column.

    Columns expected in input:
    - Subject
    - Full Name
    - Grade
    - Highest WS Completed This Month
    """
    month = month_label or current_month_label()

    # Load rules data
    grade_criteria = load_grade_criteria(grade_criteria_json)
    level_index_all = build_level_index_mapping(levels_excel)
    link_df = pd.read_excel(levels_excel, sheet_name="grade_table")

    # Helper to map grade to link_table labels
    def map_grade(g: Any) -> str:
        g = str(g).strip()
        if g.upper() in {"PK1", "PK2", "K"}:
            return g.upper() if g.upper().startswith("PK") else "K"
        if g.lower().startswith("grade"):
            return g.title()
        if g.isdigit():
            return f"Grade {g}"
        return g

    df = pd.read_csv(input_csv)
    classifications: List[str] = []
    normalized_levels: List[Optional[str]] = []
    expected_levels_normalized: List[Optional[str]] = []
    avg_ws_list: List[Optional[float]] = []
    study_months_list: List[Optional[int]] = []
    worksheets_per_day_list: List[Optional[int]] = []
    consistency_list: List[Optional[float]] = []
    consistency_index_list: List[int] = []

    # Helper to parse "Starting Month" and calculate months since start
    def parse_starting_month(start_month_str: Any) -> Optional[int]:
        """Parse 'Dec-23' format and return total months since that date."""
        if pd.isna(start_month_str):
            return None
        try:
            parts = str(start_month_str).strip().split('-')
            if len(parts) != 2:
                return None
            month_str, year_str = parts
            # Map month abbreviation to number
            month_map_abbr = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map_abbr.get(month_str.lower())
            if month_num is None:
                return None
            year_num = int(year_str)
            if year_num < 100:
                year_num += 2000
            # Calculate months from start to current (December 2025)
            current_year = datetime.now().year
            current_month = datetime.now().month
            months_elapsed = (current_year - year_num) * 12 + (current_month - month_num)
            return months_elapsed if months_elapsed > 0 else 1  # Avoid division by zero
        except:
            return None

    for _, row in df.iterrows():
        subject_raw = str(row.get("Subject", "")).strip().lower()
        subject = "math" if subject_raw.startswith("math") else "reading"
        grade_label = map_grade(row.get("Grade", ""))

        expected_row = link_df[
            (link_df["grade"] == grade_label)
            & (link_df["subject"] == subject)
            & (link_df["month"] == month)
        ]
        expected_level = expected_row["level"].iloc[0] if not expected_row.empty else None

        student_level_raw = row.get("Highest WS Completed This Month")
        student_level_norm = normalize_level(student_level_raw) if pd.notna(student_level_raw) else None
        normalized_levels.append(student_level_norm)
        expected_level_norm = normalize_level(expected_level) if expected_level else None
        expected_levels_normalized.append(expected_level_norm)

        if student_level_norm and expected_level_norm:
            label = classify_grade_level(
                student_level_norm,
                expected_level_norm,
                grade_criteria,
                level_index=level_index_all.get(subject),
                subject=subject,
            )
        else:
            label = ""

        classifications.append(label)

        # Calculate AVG WS and STUDY_MONTHS
        cum_ws = row.get("Cum. # of WS Studied")
        starting_month = row.get("Starting Month")
        months_elapsed = parse_starting_month(starting_month)
        
        study_months_list.append(months_elapsed)
        
        if pd.notna(cum_ws) and months_elapsed and months_elapsed > 0:
            avg_ws = float(cum_ws) / months_elapsed
        else:
            avg_ws = None
        avg_ws_list.append(avg_ws)

        # Get worksheets per day for student level
        ws_per_day = get_worksheets_per_day(student_level_norm, subject=subject)
        worksheets_per_day_list.append(ws_per_day)

        # Compute Consistency and Consistency_Index
        if months_elapsed is not None and months_elapsed >= 3 and avg_ws is not None and ws_per_day is not None and ws_per_day > 0:
            consistency = avg_ws / ws_per_day
        else:
            consistency = None
        consistency_list.append(consistency)

        consistency_index = 1 if (consistency is not None and consistency >= 19) else 0
        consistency_index_list.append(consistency_index)

    df["LevelClassification"] = classifications
    df["NormalizedLevel"] = normalized_levels
    df["ExpectedLevelNormalized"] = expected_levels_normalized
    df["STUDY_MONTHS"] = study_months_list
    df["AVG WS"] = avg_ws_list
    df["WorksheetsPerDay"] = worksheets_per_day_list
    df["Consistency"] = consistency_list
    df["Consistency_Index"] = consistency_index_list

    # Compute per-student Diploma classification
    # Rules:
    # - Welcome: if a student has one or two subjects and all subjects' Starting Month
    #   coincides with the current calendar month and year.
    # - Award: if at least one subject's LevelClassification is KIS or ASHR1/ASHR2/ASHR3.
    # - Certificate: if any subject is BELOW (handles "Below" and "BELOW GRADE LEVEL").

    # Helper to check if a 'Dec-25' style string matches current month/year
    month_map_abbr = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    def is_current_month_str(start_month_str: Any) -> bool:
        if pd.isna(start_month_str):
            return False
        s = str(start_month_str).strip()
        if '-' not in s:
            return False
        mon_abbr, yr = s.split('-', 1)
        mon_num = month_map_abbr.get(mon_abbr.lower())
        if mon_num is None:
            return False
        try:
            yr_num = int(yr)
            if yr_num < 100:
                yr_num += 2000
        except Exception:
            return False
        return (mon_num == datetime.now().month) and (yr_num == datetime.now().year)

    def is_below_label(label: Any) -> bool:
        if pd.isna(label):
            return False
        s = str(label).strip().upper()
        return ('BELOW' in s)

    award_labels = {"KIS", "ASHR1", "ASHR2", "ASHR3"}
    diploma_by_student: Dict[str, str] = {}
    if "Full Name" in df.columns:
        for name, group in df.groupby("Full Name"):
            starts_current = all(is_current_month_str(x) for x in group["Starting Month"]) if "Starting Month" in group.columns else False
            has_award = any(str(x).strip().upper() in award_labels for x in group["LevelClassification"]) if "LevelClassification" in group.columns else False
            has_below = any(is_below_label(x) for x in group["LevelClassification"]) if "LevelClassification" in group.columns else False

            if starts_current:
                diploma = "Welcome"
            elif has_award:
                diploma = "Award"
            elif has_below:
                diploma = "Certificate"
            else:
                diploma = ""
            diploma_by_student[name] = diploma

        df["Diploma"] = df["Full Name"].map(diploma_by_student)

    if output_csv is None:
        output_csv = input_csv
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    return df
