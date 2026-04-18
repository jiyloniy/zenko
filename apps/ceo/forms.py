from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from apps.users.models import Department, Role, Shift, User
from apps.attendance.models import Attendance
from apps.attendance.utils import parse_time_24h


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
        fields = ('user', 'date', 'status', 'check_in', 'check_out')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'check_out': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['user'].queryset = User.objects.filter(branch=branch, is_active=True)
        self.fields['check_in'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['check_out'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['check_in'].required = False
        self.fields['check_out'].required = False

    def clean(self):
        data = super().clean()
        st = data.get('status')
        ci = data.get('check_in')
        co = data.get('check_out')
        if st == Attendance.STATUS_ABSENT:
            data['check_in'] = None
            data['check_out'] = None
        elif not ci:
            raise forms.ValidationError('Kelmadi bo\'lmasa, kirish vaqtini kiriting.')
        if co and not ci:
            raise forms.ValidationError('Chiqish vaqti bo\'lsa, kirish vaqti ham bo\'lishi kerak.')
        return data


class BulkAttendanceForm(forms.Form):
    """Ommaviy: kelmadi yoki kirish/chiqish vaqtlari bilan yozuv."""

    MODE_ABSENT = 'absent'
    MODE_TIMES = 'times'

    date = forms.DateField(
        label='Sana',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'bulk-input'}),
    )
    mode = forms.ChoiceField(
        label='Tur',
        choices=[
            (MODE_ABSENT, 'Kelmadi (kirish/chiqishsiz)'),
            (MODE_TIMES, 'Kirish va chiqish vaqtlari bilan'),
        ],
        initial=MODE_ABSENT,
        widget=forms.RadioSelect(attrs={'class': 'bulk-mode-radios'}),
    )
    check_in_time = forms.CharField(
        label='Kirish vaqti (24 soat)',
        required=False,
        max_length=5,
        widget=forms.TextInput(
            attrs={
                'class': 'bulk-input bulk-time-24',
                'placeholder': '08:30',
                'pattern': r'([01]?[0-9]|2[0-3]):[0-5][0-9]',
                'title': '24 soat: masalan 08:30 yoki 17:45',
                'inputmode': 'numeric',
                'autocomplete': 'off',
            },
        ),
    )
    check_out_time = forms.CharField(
        label='Chiqish vaqti (24 soat, ixtiyoriy)',
        required=False,
        max_length=5,
        widget=forms.TextInput(
            attrs={
                'class': 'bulk-input bulk-time-24',
                'placeholder': '17:00',
                'pattern': r'([01]?[0-9]|2[0-3]):[0-5][0-9]',
                'title': '24 soat: masalan 17:00',
                'inputmode': 'numeric',
                'autocomplete': 'off',
            },
        ),
    )
    users = forms.ModelMultipleChoiceField(
        label='Hodimlar',
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['users'].queryset = User.objects.filter(branch=branch, is_active=True).select_related('department', 'shift')

    def clean(self):
        data = super().clean()
        mode = data.get('mode')
        if mode != self.MODE_TIMES:
            return data
        raw_in = (data.get('check_in_time') or '').strip()
        raw_out = (data.get('check_out_time') or '').strip()
        if not raw_in:
            raise ValidationError('«Kirish va chiqish vaqtlari» rejimida kirish vaqti majburiy (24 soat, masalan 08:30).')
        try:
            data['check_in_time'] = parse_time_24h(raw_in)
        except ValueError as e:
            raise ValidationError(str(e)) from e
        if raw_out:
            try:
                data['check_out_time'] = parse_time_24h(raw_out)
            except ValueError as e:
                raise ValidationError(str(e)) from e
            data['_checkout_blank'] = False
        else:
            data['check_out_time'] = None
            data['_checkout_blank'] = True
        return data
