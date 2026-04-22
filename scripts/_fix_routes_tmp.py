"""Temporary script to fix the broken students.py route."""
import re

with open('routes/students.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

output = []
i = 0
skip_until = None
while i < len(lines):
    line = lines[i]
    
    # Remove the misplaced nested _extract_days inside register_student_routes
    if '    def _extract_days(schedule_json_str):' in line:
        # Skip 14 lines (the whole nested function + blank line)
        i += 15
        continue
    
    # Fix the broken double add_student in students_add POST
    # Remove the first (incomplete) call: "student_id = student_manager.add_student(" through its ")"
    # This starts right after "return redirect(url_for("students_add"))"
    # The old broken call is:
    #             student_id = student_manager.add_student(
    #                 ...missing day params...
    #             )
    # Followed immediately by indented _sched_json lines
    
    stripped = line.lstrip()
    if (stripped.startswith('student_id = student_manager.add_student(') and 
        '                student_id' not in line and  # not the new correctly-indented one
        i + 1 < len(lines) and 'schedule_json' not in ''.join(lines[i:i+20])):
        # This is the old broken call without schedule_json - skip until closing )
        depth = 0
        while i < len(lines):
            for ch in lines[i]:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
            i += 1
            if depth == 0:
                break
        continue
    
    output.append(line)
    i += 1

with open('routes/students.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("Done")

# Verify syntax
import ast
with open('routes/students.py', 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error: {e}")
