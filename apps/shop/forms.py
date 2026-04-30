from django import forms
from apps.order.models import Order, Brujka


class ShopOrderForm(forms.ModelForm):
    """Shop manager uchun buyurtma formasi — status yo'q, faqat NEW."""

    class Meta:
        model = Order
        fields = ('brujka', 'name', 'quantity', 'image', 'deadline', 'priority', 'note')
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False
        self.fields['brujka'].required = False
        self.fields['image'].required = False
        self.fields['note'].required = False
