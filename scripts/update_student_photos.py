"""
Scan `static/img/students/` for image files and match them to students in
`data/kumoclock.db` (students table). Prints a dry-run summary by default.
Run with `--apply` to write `photo` filenames into the `students.photo` column.

Matching strategy:
- Normalise both filenames (name part) and student names by lowercasing,
  removing non-alphanumeric characters and collapsing whitespace.
- Exact normalized match preferred.
- If no exact match, attempt "starts with" or "contains" matches.
- Ambiguous or no-match entries are reported and skipped.

Usage:
  python scripts/update_student_photos.py       # dry-run
  python scripts/update_student_photos.py --apply  # perform updates

"""
import sqlite3
import os
import re
import argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "kumoclock.db")
IMG_DIR = os.path.join(BASE, "static", "img", "students")
TEMPL_IMG_DIR = os.path.join(BASE, "templates", "static", "img", "students")


def normalize(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    # replace common separators with space
    s = re.sub(r"[_.]+", " ", s)
    # remove non-alphanumeric (keep spaces)
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_students(conn):
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM students")
    rows = cur.fetchall()
    students = []
    for sid, name in rows:
        students.append((sid, name, normalize(name)))
    return students


def find_best_match(img_name_norm, students):
    # exact match
    exact = [s for s in students if s[2] == img_name_norm]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None, "ambiguous_exact"

    # startswith match
    starts = [s for s in students if s[2].startswith(img_name_norm) or img_name_norm.startswith(s[2])]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1:
        return None, "ambiguous_starts"

    # contains match
    contains = [s for s in students if img_name_norm in s[2] or s[2] in img_name_norm]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        return None, "ambiguous_contains"

    return None, "no_match"


def main(apply: bool):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return 1
    if not os.path.isdir(IMG_DIR):
        if os.path.isdir(TEMPL_IMG_DIR):
            print(f"Falling back to template images at {TEMPL_IMG_DIR}")
            img_dir = TEMPL_IMG_DIR
        else:
            print(f"Image folder not found: {IMG_DIR}")
            return 1
    else:
        img_dir = IMG_DIR

    files = [f for f in os.listdir(img_dir) if os.path.isfile(os.path.join(img_dir, f))]
    if not files:
        print("No image files found in", IMG_DIR)
        return 0

    conn = sqlite3.connect(DB_PATH)
    students = load_students(conn)
    norm_to_student = {s[2]: s for s in students}

    plan = []
    ambiguous = []
    no_match = []

    for fname in sorted(files):
        namepart, _ = os.path.splitext(fname)
        norm = normalize(namepart)
        if not norm:
            no_match.append((fname, "empty_norm"))
            continue

        match = find_best_match(norm, students)
        if isinstance(match, tuple) and len(match) == 2 and match[0] is None:
            # ambiguous or no_match returned as (None, reason)
            reason = match[1]
            if reason.startswith("ambiguous"):
                ambiguous.append((fname, norm, reason))
            else:
                no_match.append((fname, norm, reason))
            continue
        if match is None:
            no_match.append((fname, norm, "no_match"))
            continue
        sid, sname, snorm = match
        plan.append((fname, sid, sname))

    # Summarize
    print("Found image files:", len(files))
    print("Planned updates:", len(plan))
    if ambiguous:
        print("Ambiguous matches:")
        for f, n, r in ambiguous:
            print(f"  {f}  -> norm='{n}'  reason={r}")
    if no_match:
        print("No matches:")
        for f, n, r in no_match:
            print(f"  {f}  -> norm='{n}'  reason={r}")

    if plan:
        print("\nPreview of updates:")
        for fname, sid, sname in plan:
            print(f"  Student id={sid} name='{sname}'  <- '{fname}'")

    if not apply:
        print("\nDry-run only. Rerun with --apply to write changes to the database.")
        conn.close()
        return 0

    # Apply updates
    cur = conn.cursor()
    applied = 0
    for fname, sid, sname in plan:
        cur.execute("UPDATE students SET photo=? WHERE id=?", (fname, sid))
        applied += 1
    conn.commit()
    conn.close()
    print(f"Applied {applied} updates to the database.")
    if ambiguous or no_match:
        print("Note: some files were ambiguous or not matched and were skipped.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Write updates to DB")
    args = p.parse_args()
    raise SystemExit(main(args.apply))
