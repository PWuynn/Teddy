from pathlib import Path

p = Path('quiz_ai/views.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    "_CHOICE_MARKER_RE = re.compile(r'(?<!\\w)[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*[\\.\\):\\-/]\\s+')\n"
    "_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*(?:[\\.\\):\\-/]|\\s+)')",
    "_CHOICE_MARKER_RE = re.compile(r'(?<!\\w)[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*[\\.\\):\\-/\\u2013\\u2014]\\s+')\n"
    "_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:\\(?[A-Fa-f]\\)?)[\\s]*(?:[\\.\\):\\-/\\u2013\\u2014]|\\s+)')\n"
    "_NAMED_CHOICE_LINE_RE = re.compile(r'^[\\s\\-*]*(?:dap an|phuong an|option|choice)\\s+([a-f])\\s*[\\.\\):\\-/\\u2013\\u2014]\\s+')",
)

s = s.replace(
    "def _is_choice_line(line):\n    value = line.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    return bool(_CHOICE_LINE_RE.match(value))",
    "def _is_choice_line(line):\n    value = line.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    return bool(_CHOICE_LINE_RE.match(value) or _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)))",
)

s = s.replace(
    "def _choice_letter(answer, index):\n    value = answer.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    match = _CHOICE_LINE_RE.match(value)\n    if match:\n        for char in match.group(0):\n            if char.lower() in 'abcdef':\n                return char.lower()\n    return chr(ord('a') + index)",
    "def _choice_letter(answer, index):\n    value = answer.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    named_match = _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value))\n    if named_match:\n        return named_match.group(1).lower()\n    match = _CHOICE_LINE_RE.match(value)\n    if match:\n        for char in match.group(0):\n            if char.lower() in 'abcdef':\n                return char.lower()\n    return chr(ord('a') + index)",
)

s = s.replace(
    "def _clean_choice_prefix(answer):\n    value = answer.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    if value.endswith('*'):\n        value = value[:-1].strip()\n    return _CHOICE_LINE_RE.sub('', value, count=1).strip()",
    "def _clean_choice_prefix(answer):\n    value = answer.strip()\n    if value.startswith('*'):\n        value = value[1:].strip()\n    if value.endswith('*'):\n        value = value[:-1].strip()\n    if _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)):\n        for separator in (':', '.', ')', '-', '/', chr(8211), chr(8212)):\n            if separator in value:\n                return value.split(separator, 1)[1].strip()\n    return _CHOICE_LINE_RE.sub('', value, count=1).strip()",
)

p.write_text(s, encoding='utf-8')
