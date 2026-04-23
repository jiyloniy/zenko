from urllib import request

from django.shortcuts import render, redirect



def home(request):
    return redirect('login')