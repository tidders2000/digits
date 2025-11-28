from django.shortcuts import render,redirect

from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required
from django.contrib import auth, messages
# Create your views here.
def register(request):
    if request.method== 'POST':
        form=RegisterForm(request.POST)
        if form.is_valid ():
            form.save()
            username=form.cleaned_data.get('username')
            messages.success(request,f'Welcome {username} ,your account is created')
            return redirect('login')
    else:       

  
        form =RegisterForm()
    return render(request,'users/register.html',{'form':form})

@login_required
def profilepage(request):
    return render(request,'users/profile.html')

def logout(request):
    """Log the user out"""

    
    auth.logout(request)
    messages.success(request, "You have successfully been logged out")
    return redirect('login')
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keeps them logged in
            messages.success(request, 'Password updated successfully.')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})