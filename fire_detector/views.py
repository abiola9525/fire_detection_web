from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from .forms import DetectionForm
from .models import Detection
from .utils import process_upload
import os
import threading

def home(request):
    """Home page with upload form"""
    form = DetectionForm()
    context = {
        'form': form,
    }
    return render(request, 'home.html', context)

def detect_fire(request):
    """Handle file upload and fire detection"""
    if request.method == 'POST':
        form = DetectionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the detection object
                detection = form.save()
                
                # Process the upload in a separate thread to avoid blocking
                def process_async():
                    try:
                        process_upload(detection)
                    except Exception as e:
                        print(f"Error in async processing: {e}")
                        # Update detection with error status
                        detection.has_fire = False
                        detection.confidence = 0.0
                        detection.save()
                
                threading.Thread(target=process_async, daemon=True).start()
                
                # Redirect to results page
                return redirect('fire_detector:results', file_id=detection.id)
                
            except Exception as e:
                print(f"Error saving detection: {e}")
                messages.error(request, "Error processing your file. Please try again.")
        else:
            # Form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    # If we get here, there was an error - redirect back to home
    return redirect('fire_detector:home')

def results(request, file_id):
    """Display detection results"""
    try:
        detection = get_object_or_404(Detection, id=file_id)
        
        # Check if processing is complete
        processing_complete = (
            detection.result_file and 
            detection.result_file.name and 
            os.path.exists(detection.result_file.path)
        )
        
        # Calculate confidence percentage
        confidence_percentage = detection.confidence * 100
        
        context = {
            'detection': detection,
            'processing_complete': processing_complete,
            'confidence_percentage': confidence_percentage,
        }
        
        return render(request, 'results.html', context)
        
    except Exception as e:
        print(f"Error in results view: {e}")
        messages.error(request, "Error loading results. Please try uploading again.")
        return redirect('fire_detector:home')