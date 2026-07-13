from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField


class Quiz(models.Model):

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    null=True,
    blank=True
)
    classroom = models.ForeignKey(
        'classroom.Classroom',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Cài đặt đề kiểm tra

    max_attempts = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Số lượt làm tối đa"
    )

    time_limit = models.IntegerField(
        default=30,
        verbose_name="Giới hạn thời gian (phút)"
    )

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    content = models.TextField()

    explanation = models.TextField(blank=True, default='')

    if settings.USE_CLOUDINARY_MEDIA:
        image = CloudinaryField(
            folder='teddy/quiz_question_images',
            null=True,
            blank=True,
        )
    else:
        image = models.ImageField(
            upload_to='quiz_question_images/',
            null=True,
            blank=True
        )

    def __str__(self):
        return self.content


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )

    content = models.CharField(max_length=255)

    is_correct = models.BooleanField(default=False)

    if settings.USE_CLOUDINARY_MEDIA:
        image = CloudinaryField(folder='teddy/quiz_choice_images', null=True, blank=True)
    else:
        image = models.ImageField(upload_to='quiz_choice_images/', null=True, blank=True)

    def __str__(self):
        return self.content
    

class QuizReloadPenalty(models.Model):
    """A limited-attempt quiz consumes one attempt when its active page reloads."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class QuizResult(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    quiz = models.ForeignKey(
        'Quiz',
        on_delete=models.CASCADE
    )

    score = models.IntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user} - {self.quiz}"