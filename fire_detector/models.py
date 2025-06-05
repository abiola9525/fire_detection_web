from django.db import models
import uuid
import os

def get_upload_path(instance, filename):
    """Generate unique path for uploaded files"""
    ext = filename.split('.')[-1]
    filename = f"{instance.id}.{ext}"
    return os.path.join('uploads', filename)

def get_result_path(instance, filename):
    """Generate unique path for result files"""
    ext = filename.split('.')[-1]
    filename = f"{instance.id}_result.{ext}"
    return os.path.join('results', filename)

class Detection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_file = models.FileField(upload_to=get_upload_path)
    result_file = models.FileField(upload_to=get_result_path, null=True, blank=True)
    is_video = models.BooleanField(default=False)
    has_fire = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Detection {self.id}"
    
    def filename(self):
        return os.path.basename(self.uploaded_file.name)