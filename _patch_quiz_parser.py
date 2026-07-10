from pathlib import Path
import re

p = Path('quiz_ai/views.py')
s = p.read_text(encoding='utf-8')

if 'import unicodedata' not in s:
    s = s.replace('import re', 'import re\nimport unicodedata', 1)

start = s.index('_CHOICE_MARKER_RE =')
end = s.index('\n\ndef _decode_uploaded_text', start)
constants = """_CHOICE_MARKER_RE = re.compile(r'(?<!\\w)[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*[\\.\\):\\-/]\\s+')
_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*(?:[\\.\\):\\-/]|\\s+)')
_ANSWER_PREFIXES = (
    'dap an:', 'dap an dung:', 'answer:', 'answer key:', 'correct:',
)


def _fold_quiz_text(value):
    normalized = unicodedata.normalize('NFD', value.lower().strip())
    without_marks = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    return without_marks.replace('đ', 'd')
"""
s = s[:start] + constants + s[end:]

s = s.replace('lowered = line.lower().strip()', 'lowered = _fold_quiz_text(line)')
s = s.replace('lowered = line.lower()', 'lowered = _fold_quiz_text(line)')
s = s.replace(
    "return len(value) >= 2 and value[0].lower() in 'abcdef' and value[1] in '.):-'",
    'return bool(_CHOICE_LINE_RE.match(value))',
)

start = s.index('def _choice_letter')
end = s.index('\n\ndef _parse_question_block', start)
choice_helpers = """def _choice_letter(answer, index):
    value = answer.strip()
    if value.startswith('*'):
        value = value[1:].strip()
    match = _CHOICE_LINE_RE.match(value)
    if match:
        for char in match.group(0):
            if char.lower() in 'abcdef':
                return char.lower()
    return chr(ord('a') + index)


def _clean_choice_prefix(answer):
    value = answer.strip()
    if value.startswith('*'):
        value = value[1:].strip()
    if value.endswith('*'):
        value = value[:-1].strip()
    return _CHOICE_LINE_RE.sub('', value, count=1).strip()
"""
s = s[:start] + choice_helpers + s[end:]

s = s.replace(
    'answer_lines.append((line_number, "ÄÃ¡p Ã¡n: " + ",".join(sorted(inline_correct_letters))))',
    'answer_lines.append((line_number, "Dap an: " + ",".join(sorted(inline_correct_letters))))',
)

p.write_text(s, encoding='utf-8')
