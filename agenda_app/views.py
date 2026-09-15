from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from .models import AgendaItem

def dashboard_view(request):
    status_filter = request.GET.get('status', 'all')
    items = AgendaItem.objects.all().order_by('date', 'id')
    
    if status_filter == 'pending':
        items = items.filter(completed=False)
    elif status_filter == 'completed':
        items = items.filter(completed=True)
        
    context = {
        'items': items,
        'status_filter': status_filter,
    }
    return render(request, 'agenda_app/dashboard.html', context)

def toggle_complete(request, pk):
    item = get_object_or_404(AgendaItem, pk=pk)
    item.completed = not item.completed
    item.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'completed': item.completed})
    return redirect('dashboard')
