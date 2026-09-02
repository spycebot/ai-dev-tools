from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Chore
from .forms import ChoreForm, CompleteChoreForm


def chore_list(request):
    """Display all chores, sorted by status and priority."""
    chores = Chore.objects.all()
    pending_chores = chores.filter(status='pending').order_by('-priority')
    completed_chores = chores.filter(status='completed').order_by('-completed_at')
    
    context = {
        'pending_chores': pending_chores,
        'completed_chores': completed_chores,
    }
    return render(request, 'chores/chore_list.html', context)


@require_http_methods(["GET", "POST"])
def add_chore(request):
    """Add a new chore to the list."""
    if request.method == 'POST':
        form = ChoreForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('chore_list')
    else:
        form = ChoreForm()
    
    return render(request, 'chores/add_chore.html', {'form': form})


@require_http_methods(["GET", "POST"])
def complete_chore(request, pk):
    """Mark a chore as complete."""
    chore = get_object_or_404(Chore, pk=pk)
    
    if request.method == 'POST':
        form = CompleteChoreForm(request.POST, instance=chore)
        if form.is_valid():
            form.save()
            return redirect('chore_list')
    else:
        form = CompleteChoreForm(instance=chore)
    
    return render(request, 'chores/complete_chore.html', {'form': form, 'chore': chore})
