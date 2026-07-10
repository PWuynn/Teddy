from pathlib import Path

p = Path('quiz_ai/views.py')
lines = p.read_text(encoding='utf-8').splitlines()
out = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('return without_marks.replace('):
        out.append("    return without_marks.replace(chr(273), 'd')")
    elif 'ít nhất 2' in line or 'Ã­t nháº¥t 2' in line or 'mỗi câu' in line or 'má»—i' in line:
        if 'return None' in line:
            out.append("        return None, f'Dòng {first_line_number}: mỗi câu hỏi cần ít nhất 2 đáp án.'")
        else:
            out.append(line)
    elif 'errors.append(' in line and 'nh' in line and 'di' in line:
        out.append("        errors.append('File chưa có câu hỏi hoặc đáp án có thể nhận diện được.')")
    elif 'messages.error(request' in line and 'File' in line and 'B' in line:
        out.append('                messages.error(request, "File chưa có câu hỏi đúng cấu trúc. Bài kiểm tra chưa được tạo.")')
    else:
        out.append(line)
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
