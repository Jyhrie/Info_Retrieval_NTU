from django.shortcuts import render
from .forms import TextForm

def home(request):
    form = TextForm()
    return render(request, 'home.html', {'form': form})
