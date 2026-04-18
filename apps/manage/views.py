from django.shortcuts import render


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')