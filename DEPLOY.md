# Deploy TEDDY

Du an da san sang de deploy len cac nen tang Python/Django nhu Render, Railway hoac VPS.

## Bien moi truong can cau hinh

- `SECRET_KEY`: khoa bao mat moi, khong dung gia tri mac dinh.
- `DEBUG`: dat `False` khi deploy that.
- `ALLOWED_HOSTS`: domain cua web, vi du `teddy.onrender.com`.
- `CSRF_TRUSTED_ORIGINS`: origin day du, vi du `https://teddy.onrender.com`.
- `DATABASE_URL`: chuoi ket noi database cloud, nen dung PostgreSQL/MySQL managed.
- `OPENROUTER_API_KEY`: key AI neu chatbot/AI can goi API ngoai.

## Lenh build/run pho bien

Build command:

```bash
./build.sh
```

Start command:

```bash
gunicorn study_support.wsgi:application
```

## Luu y

- Khong nen dung database MySQL local `127.0.0.1` khi deploy len mang.
- File upload trong thu muc `media` can storage ben ngoai neu muon luu ben vung lau dai tren cloud.
- Sau khi co domain that, cap nhat `ALLOWED_HOSTS` va `CSRF_TRUSTED_ORIGINS` dung domain do.

## Ảnh và avatar trên Render

Render dùng filesystem tạm thời, vì vậy không lưu ảnh upload trong thư mục `media` nếu dịch vụ restart hoặc deploy lại. Ứng dụng đã dùng Cloudinary cho avatar và hình ảnh câu hỏi khi có đủ ba biến môi trường sau:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Trong Render Dashboard, vào **Environment** và thêm ba biến này từ trang Cloudinary Dashboard, sau đó deploy lại. Ảnh mới upload sẽ có URL Cloudinary và vẫn hiển thị sau deploy/restart.
