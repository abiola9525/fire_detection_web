from django import forms
from .models import Detection

class DetectionForm(forms.ModelForm):
    class Meta:
        model = Detection
        fields = ['uploaded_file']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uploaded_file'].widget.attrs.update({
            'class': 'form-control-file',
            'id': 'uploadFile',
            'accept': 'image/*,video/*',
        })
        
    def clean_uploaded_file(self):
        file = self.cleaned_data.get('uploaded_file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'mp4', 'avi', 'mov']:
                raise forms.ValidationError("Unsupported file type. Please upload an image (jpg, jpeg, png) or video (mp4, avi, mov).")
            if ext in ['mp4', 'avi', 'mov']:
                self.instance.is_video = True
        return file