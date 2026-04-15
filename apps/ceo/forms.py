from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.users.models import Department, Role, Shift, User
from apps.attendance.models import Attendance


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'name', 'phone', 'role', 'department', 'shift', 'is_active')


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'name', 'phone', 'role', 'department', 'shift', 'is_active')


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ('name', 'description')


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('name', 'description')


class ShiftForm(forms.ModelForm):
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


class AttendanceForm(forms.ModelForm):
    """Qo'lda davomat qo'shish / tahrirlash."""

    class Meta:
        model = Attendance
        fields = ('user', 'shift', 'date', 'check_in', 'check_out', 'status', 'is_overtime')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'check_out': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['user'].queryset = User.objects.filter(branch=branch, is_active=True)
            self.fields['shift'].queryset = Shift.objects.filter(branch=branch)
        self.fields['check_in'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['check_out'].input_formats = ['%Y-%m-%dT%H:%M']


class BulkAttendanceForm(forms.Form):
    """Bir nechta hodimga bir vaqtda davomat belgilash."""
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    shift = forms.ModelChoiceField(queryset=Shift.objects.none(), required=False)
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    status = forms.ChoiceField(choices=Attendance.STATUS_CHOICES)
    is_overtime = forms.BooleanField(required=False)

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['users'].queryset = User.objects.filter(branch=branch, is_active=True).select_related('department', 'shift')
            self.fields['shift'].queryset = Shift.objects.filter(branch=branch)
