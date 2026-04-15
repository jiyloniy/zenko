from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.users.models import Branch, Department, Role, Shift, User


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ('name', 'address', 'phone', 'is_active')


class BranchDepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('name', 'description')


class BranchShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ('name', 'start_time', 'end_time', 'break_start', 'break_end', 'description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        time_attrs = {
            'class': 'form-control',
            'maxlength': '5',
            'pattern': r'([01]?[0-9]|2[0-3]):[0-5][0-9]',
        }
        self.fields['start_time'].widget = forms.TimeInput(
            format='%H:%M', attrs={**time_attrs, 'placeholder': '08:00'},
        )
        self.fields['end_time'].widget = forms.TimeInput(
            format='%H:%M', attrs={**time_attrs, 'placeholder': '17:00'},
        )
        self.fields['break_start'].widget = forms.TimeInput(
            format='%H:%M', attrs={**time_attrs, 'placeholder': '12:00'},
        )
        self.fields['break_end'].widget = forms.TimeInput(
            format='%H:%M', attrs={**time_attrs, 'placeholder': '13:00'},
        )


class BranchUserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'name', 'phone', 'role', 'department', 'shift', 'is_active')


class BranchUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'name', 'phone', 'role', 'department', 'shift', 'is_active')
