from django import forms
from django.utils import timezone
from .models import Chore


class ChoreForm(forms.ModelForm):
    """Form to create a new chore."""
    
    class Meta:
        model = Chore
        fields = ['description', 'priority']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Describe the chore...'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }


class CompleteChoreForm(forms.ModelForm):
    """Form to mark a chore as completed."""
    
    class Meta:
        model = Chore
        fields = ['completed_by']
        widgets = {
            'completed_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name...'}),
        }
    
    def save(self, commit=True):
        """Override save to set status and completed_at when marking complete."""
        chore = super().save(commit=False)
        chore.status = 'completed'
        chore.completed_at = timezone.now()
        if commit:
            chore.save()
        return chore
