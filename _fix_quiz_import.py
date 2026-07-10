from pathlib import Path

p = Path('quiz_ai/views.py')
s = p.read_text(encoding='utf-8')

bad = 'from django.shortcuts import re\nimport unicodedatander, redirect, get_object_or_404'
s = s.replace(bad, 'from django.shortcuts import render, redirect, get_object_or_404')
if 'import unicodedata' not in s:
    s = s.replace('import re\n', 'import re\nimport unicodedata\n', 1)

s = s.replace("return without_marks.replace('Ä‘', 'd')", "return without_marks.replace('đ', 'd')")
s = s.replace("value = line.strip().lower()\n    if not value:\n        return False\n    prefixes = ('cÃ¢u ', 'cau ', 'question ', 'q.')", "value = _fold_quiz_text(line)\n    if not value:\n        return False\n    prefixes = ('cau ', 'question ', 'q.')")
s = s.replace('"Ä\x90Ã¡p Ã¡n: "', '"Dap an: "')

p.write_text(s, encoding='utf-8')
