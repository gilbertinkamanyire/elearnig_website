import os

file_path = r'c:\Users\MATRIXCOMPUTER\elerning_system\routes\courses.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i in range(len(lines)):
    if skip:
        skip = False
        continue
    if i < len(lines) - 1:
        if lines[i].strip() == "@app.route('/courses')" and lines[i+1].strip() == "@app.route('/courses')":
            new_lines.append(lines[i])
            skip = True
            continue
        if lines[i].strip() == "@app.route('/courses/<int:course_id>')" and lines[i+1].strip() == "@app.route('/courses/<int:course_id>')":
            new_lines.append(lines[i])
            skip = True
            continue
    new_lines.append(lines[i])

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Double routes fixed.")
