from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import FileResponse, Http404
import mimetypes
import os
from urllib.parse import quote
import cloudinary.api
from .models import Document
from .forms import DocumentForm



def _document_extension(document):
    for value in (document.file.name, document.file.url):
        extension = os.path.splitext((value or '').split('?', 1)[0])[1].lower()
        if extension:
            return extension

    for resource_type in ('image', 'raw', 'video'):
        try:
            resource = cloudinary.api.resource(document.file.name, resource_type=resource_type)
            file_format = resource.get('format')
            if file_format:
                return '.' + file_format.lower()
        except Exception:
            continue

    return ''


def _cloudinary_attachment_url(url):
    if not url or '/upload/' not in url:
        return url
    return url.replace('/upload/', '/upload/fl_attachment/', 1)


def _document_preview_context(document):
    extension = _document_extension(document)
    context = {
        'preview_type': 'unsupported',
        'preview_text': [],
        'preview_error': '',
        'file_extension': extension,
    }

    if extension == '.pdf':
        context['preview_type'] = 'pdf'
        return context

    if extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        context['preview_type'] = 'image'
        return context

    if extension in {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}:
        context['preview_type'] = 'office'
        context['office_preview_url'] = 'https://view.officeapps.live.com/op/embed.aspx?src=' + quote(document.file.url, safe='')
        return context

    try:
        if extension in {'.txt', '.csv'}:
            with document.file.open('rb') as file_obj:
                data = file_obj.read().decode('utf-8', errors='replace')
            context['preview_type'] = 'text'
            context['preview_text'] = [line for line in data.splitlines() if line.strip()]
            return context
    except Exception:
        context['preview_error'] = 'Không đọc được nội dung file để xem trước.'

    return context
@login_required
def document_list(request):

    documents = Document.objects.all().order_by('-created_at')

    q = request.GET.get('q')
    level = request.GET.get('level')
    subject = request.GET.get('subject')

    if q:
        documents = documents.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(subject__icontains=q)
        )

    if level:
        documents = documents.filter(level=level)

    if subject:
        documents = documents.filter(subject__icontains=subject)

    return render(
        request,
        'materials/document_list.html',
        {
            'documents': documents
        }
    )

@login_required
def edit_document(request, pk):
    doc = get_object_or_404(
        Document,
        pk=pk,
        owner=request.user
    )

    if request.method == "POST":

        doc.title = request.POST.get("title")
        doc.description = request.POST.get("description")
        doc.subject = request.POST.get("subject")
        doc.level = request.POST.get("level")
        doc.permission = request.POST.get("permission")

        if request.FILES.get("file"):
            doc.file = request.FILES.get("file")

        doc.save()

        messages.success(
            request,
            "Cập nhật tài liệu thành công."
        )

        return redirect("materials:document_list")

    return render(
        request,
        "materials/edit_document.html",
        {"doc": doc}
    )
@login_required
def delete_document(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)

    if request.method == "POST":
        doc.delete()
        return redirect("materials:document_list")

    return render(request, "materials/delete_document.html", {"doc": doc})
@login_required
def upload_document(request):

    if request.method == "POST":

        Document.objects.create(
            owner=request.user,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            level=request.POST.get("level"),
            subject=request.POST.get("subject"),
            permission=request.POST.get("permission"),
            file=request.FILES.get("file")
        )

        messages.success(
            request,
            "Tải tài liệu thành công."
        )

        return redirect("materials:document_list")

    return render(
        request,
        "materials/upload_document.html"
    )

@login_required
def download_document(request, pk):

    document = get_object_or_404(
        Document,
        pk=pk
    )

    context = {'document': document}
    context.update(_document_preview_context(document))

    return render(
        request,
        'materials/download_document.html',
        context
    )


@login_required
def document_file(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not document.file:
        raise Http404("Tài liệu chưa có file.")

    download = request.GET.get('download') == '1'
    filename = os.path.basename(document.file.name)
    content_type, _ = mimetypes.guess_type(filename)

    if download and document.file.url.startswith('http'):
        return redirect(_cloudinary_attachment_url(document.file.url))

    try:
        return FileResponse(
            document.file.open('rb'),
            as_attachment=download,
            filename=filename,
            content_type=content_type or 'application/octet-stream'
        )
    except Exception:
        target_url = _cloudinary_attachment_url(document.file.url) if download else document.file.url
        return redirect(target_url)
