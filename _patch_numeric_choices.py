from pathlib import Path

p = Path('quiz_ai/views.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    "_NAMED_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:dap an|phuong an|option|choice)\\s+([a-f])\\s*[\\.\\):\\-/\\u2013\\u2014]\\s+')",
    "_NAMED_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:dap an|phuong an|option|choice)\\s+([a-f])\\s*[\\.\\):\\-/\\u2013\\u2014]\\s+')\n_NUMERIC_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*[1-9][0-9]*[\\.\\):\\-/\\u2013\\u2014]\\s+')",
)
s = s.replace(
    "return bool(_CHOICE_LINE_RE.match(value) or _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)))",
    "return bool(_CHOICE_LINE_RE.match(value) or _NUMERIC_CHOICE_LINE_RE.match(value) or _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)))",
)
s = s.replace(
    "return _CHOICE_LINE_RE.sub('', value, count=1).strip()",
    "value = _NUMERIC_CHOICE_LINE_RE.sub('', value, count=1).strip()\n    return _CHOICE_LINE_RE.sub('', value, count=1).strip()",
)
old = """        if _is_question_line(line) and (question_lines or answer_lines):
            flush_current()

        if not question_lines:
            first_line_number = line_number
            question_lines.append(line)
            continue

        if _is_choice_line(line) or is_answer_marker or line.startswith('*'):
            answer_lines.append((line_number, line))
            continue
"""
new = """        if question_lines and (_is_choice_line(line) or is_answer_marker or line.startswith('*')):
            answer_lines.append((line_number, line))
            continue

        if _is_question_line(line) and (question_lines or answer_lines):
            flush_current()

        if not question_lines:
            first_line_number = line_number
            question_lines.append(line)
            continue

        if _is_choice_line(line) or is_answer_marker or line.startswith('*'):
            answer_lines.append((line_number, line))
            continue
"""
s = s.replace(old, new)

p.write_text(s, encoding='utf-8')
