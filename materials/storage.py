import os

from cloudinary_storage.storage import MediaCloudinaryStorage, RESOURCE_TYPES
from django.utils.deconstruct import deconstructible


@deconstructible
class DocumentCloudinaryStorage(MediaCloudinaryStorage):
    RAW_EXTENSIONS = {
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.csv', '.rtf', '.zip', '.rar', '.7z',
    }

    def _get_resource_type(self, name):
        extension = os.path.splitext(name)[1].lower()
        if extension in self.RAW_EXTENSIONS:
            return RESOURCE_TYPES['RAW']
        return super()._get_resource_type(name)