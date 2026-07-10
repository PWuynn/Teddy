from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Quiz, Question, Choice, QuizResult
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import datetime
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from classroom.models import ClassroomMember
from django.template.loader import get_template
import re
import unicodedata


_CHOICE_MARKER_RE = re.compile(r'(?<!\w)[\s\-*]*(?:\(?[A-Fa-f]\)?)[\s]*[\.\):\-/\u2013\u2014]\s+')
_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*(?:\(?[A-Fa-f]\)?)[\s]*(?:[\.\):\-/\u2013\u2014]|\s+)')
_NAMED_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*(?:dap an|phuong an|option|choice)\s+([a-f])\s*[\.\):\-/\u2013\u2014]\s+')
_NUMERIC_CHOICE_LINE_RE = re.compile(r'^[\s\-*]*[1-9][0-9]*[\.\):\-/\u2013\u2014]\s+')
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
            letters = lowered.split(':', 1)[1]
            for letter in ('a', 'b', 'c', 'd', 'e', 'f'):
                if letter in letters:
                    correct_letters.add(letter)
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


def _is_choice_line(line):
    value = line.strip()
    if value.startswith('*'):
        value = value[1:].strip()
    return bool(_CHOICE_LINE_RE.match(value) or _NUMERIC_CHOICE_LINE_RE.match(value) or _NAMED_CHOICE_LINE_RE.match(_fold_quiz_text(value)))


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
    value = _NUMERIC_CHOICE_LINE_RE.sub('', value, count=1).strip()
    return _CHOICE_LINE_RE.sub('', value, count=1).strip()


def _parse_question_block(first_line_number, question_lines, answer_lines):
    question_text = _normalize_quiz_text('\n'.join(question_lines))
    correct_letters, answer_lines = _extract_correct_letters(answer_lines)

    if not question_text:
        return None, f'Dòng {first_line_number}: câu hỏi không hợp lệ.'

    if len(answer_lines) < 2:
        return None, f'Dòng {first_line_number}: mỗi câu hỏi cần ít nhất 2 đáp án.'

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


def _parse_uploaded_quiz_file(uploaded_file):
    text = _decode_uploaded_text(uploaded_file).replace('\r\n', '\n').replace('\r', '\n')
    questions = []
    errors = []
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

def _generate_ai_questions(topic, count):
    base = topic.strip() or "chủ đề học tập"
    templates = [
        ("Khái niệm cốt lõi nhất của {topic} là gì?", ["Một nguyên tắc nền tảng giúp giải thích và áp dụng kiến thức", "Một chi tiết phụ ít liên quan", "Một công cụ trang trí giao diện", "Một lỗi thường gặp"]),
        ("Khi học {topic}, bước nào nên làm trước?", ["Nắm mục tiêu và các khái niệm chính", "Bỏ qua lý thuyết", "Chỉ ghi nhớ đáp án", "Không cần luyện tập"]),
        ("Dấu hiệu nào cho thấy bạn đã hiểu {topic}?", ["Giải thích được bằng lời của mình và áp dụng vào bài tập", "Chỉ đọc lướt tiêu đề", "Chỉ nhớ một ví dụ", "Không trả lời được câu hỏi mới"]),
        ("Cách ôn tập {topic} hiệu quả là gì?", ["Chia nhỏ kiến thức, luyện câu hỏi và tự kiểm tra", "Học dồn vào phút cuối", "Không ghi chú", "Chỉ xem đáp án"]),
        ("Sai lầm phổ biến khi học {topic} là gì?", ["Không liên hệ kiến thức với ví dụ hoặc bài tập", "Ôn tập đều đặn", "Đặt câu hỏi khi chưa hiểu", "Tự đánh giá tiến độ"]),
    ]
    questions = []
    for index in range(max(1, min(count, 20))):
        content, choices = templates[index % len(templates)]
        questions.append((content.format(topic=base), choices))
    return questions


def _can_access_quiz(user, quiz):
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
                generated_questions = _generate_ai_questions(title or description or "chủ đề học tập", 10)
                with transaction.atomic():
                    for content, choices in generated_questions:
                        question = Question.objects.create(quiz=quiz, content=content)
                        for index, choice_text in enumerate(choices):
                            Choice.objects.create(
                                question=question,
                                content=choice_text,
                                is_correct=index == 0
                            )
                messages.success(request, "Đã tạo nhanh 10 câu hỏi AI mẫu. Bạn có thể chỉnh sửa lại đáp án nếu cần.")
                return redirect('quiz_ai:add_question', quiz.id)

            parsed_questions, parse_errors = _parse_uploaded_quiz_file(quiz_file)
            if not parsed_questions:
                quiz.delete()
                messages.error(request, "File chưa có câu hỏi đúng cấu trúc. Bài kiểm tra chưa được tạo.")
                for error in parse_errors[:10]:
                    messages.warning(request, error)
                return render(request, 'quiz_ai/create_quiz.html')

            with transaction.atomic():
                for content, choices in parsed_questions:
                    question = Question.objects.create(quiz=quiz, content=content)
                    for choice_text, is_correct in choices:
                        Choice.objects.create(
                            question=question,
                            content=choice_text,
                            is_correct=is_correct
                        )

            messages.success(request, f"Đã tạo {len(parsed_questions)} câu hỏi từ file tải lên.")
            if parse_errors:
                messages.warning(request, f"Có {len(parse_errors)} câu hỏi/dòng sai cấu trúc và đã được bỏ qua.")
                for error in parse_errors[:10]:
                    messages.warning(request, error)
            return redirect('quiz_ai:quiz_detail', quiz.id)
        manual_questions = request.POST.get('manual_questions', '').strip()
        if manual_questions:
            for lines in _split_manual_question_blocks(manual_questions):
                if len(lines) < 2:
                    continue
                question = Question.objects.create(quiz=quiz, content=_normalize_quiz_text(lines[0]))
                for line in lines[1:]:
                    is_correct = line.startswith('*')
                    Choice.objects.create(
                        question=question,
                        content=_normalize_quiz_text(line[1:].strip() if is_correct else line),
                        is_correct=is_correct
                    )
            return redirect('quiz_ai:quiz_detail', quiz.id)

        return redirect('quiz_ai:add_question', quiz.id)

    return render(request, 'quiz_ai/create_quiz.html')


@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)

    if not request.user.is_admin and  quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa bài kiểm tra này.")

    if request.method == 'POST':
        content = _normalize_quiz_text(request.POST.get('content', ''))
        answers = request.POST.get('answers', '').splitlines()

        question = Question.objects.create(quiz=quiz, content=content)

        for ans in answers:
            ans = ans.strip()
            if not ans:
                continue

            is_correct = ans.startswith('*')
            Choice.objects.create(
                question=question,
                content=_normalize_quiz_text(ans[1:].strip() if is_correct else ans),
                is_correct=is_correct
            )

        messages.success(request, "Đã thêm câu hỏi mới.")
        return redirect('quiz_ai:add_question', quiz.id)

    questions = quiz.questions.all()
    template = get_template("quiz_ai/add_question.html")
    print("TEMPLATE:", template.origin.name)
    return render(request, 'quiz_ai/add_question.html', {
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

    return render(request, 'quiz_ai/quiz_list.html', {
        'quizzes': quizzes.order_by('-created_at'),
        'keyword': keyword,
    })


@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.select_related('created_by', 'classroom').prefetch_related('questions__choices'),
        id=quiz_id
    )

    if not request.user.is_admin and  _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền xem đề thi này.")

    questions = list(quiz.questions.all())
    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1

    attempt_count = QuizResult.objects.filter(user=request.user, quiz=quiz).count()
    blocked = bool(quiz.max_attempts and attempt_count >= quiz.max_attempts and quiz.created_by != request.user)

    return render(request, 'quiz_ai/quiz_detail.html', {
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

    if not request.user.is_admin and  _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền làm bài kiểm tra này.")

    attempt_count = QuizResult.objects.filter(user=request.user, quiz=quiz).count()
    if quiz.max_attempts and attempt_count >= quiz.max_attempts and quiz.created_by != request.user:
        return render(request, 'quiz_ai/attempt_limit.html', {'quiz': quiz})

    questions = list(quiz.questions.all())
    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1

    request.session[f'quiz_start_{quiz.id}'] = timezone.now().isoformat()

    return render(request, 'quiz_ai/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'attempt_count': attempt_count,
    })


@login_required
def submit_quiz(request, quiz_id):
    if request.method != 'POST':
        return redirect('quiz_ai:take_quiz', quiz_id=quiz_id)

    quiz = get_object_or_404(
        Quiz.objects.select_related('created_by').prefetch_related('questions__choices'),
        id=quiz_id
    )

    if not request.user.is_admin and _can_access_quiz(request.user, quiz):
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

    return render(request, 'quiz_ai/result.html', {
        'quiz': quiz,
        'score': score,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'minutes': minutes,
        'seconds': seconds,
    })


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(
        Question.objects.select_related('quiz').prefetch_related('choices'),
        id=question_id
    )

    if not request.user.is_admin and question.quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa câu hỏi này.")

    if request.method == 'POST':
        question.quiz.title = request.POST.get('title', '').strip()
        question.quiz.description = request.POST.get('description', '').strip()
        question.quiz.save(update_fields=['title', 'description'])

        question.content = _normalize_quiz_text(request.POST.get('content', ''))
        question.save(update_fields=['content'])

        question.choices.all().delete()
        for answer in request.POST.get('answers', '').splitlines():
            answer = answer.strip()
            if not answer:
                continue
            is_correct = answer.startswith('*')
            Choice.objects.create(
                question=question,
                content=_normalize_quiz_text(answer[1:].strip() if is_correct else answer),
                is_correct=is_correct
            )

        messages.success(request, "Đã lưu thay đổi câu hỏi.")
        return redirect('quiz_ai:add_question', question.quiz.id)

    return render(request, 'quiz_ai/edit_question.html', {'question': question})


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question.objects.select_related('quiz'), id=question_id)
    quiz = question.quiz

    if not request.user.is_admin and quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa câu hỏi này.")

    if request.method == 'POST':
        question.delete()
        messages.success(request, "Đã xóa câu hỏi.")

    return redirect('quiz_ai:add_question', quiz.id)


@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if not request.user.is_admin and quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa đề thi này.")

    if request.method == 'POST':
        quiz.delete()
        messages.success(request, "Đã xóa đề thi.")

    return redirect('quiz_ai:quiz_list')


@login_required
def flashcards(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), id=quiz_id)

    if not request.user.is_admin and _can_access_quiz(request.user, quiz):
        return HttpResponseForbidden("Bạn không có quyền xem flashcards của đề này.")

    questions = list(quiz.questions.all())
    for question in questions:
        question.allows_multiple = sum(1 for choice in question.choices.all() if choice.is_correct) > 1

    return render(request, 'quiz_ai/quiz_detail.html', {
        'quiz': quiz,
        'questions': questions,
        'blocked': False,
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

    return render(request, 'quiz_ai/history.html', {'results': results})


@login_required
def delete_result(request, result_id):
    result = get_object_or_404(QuizResult, id=result_id)

    if not request.user.is_admin and result.quiz.created_by != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa lịch sử này")

    if request.method == "POST":
        result.delete()
        messages.success(request, "Đã xóa lịch sử làm bài")

    return redirect('quiz_ai:quiz_history')




