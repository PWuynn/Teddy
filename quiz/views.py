from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Quiz, Question, Choice, QuizResult, QuizReloadPenalty
from django.http import HttpResponseForbidden, HttpResponse
from django.utils import timezone
from datetime import datetime
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from classroom.models import ClassroomMember
from django.template.loader import get_template
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import os
import cloudinary.uploader
import re
import unicodedata
import random
from io import BytesIO


_CHOICE_MARKER_RE = re.compile(r'(?<!\w)[\s\-*]*(?:\(?[A-Fa-f]\)?)[\s]*[\.\):\-/\u2013\u2014]\s*')
_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*(?:\(?[A-Fa-f]\)?)[\s]*(?:[\.\):\-/\u2013\u2014]|\s+)')
_NAMED_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*(?:dap an|phuong an|option|choice)\s+([a-f])\s*[\.\):\-/\u2013\u2014]\s+')
_NUMERIC_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*[1-9][0-9]*[\.)]\s*\S+$')
_NUMERIC_CHOICE_PREFIX_RE = re.compile(r'^[\s\-*]*[1-9][0-9]*[\.)]\s*')
_BULLET_CHOICE_LINE_RE = re.compile(r'^[\s]*(?:[-\u2022\u2013\u2014]|\*)\s+\S+$')
_BULLET_CHOICE_PREFIX_RE = re.compile(r'^[\s]*(?:[-\u2022\u2013\u2014]|\*)\s+')
_ANSWER_PREFIXES = (
    'dap an:', 'dap an dung:', 'answer:', 'answer key:', 'correct:',
)


def _fold_quiz_text(value):
    normalized = unicodedata.normalize('NFD', value.lower().strip())
    without_marks = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    return without_marks.replace(chr(273), 'd')


def _decode_uploaded_text(uploaded_file):
    raw_content = uploaded_file.read()
    for encoding in ('utf-8-sig', 'utf-8', 'cp1258', 'cp1252'):
        try:
            return raw_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_content.decode('utf-8', errors='replace')


def _normalize_quiz_text(value):
    return value.strip().replace('<br />', '\n').replace('<br/>', '\n').replace('<br>', '\n')



def _decode_uploaded_bytes(raw_content):
    for encoding in ('utf-8-sig', 'utf-8', 'cp1258', 'cp1252'):
        try:
            return raw_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_content.decode('utf-8', errors='replace')



def _extract_uploaded_quiz_images(uploaded_file):
    """Return embedded Word images in document order for automatic quizzes."""
    filename = (getattr(uploaded_file, 'name', '') or '').lower()
    if not filename.endswith('.docx'):
        return []

    try:
        from docx import Document
        raw_content = uploaded_file.read()
        uploaded_file.seek(0)
        document = Document(BytesIO(raw_content))
    except Exception:
        return []

    images = []
    extension_by_type = {
        'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
        'image/webp': 'webp', 'image/bmp': 'bmp',
    }
    for index, shape in enumerate(document.inline_shapes, start=1):
        try:
            relationship_id = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            image_part = document.part.related_parts[relationship_id]
            extension = extension_by_type.get(image_part.content_type, 'png')
            images.append(SimpleUploadedFile(
                name=f'question_{index}.{extension}',
                content=image_part.blob,
                content_type=image_part.content_type,
            ))
        except Exception:
            continue
    return images


def _store_word_question_image(image_file, quiz_id, index):
    """Upload a Word-extracted image explicitly and return its Cloudinary ID."""
    if not image_file:
        return None
    if not settings.USE_CLOUDINARY_MEDIA:
        return image_file

    image_file.seek(0)
    result = cloudinary.uploader.upload(
        image_file,
        resource_type="image",
        folder=f"teddy/quiz_question_images/quiz_{quiz_id}",
        public_id=f"question_{index + 1}",
        overwrite=True,
    )
    return result["public_id"]


def _docx_paragraph_with_images(paragraph, document, image_map):
    """Keep text and replace legacy Word equation/image objects with markers."""
    parts = []
    relationship_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    for run in paragraph._p:
        if not run.tag.endswith('}r'):
            continue
        for node in run:
            if node.tag.endswith('}t'):
                parts.append(node.text or '')
            elif node.tag.endswith('}tab'):
                parts.append('\t')
            elif node.tag.endswith(('}object', '}drawing')):
                for image_node in node.iter():
                    if not image_node.tag.endswith('}imagedata'):
                        continue
                    relationship_id = image_node.get(relationship_ns)
                    if not relationship_id or relationship_id not in document.part.related_parts:
                        continue
                    image_part = document.part.related_parts[relationship_id]
                    extension = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif', 'image/webp': 'webp'}.get(image_part.content_type, 'png')
                    marker = f'[[DOCX_IMAGE_{len(image_map)}]]'
                    image_map[marker] = SimpleUploadedFile(name=f'equation_{len(image_map) + 1}.{extension}', content=image_part.blob, content_type=image_part.content_type)
                    parts.append(marker)
    return ''.join(parts).strip()


def _extract_docx_answer_key(document):
    answer_key = {}
    for table in document.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        for index in range(0, len(rows) - 1, 2):
            for number, answer in zip(rows[index], rows[index + 1]):
                if number.isdigit() and answer.upper() in {'A', 'B', 'C', 'D', 'E', 'F'}:
                    answer_key[number] = answer.upper()
    return answer_key

def _extract_uploaded_quiz_text(uploaded_file):
    raw_content = uploaded_file.read()
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    filename = (getattr(uploaded_file, 'name', '') or '').lower()
    extension = filename.rsplit('.', 1)[-1] if '.' in filename else ''

    if extension in {'txt', 'text', 'csv'}:
        return _decode_uploaded_bytes(raw_content), []

    if extension == 'docx':
        try:
            from docx import Document
        except ImportError:
            return '', ['Máy chủ chưa có thư viện đọc Word. Vui lòng cài python-docx.']
        try:
            document = Document(BytesIO(raw_content))
        except Exception:
            return '', ['Không thể đọc tệp Word. Vui lòng tải tệp .docx hợp lệ.']

        image_map = {}
        blocks = [_docx_paragraph_with_images(paragraph, document, image_map) for paragraph in document.paragraphs]
        blocks = [block for block in blocks if block]
        uploaded_file._docx_image_map = image_map
        uploaded_file._docx_answer_key = _extract_docx_answer_key(document)
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if len(cells) < 2 or not cells[0] or not cells[1]:
                    continue
                header = _fold_quiz_text(f'{cells[0]} {cells[1]}')
                if 'cau hoi' in header and ('dap an' in header or 'lua chon' in header):
                    continue
                blocks.append(f'{cells[0]}\n{cells[1]}')
        # Each Word paragraph is a consecutive quiz line. Separating every
        # paragraph with a blank line flushes the parser before its choices.
        return '\n'.join(blocks), []

    if extension == 'pdf':
        try:
            import pdfplumber
        except ImportError:
            return '', ['Máy chủ chưa có thư viện đọc PDF. Vui lòng cài pdfplumber.']
        try:
            with pdfplumber.open(BytesIO(raw_content)) as pdf:
                table_blocks = []
                plain_text = []
                for page in pdf.pages:
                    plain_text.append(page.extract_text() or '')
                    for table in page.extract_tables() or []:
                        for row in table:
                            cells = [(cell or '').strip() for cell in row]
                            if len(cells) < 2 or not cells[0] or not cells[1]:
                                continue
                            header = _fold_quiz_text(f'{cells[0]} {cells[1]}')
                            if 'cau hoi' in header and ('dap an' in header or 'lua chon' in header):
                                continue
                            table_blocks.append(f'{cells[0]}\n{cells[1]}')
        except Exception:
            return '', ['Không thể đọc tệp PDF. Vui lòng tải PDF có thể chọn/sao chép văn bản.']
        return ('\n\n'.join(table_blocks) if table_blocks else '\n'.join(plain_text)), []

    return '', ['Chỉ hỗ trợ tệp .docx, .pdf, .txt, .text hoặc .csv.']


def _split_manual_question_blocks(text):
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    blocks = []
    current = []

    for line in normalized.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = []
            continue
        if stripped.startswith("'"):
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(stripped)

    if current:
        blocks.append(current)

    return blocks


def _extract_correct_letters(lines):
    correct_letters = set()
    clean_lines = []

    for line_number, line in lines:
        lowered = _fold_quiz_text(line)
        if lowered.startswith(_ANSWER_PREFIXES):
            answer_value = line.split(':', 1)[1].strip() if ':' in line else ''
            compact_key = re.sub(r'[\s,;/&]+', '', _fold_quiz_text(answer_value))
            compact_key = compact_key.replace('va', '').replace('and', '')
            if compact_key and all(letter in 'abcdef' for letter in compact_key):
                correct_letters.update(compact_key)
                continue
            
            clean_lines.append((line_number, answer_value))
            continue
        clean_lines.append((line_number, line))

    return correct_letters, clean_lines


def _strip_inline_answer_key(line):
    lowered = _fold_quiz_text(line)
    positions = [lowered.find(prefix) for prefix in _ANSWER_PREFIXES if lowered.find(prefix) >= 0]
    if not positions:
        return line, set()

    marker_index = min(positions)
    answer_key = lowered[marker_index:].split(':', 1)[1] if ':' in lowered[marker_index:] else ''
    correct_letters = {letter for letter in ('a', 'b', 'c', 'd', 'e', 'f') if letter in answer_key}
    return line[:marker_index].strip(), correct_letters


def _split_inline_choices(line):
    line, inline_correct_letters = _strip_inline_answer_key(line)
    matches = list(_CHOICE_MARKER_RE.finditer(line))
    if len(matches) < 2:
        return None, [], inline_correct_letters

    question_text = line[:matches[0].start()].strip()
    answers = []

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        answer_text = line[match.start():end].strip()
        if answer_text:
            answers.append(answer_text)

    return question_text, answers, inline_correct_letters


def _is_question_line(line):
    value = line.strip().lower()
    if not value:
        return False
    prefixes = ('câu ', 'cau ', 'question ', 'q.')
    if value.startswith(prefixes):
        return True
    if len(value) >= 3 and value[0].isdigit():
        marker_index = 1
        while marker_index < len(value) and value[marker_index].isdigit():
            marker_index += 1
        return marker_index < len(value) and value[marker_index] in '. ):'
    return False


def _is_section_heading(line):
    value = _fold_quiz_text(line).strip()
    while value and not value[0].isalnum():
        value = value[1:]
    return value.startswith('phan ') or value.startswith('section ')


def _is_choice_line(line):
    value = line.strip()
    if value.startswith('*'):
        value = value[1:].strip()
    return bool(
        _CHOICE_LINE_RE.match(value)
        or _NUMERIC_CHOICE_LINE_RE.match(value)
        or _BULLET_CHOICE_LINE_RE.match(value)
        or _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value))
    )


def _choice_letter(answer, index):
    value = answer.strip()
    if value.startswith('*'):
        value = value[1:].strip()
    named_match = _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value))
    if named_match:
        return named_match.group(1).lower()
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
    if _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)):
        for separator in (':', '.', ')', '-', '/', chr(8211), chr(8212)):
            if separator in value:
                return value.split(separator, 1)[1].strip()
    value = _NUMERIC_CHOICE_PREFIX_RE.sub('', value, count=1).strip()
    value = _BULLET_CHOICE_PREFIX_RE.sub('', value, count=1).strip()
    return _CHOICE_LINE_RE.sub('', value, count=1).strip()


def _parse_question_block(first_line_number, question_lines, answer_lines):
    question_text = _normalize_quiz_text('\n'.join(question_lines))
    correct_letters, answer_lines = _extract_correct_letters(answer_lines)
    expanded_answers = []
    for line_number, answer in answer_lines:
        markers = list(_CHOICE_MARKER_RE.finditer(answer))
        if len(markers) >= 2:
            for index, marker in enumerate(markers):
                end = markers[index + 1].start() if index + 1 < len(markers) else len(answer)
                expanded_answers.append((line_number, answer[marker.start():end].strip()))
        else:
            expanded_answers.append((line_number, answer))
    answer_lines = expanded_answers

    if not question_text:
        return None, f'Dòng {first_line_number}: câu hỏi không hợp lệ.'

    if not answer_lines:
        return None, f'Dòng {first_line_number}: câu hỏi chưa có đáp án.'

    choices = []
    correct_count = 0

    for index, (line_number, answer) in enumerate(answer_lines):
        raw_answer = answer.strip()
        is_correct = (
            raw_answer.startswith('*')
            or raw_answer.endswith('*')
            or _choice_letter(raw_answer, index) in correct_letters
        )
        choice_text = _normalize_quiz_text(_clean_choice_prefix(raw_answer))

        if not choice_text:
            return None, f'Dòng {line_number}: đáp án không được để trống.'

        if is_correct:
            correct_count += 1
        choices.append((choice_text, is_correct))

    if correct_count == 0:
        first_choice, _ = choices[0]
        choices[0] = (first_choice, True)

    return (question_text, choices), None



def _parse_answers_for_question(question_text, answers):
    """Parse answers from the manual add/edit forms with import rules."""
    answer_lines = [
        (line_number, line.strip())
        for line_number, line in enumerate(answers.splitlines(), start=1)
        if line.strip()
    ]
    parsed, error = _parse_question_block(1, [question_text], answer_lines)
    if error:
        return [], error
    return parsed[1], None


def _parse_uploaded_quiz_file(uploaded_file):
    text, errors = _extract_uploaded_quiz_text(uploaded_file)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    questions = []
    question_lines = []
    answer_lines = []
    first_line_number = None

    def flush_current():
        
        nonlocal question_lines, answer_lines, first_line_number
        if not question_lines and not answer_lines:
            return
        parsed, error = _parse_question_block(first_line_number or 1, question_lines, answer_lines)
        if parsed:
            questions.append(parsed)
        if error:
            errors.append(error)
        question_lines = []
        answer_lines = []
        first_line_number = None

    for line_number, raw_line in enumerate(text.split('\n'), start=1):
        line = raw_line.strip()
        if not line:
            if question_lines or answer_lines:
                flush_current()
            continue
        if line.startswith("'"):
            flush_current()
            continue

        lowered = _fold_quiz_text(line)
        is_answer_marker = lowered.startswith(_ANSWER_PREFIXES)
        inline_question, inline_answers, inline_correct_letters = _split_inline_choices(line)

        if _is_section_heading(line):
            if question_lines and answer_lines:
                flush_current()
            elif question_lines:
                question_lines = []
                first_line_number = None
            continue

        if question_lines and answer_lines and _is_question_line(line):
            flush_current()

        if inline_answers and inline_question:
            if question_lines or answer_lines:
                flush_current()
            first_line_number = line_number
            question_lines.append(inline_question)
            answer_lines.extend((line_number, answer) for answer in inline_answers)
            if inline_correct_letters:
                answer_lines.append((line_number, "Đáp án: " + ",".join(sorted(inline_correct_letters))))
            continue
            
        if question_lines and (_is_choice_line(line) or is_answer_marker or line.startswith('*')):
            answer_lines.append((line_number, line))
            continue

        if _is_question_line(line) and (question_lines or answer_lines):
            flush_current()
            
        if question_lines and not answer_lines and _is_question_line(question_lines[0]):
            answer_lines.append((line_number, line))
            continue

        if not question_lines:
            first_line_number = line_number
            question_lines.append(line)
            continue

        if _is_choice_line(line) or is_answer_marker or line.startswith('*'):
            answer_lines.append((line_number, line))
            continue

        if answer_lines:
            prev_line_number, prev_text = answer_lines[-1]
            answer_lines[-1] = (prev_line_number, prev_text + '\n' + line)
        else:
            question_lines.append(line)
    
    flush_current()

    if not questions and not errors:
        errors.append('File chưa có câu hỏi hoặc đáp án có thể nhận diện được.')

    return questions, errors


def _quiz_attempt_count(user, quiz):
    return (
        QuizResult.objects.filter(user=user, quiz=quiz).count()
        + QuizReloadPenalty.objects.filter(user=user, quiz=quiz).count()
    )

def _can_access_quiz(user, quiz):
    if user.is_admin:
        return True
    if quiz.created_by == user or not quiz.classroom_id:
        return True
    return ClassroomMember.objects.filter(
        classroom=quiz.classroom,
        student=user,
        status='approved'
    ).exists()
@login_required
def create_quiz(request):

    if request.method == 'POST':

        title = request.POST.get('title')
        description = request.POST.get('description')
        max_attempts = request.POST.get('max_attempts') or None
        time_limit = request.POST.get('time_limit') or None

        quiz = Quiz.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            max_attempts=max_attempts,
            time_limit=time_limit
        )

        mode = request.POST.get('mode') or 'manual'
        if mode == 'ai':
            quiz_file = request.FILES.get('quiz_file')
            if not quiz_file:
                quiz.delete()
                messages.error(request, "Vui lòng tải file Word (.docx), PDF hoặc file văn bản có câu hỏi trước khi tạo đề tự động.")
                return render(request, 'quiz/create_quiz.html')

            parsed_questions, parse_errors = _parse_uploaded_quiz_file(quiz_file)
            if not parsed_questions:
                quiz.delete()
                messages.error(request, "File chưa có câu hỏi đúng cấu trúc. Bài kiểm tra chưa được tạo.")
                for error in parse_errors[:10]:
                    messages.warning(request, error)
                return render(request, 'quiz/create_quiz.html')

            question_images = _extract_uploaded_quiz_images(quiz_file)
            image_map = getattr(quiz_file, '_docx_image_map', {})
            with transaction.atomic():
                for index, (content, choices) in enumerate(parsed_questions):
                    marker_keys = re.findall(r'\\[\\[DOCX_IMAGE_\\d+\\]\\]', content)
                    image = image_map.get(marker_keys[0]) if marker_keys else None
                    if image is None and index < len(question_images):
                        image = question_images[index]
                    if image:
                        image = _store_word_question_image(image, quiz.id, index)
                    clean_content = re.sub(r'\\[\\[DOCX_IMAGE_\\d+\\]\\]', '', content).strip()
                    question = Question.objects.create(
                        quiz=quiz,
                        content=clean_content,
                        image=image,
                    )
                    for choice_index, (choice_text, is_correct) in enumerate(choices):
                        marker_keys = re.findall(r'\\[\\[DOCX_IMAGE_\\d+\\]\\]', choice_text)
                        choice_image = image_map.get(marker_keys[0]) if marker_keys else None
                        if choice_image:
                            choice_image = _store_word_question_image(choice_image, quiz.id, index * 10 + choice_index)
                        Choice.objects.create(
                            question=question,
                            content=re.sub(r'\\[\\[DOCX_IMAGE_\\d+\\]\\]', '', choice_text).strip(),
                            is_correct=is_correct,
                            image=choice_image,
                        )

            messages.success(request, f"Đã tạo {len(parsed_questions)} câu hỏi từ file tải lên.")
            if parse_errors:
                messages.warning(request, f"Có {len(parse_errors)} câu hỏi/dòng sai cấu trúc và đã được bỏ qua.")
                for error in parse_errors[:10]:
                    messages.warning(request, error)
            return redirect('quiz:quiz_detail', quiz.id)
        manual_questions = request.POST.get('manual_questions', '').strip()
        if manual_questions:
            for lines in _split_manual_question_blocks(manual_questions):
                if len(lines) < 2:
                    continue
                parsed, error = _parse_question_block(
                    1,
                    [lines[0]],
                    list(enumerate(lines[1:], start=2)),
                )
                if error:
                    messages.warning(request, error)
                    continue
                content, choices = parsed
                question = Question.objects.create(quiz=quiz, content=content)
                for choice_text, is_correct in choices:
                    Choice.objects.create(question=question, content=choice_text, is_correct=is_correct)
            return redirect('quiz:quiz_detail', quiz.id)

        return redirect('quiz:add_question', quiz.id)

    return render(request, 'quiz/create_quiz.html')


@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)

    if not request.user.is_admin and  quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa bài kiểm tra này.")

    if request.method == 'POST':
        content = _normalize_quiz_text(request.POST.get('content', ''))
        answers = request.POST.get('answers', '').splitlines()

        choices, error = _parse_answers_for_question(content, '\n'.join(answers))
        if error:
            messages.error(request, error)
            return redirect('quiz:add_question', quiz.id)

        question = Question.objects.create(
            quiz=quiz,
            content=content,
            image=request.FILES.get('image') or None,
        )
        for choice_text, is_correct in choices:
            Choice.objects.create(question=question, content=choice_text, is_correct=is_correct)

        messages.success(request, "Đã thêm câu hỏi mới.")
        return redirect('quiz:add_question', quiz.id)

    questions = quiz.questions.all()
    template = get_template("quiz/add_question.html")
    print("TEMPLATE:", template.origin.name)
    return render(request, 'quiz/add_question.html', {
        'quiz': quiz,
        'questions': questions
    })


@login_required
def quiz_list(request):
    keyword = request.GET.get('q', '').strip()
    quizzes = Quiz.objects.select_related('created_by', 'classroom').prefetch_related('questions')

    if keyword:
        quizzes = quizzes.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(classroom__name__icontains=keyword)
        )

    return render(request, 'quiz/quiz_list.html', {
        'quizzes': quizzes.order_by('-created_at'),
        'keyword': keyword,
    })


@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.select_related('created_by', 'classroom').prefetch_related('questions__choices'),
        id=quiz_id
    )

    if not request.user.is_admin and not _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền xem đề thi này.")

    questions = list(quiz.questions.all())
    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1

    attempt_count = _quiz_attempt_count(request.user, quiz)
    blocked = bool(quiz.max_attempts and attempt_count >= quiz.max_attempts and quiz.created_by != request.user)

    return render(request, 'quiz/quiz_detail.html', {
        'quiz': quiz,
        'questions': questions,
        'blocked': blocked,
        'attempt_count': attempt_count,
    })


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.select_related('created_by', 'classroom').prefetch_related('questions__choices'),
        id=quiz_id
    )

    if not request.user.is_admin and not _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền làm bài kiểm tra này.")

    attempt_count = _quiz_attempt_count(request.user, quiz)
    if quiz.max_attempts and attempt_count >= quiz.max_attempts and quiz.created_by != request.user:
        return render(request, 'quiz/attempt_limit.html', {'quiz': quiz})

    question_order = request.GET.get('shuffle_questions')
    answer_order = request.GET.get('shuffle_answers')
    show_order_setup = question_order is None or answer_order is None
    shuffle_questions = question_order == '1'
    shuffle_answers = answer_order == '1'

    reload_key = f'quiz_active_{quiz.id}'
    if not show_order_setup:
        if quiz.max_attempts and quiz.created_by != request.user and request.session.get(reload_key):
            QuizReloadPenalty.objects.create(user=request.user, quiz=quiz)
            attempt_count += 1
        request.session[reload_key] = True

    questions = list(quiz.questions.all())
    if shuffle_questions:
        random.shuffle(questions)

    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1
        question.display_choices = list(question.choices.all())
        if shuffle_answers:
            random.shuffle(question.display_choices)

    if not show_order_setup:
        request.session[f'quiz_start_{quiz.id}'] = timezone.now().isoformat()

    return render(request, 'quiz/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'attempt_count': attempt_count,
        'show_order_setup': show_order_setup,
        'shuffle_questions': shuffle_questions,
        'shuffle_answers': shuffle_answers,
    })


@login_required
def submit_quiz(request, quiz_id):
    if request.method != 'POST':
        return redirect('quiz:take_quiz', quiz_id=quiz_id)

    quiz = get_object_or_404(
        Quiz.objects.select_related('created_by').prefetch_related('questions__choices'),
        id=quiz_id
    )

    if not request.user.is_admin and not _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền nộp bài kiểm tra này.")

    total_questions = quiz.questions.count()
    correct_answers = 0

    for question in quiz.questions.all():
        correct_ids = {
            str(choice.id)
            for choice in question.choices.all()
            if choice.is_correct
        }
        selected_ids = set(request.POST.getlist(f'question_{question.id}'))

        if correct_ids and selected_ids == correct_ids:
            correct_answers += 1

    score = round((correct_answers / total_questions) * 10) if total_questions else 0

    request.session.pop(f'quiz_active_{quiz.id}', None)
    start_time_str = request.session.pop(f'quiz_start_{quiz.id}', None)
    total_seconds = 0
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str)
            total_seconds = max(0, int((timezone.now() - start_time).total_seconds()))
        except ValueError:
            total_seconds = 0

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    QuizResult.objects.create(
        user=request.user,
        quiz=quiz,
        score=score
    )

    return render(request, 'quiz/result.html', {
        'quiz': quiz,
        'score': score,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'minutes': minutes,
        'seconds': seconds,
    })


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if not request.user.is_admin and quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa đề thi này.")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Tên đề thi không được để trống.")
            return redirect('quiz:edit_quiz', quiz.id)

        try:
            time_limit = int(request.POST.get('time_limit') or 0) or None
            max_attempts = int(request.POST.get('max_attempts') or 0) or None
            if (time_limit and time_limit < 1) or (max_attempts and max_attempts < 1):
                raise ValueError
        except ValueError:
            messages.error(request, "Thời gian và số lượt làm bài phải là số nguyên dương.")
            return redirect('quiz:edit_quiz', quiz.id)

        quiz.title = title
        quiz.description = request.POST.get('description', '').strip()
        quiz.time_limit = time_limit
        quiz.max_attempts = max_attempts
        quiz.save(update_fields=['title', 'description', 'time_limit', 'max_attempts'])
        messages.success(request, "Đã cập nhật thông tin đề thi.")
        return redirect('quiz:edit_quiz', quiz.id)

    return render(request, 'quiz/edit_quiz.html', {'quiz': quiz})

@login_required
def edit_question(request, question_id):
    question = get_object_or_404(
        Question.objects.select_related('quiz').prefetch_related('choices'),
        id=question_id
    )

    if not request.user.is_admin and question.quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa câu hỏi này.")

    if request.method == 'POST':
        question.content = _normalize_quiz_text(request.POST.get('content', ''))
        image = request.FILES.get('image')
        if request.POST.get('remove_image') and question.image:
            question.image.delete(save=False)
            question.image = None
        elif image:
            question.image = image
        question.save()

        choices, error = _parse_answers_for_question(question.content, request.POST.get('answers', ''))
        if error:
            messages.error(request, error)
            return redirect('quiz:edit_question', question.id)

        question.choices.all().delete()
        for choice_text, is_correct in choices:
            Choice.objects.create(question=question, content=choice_text, is_correct=is_correct)

        messages.success(request, "Đã lưu thay đổi câu hỏi.")
        return redirect('quiz:add_question', question.quiz.id)

    return render(request, 'quiz/edit_question.html', {'question': question})


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question.objects.select_related('quiz'), id=question_id)
    quiz = question.quiz

    if not request.user.is_admin and quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa câu hỏi này.")

    if request.method == 'POST':
        question.delete()
        messages.success(request, "Đã xóa câu hỏi.")

    return redirect('quiz:add_question', quiz.id)


@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if not request.user.is_admin and quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa đề thi này.")

    if request.method == 'POST':
        quiz.delete()
        messages.success(request, "Đã xóa đề thi.")

    return redirect('quiz:quiz_list')



@login_required
def download_quiz(request, quiz_id, format):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)

    filename = re.sub(r'[^\w-]+', '_', quiz.title, flags=re.UNICODE).strip('_') or 'de_kiem_tra'
    if format == 'docx':
        from docx import Document
        document = Document()
        document.add_heading(quiz.title, 0)
        if quiz.description:
            document.add_paragraph(quiz.description)
        for number, question in enumerate(quiz.questions.all(), start=1):
            document.add_heading(f'Câu {number}: {question.content}', level=2)
            for letter, choice in zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', question.choices.all()):
                marker = ' (Đáp án đúng)' if choice.is_correct else ''
                document.add_paragraph(f'{letter}. {choice.content}{marker}')
        buffer = BytesIO()
        document.save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{filename}.docx"'
        return response

    if format == 'pdf':
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from xml.sax.saxutils import escape
        except ImportError:
            return HttpResponse('PDF chưa sẵn sàng. Vui lòng tải bản Word.', status=503)

        font_regular = 'Helvetica'
        font_bold = 'Helvetica-Bold'
        font_candidates = [
            (r'C:\Windows\Fonts\DejaVuSans.ttf', r'C:\Windows\Fonts\DejaVuSans-Bold.ttf'),
            (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
        ]
        for regular_path, bold_path in font_candidates:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('TeddyUnicode', regular_path))
                pdfmetrics.registerFont(TTFont('TeddyUnicode-Bold', bold_path))
                font_regular = 'TeddyUnicode'
                font_bold = 'TeddyUnicode-Bold'
                break

        def paragraph_text(value):
            return escape(str(value or '')).replace('\n', '<br/>')

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=quiz.title,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'QuizTitle',
            parent=styles['Title'],
            fontName=font_bold,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=8,
        )
        description_style = ParagraphStyle(
            'QuizDescription',
            parent=styles['BodyText'],
            fontName=font_regular,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor('#475569'),
            spaceAfter=12,
        )
        question_style = ParagraphStyle(
            'QuizQuestion',
            parent=styles['BodyText'],
            fontName=font_bold,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#111827'),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )
        choice_style = ParagraphStyle(
            'QuizChoice',
            parent=styles['BodyText'],
            fontName=font_regular,
            fontSize=10,
            leading=15,
            leftIndent=8 * mm,
            firstLineIndent=-5 * mm,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=3,
        )
        correct_choice_style = ParagraphStyle(
            'QuizCorrectChoice',
            parent=choice_style,
            fontName=font_bold,
            textColor=colors.HexColor('#166534'),
        )

        story = [Paragraph(paragraph_text(quiz.title), title_style)]
        if quiz.description:
            story.append(Paragraph(paragraph_text(quiz.description), description_style))

        for number, question in enumerate(quiz.questions.all(), start=1):
            story.append(Paragraph(f'Câu {number}: {paragraph_text(question.content)}', question_style))
            for letter, choice in zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', question.choices.all()):
                suffix = ' (Đáp án đúng)' if choice.is_correct else ''
                style = correct_choice_style if choice.is_correct else choice_style
                story.append(Paragraph(f'{letter}. {paragraph_text(choice.content)}{suffix}', style))
            story.append(Spacer(1, 4))

        document.build(story)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response
    return HttpResponse(status=404)

@login_required
def flashcards(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)

    if not request.user.is_admin and not _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền xem flashcards của đề này.")

    questions = list(quiz.questions.all())
    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1

    return render(request, 'quiz/flashcards.html', {
        'quiz': quiz,
        'questions': questions,
    })


@login_required
def quiz_history(request):
    results = QuizResult.objects.filter(
        Q(user=request.user) |
        Q(quiz__created_by=request.user)
    ).select_related(
        'user',
        'quiz',
        'quiz__created_by'
    ).distinct().order_by('-created_at')

    return render(request, 'quiz/history.html', {'results': results})


@login_required
def delete_result(request, result_id):
    result = get_object_or_404(QuizResult, id=result_id)

    if not request.user.is_admin and result.quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa lịch sử này")

    if request.method == "POST":
        result.delete()
        messages.success(request, "Đã xóa lịch sử làm bài")

    return redirect('quiz:quiz_history')
