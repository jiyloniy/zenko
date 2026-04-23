# 🔧 Stanok Model - Amaliy API & Foydalanish Namunalari

## 1. DATABASE QUERIES (ORM)

### Create (Yaratish)

```python
from apps.casting.models import Stanok

# 1️⃣ Oddiy yaratish
stanok = Stanok.objects.create(
    name="CNC-100",
    status="active"
)

# 2️⃣ Form orqali (Validated)
from apps.casting.forms import StanokForm
form = StanokForm(data={'name': 'Laser 500', 'status': 'active'})
if form.is_valid():
    stanok = form.save()
else:
    print(form.errors)

# 3️⃣ Bulk create
stanoklar = [
    Stanok(name=f"Stanok {i}", status="active")
    for i in range(1, 6)
]
Stanok.objects.bulk_create(stanoklar)
```

### Read (O'qish)

```python
# 1️⃣ Bittasini ID orqali
stanok = Stanok.objects.get(pk=1)

# 2️⃣ get_object_or_404 (View'da xavfsiz)
from django.shortcuts import get_object_or_404
stanok = get_object_or_404(Stanok, pk=1)

# 3️⃣ Barcha stanoklar
all_stanoklar = Stanok.objects.all()

# 4️⃣ Faol stanoklar faqat
active = Stanok.objects.filter(status=Stanok.Status.ACTIVE)

# 5️⃣ Status bo'yicha filter
repairs = Stanok.objects.filter(status="repair")
inactive = Stanok.objects.filter(status=Stanok.Status.INACTIVE)

# 6️⃣ Nomi bo'yicha qidiruv (Case-insensitive)
results = Stanok.objects.filter(name__icontains="CNC")

# 7️⃣ Qidiruv + Filter
results = Stanok.objects.filter(
    name__icontains="CNC",
    status=Stanok.Status.ACTIVE
)

# 8️⃣ Ordering
sorted_asc = Stanok.objects.all().order_by('name')
sorted_desc = Stanok.objects.all().order_by('-name')

# 9️⃣ Statistika
total = Stanok.objects.count()
active_count = Stanok.objects.filter(status=Stanok.Status.ACTIVE).count()

# 🔟 Limit & Offset
first_5 = Stanok.objects.all()[:5]
skip_10_take_5 = Stanok.objects.all()[10:15]
```

### Update (Yangilash)

```python
# 1️⃣ Bitta objektni yangilash
stanok = Stanok.objects.get(pk=1)
stanok.name = "Yangi nomi"
stanok.status = Stanok.Status.REPAIR
stanok.save()

# 2️⃣ QuerySet bulk update
Stanok.objects.filter(status=Stanok.Status.ACTIVE).update(
    status=Stanok.Status.INACTIVE
)

# 3️⃣ Form orqali (Validated)
stanok = Stanok.objects.get(pk=1)
form = StanokForm(
    data={'name': 'Yangi nomi', 'status': 'repair'},
    instance=stanok
)
if form.is_valid():
    updated = form.save()
```

### Delete (O'chirish)

```python
# 1️⃣ Bitta objektni o'chirish
stanok = Stanok.objects.get(pk=1)
stanok.delete()

# 2️⃣ QuerySet bulk delete
Stanok.objects.filter(status=Stanok.Status.INACTIVE).delete()

# 3️⃣ Barchasini o'chirish
Stanok.objects.all().delete()
```

---

## 2. VIEW'DA FOYDALANISH

### StanokListView - Qidiruv va Filtrlash

```python
from django.shortcuts import render, get_object_or_404
from django.views import View
from apps.casting.models import Stanok

class StanokListView(View):
    def get(self, request):
        # Query parametrlarini olish
        q = request.GET.get('q', '').strip()
        status_f = request.GET.get('status', '')
        
        # QuerySet yaratish
        qs = Stanok.objects.all()
        
        # Qidiruv filteri
        if q:
            qs = qs.filter(name__icontains=q)
        
        # Status filteri
        if status_f:
            qs = qs.filter(status=status_f)
        
        # Statistika
        counts = {
            'total':    Stanok.objects.count(),
            'active':   Stanok.objects.filter(status=Stanok.Status.ACTIVE).count(),
            'repair':   Stanok.objects.filter(status=Stanok.Status.REPAIR).count(),
            'inactive': Stanok.objects.filter(status=Stanok.Status.INACTIVE).count(),
        }
        
        return render(request, 'casting/stanok_list.html', {
            'stanoklar': qs,
            'q': q,
            'status_f': status_f,
            'counts': counts,
            'statuses': Stanok.Status.choices,
        })
```

### StanokCreateView - Form orqali Yaratish

```python
from django.contrib import messages
from apps.casting.forms import StanokForm

class StanokCreateView(View):
    def get(self, request):
        form = StanokForm()
        return render(request, 'casting/stanok_form.html', {
            'title': 'Yangi stanok',
            'form': form,
        })
    
    def post(self, request):
        form = StanokForm(request.POST)
        if form.is_valid():
            stanok = form.save()
            messages.success(request, f'"{stanok.name}" qo\'shildi')
            return redirect('casting:stanok_list')
        
        return render(request, 'casting/stanok_form.html', {
            'title': 'Yangi stanok',
            'form': form,
        })
```

### StanokUpdateView - Form orqali Tahrirlash

```python
class StanokUpdateView(View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        form = StanokForm(instance=stanok)
        return render(request, 'casting/stanok_form.html', {
            'title': f'{stanok.name} — tahrirlash',
            'form': form,
        })
    
    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        form = StanokForm(request.POST, instance=stanok)
        if form.is_valid():
            stanok = form.save()
            messages.success(request, f'"{stanok.name}" yangilandi')
            return redirect('casting:stanok_list')
        
        return render(request, 'casting/stanok_form.html', {
            'title': f'{stanok.name} — tahrirlash',
            'form': form,
        })
```

---

## 3. TEMPLATE'DA FOYDALANISH

### Ro'yxat (List)

```html
<table>
    <thead>
        <tr>
            <th>Nomi</th>
            <th>Holat</th>
            <th>Amallar</th>
        </tr>
    </thead>
    <tbody>
        {% for stanok in stanoklar %}
        <tr>
            <td>{{ stanok.name }}</td>
            <td>
                <span class="status-{{ stanok.status }}">
                    {{ stanok.get_status_display }}
                </span>
            </td>
            <td>
                <a href="{% url 'casting:stanok_edit' stanok.pk %}">
                    Tahrirlash
                </a>
                <a href="{% url 'casting:stanok_delete' stanok.pk %}">
                    O'chirish
                </a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<!-- Filtr forma -->
<form method="get">
    <input type="text" name="q" value="{{ q }}" placeholder="Nomi bo'yicha qidirish...">
    <select name="status">
        <option value="">Barcha holatlar</option>
        {% for val, label in statuses %}
            <option value="{{ val }}" {% if val == status_f %}selected{% endif %}>
                {{ label }}
            </option>
        {% endfor %}
    </select>
    <button type="submit">Qidirish</button>
</form>
```

### Form (Create/Edit)

```html
<form method="post">
    {% csrf_token %}
    
    <!-- Nomi maydoni -->
    <div class="form-group">
        <label for="id_name">Nomi *</label>
        {{ form.name }}
        {% if form.name.errors %}
            <span class="error">{{ form.name.errors.0 }}</span>
        {% endif %}
    </div>
    
    <!-- Holat maydoni -->
    <div class="form-group">
        <label>Holat</label>
        <div class="radio-group">
            {% for value, label in form.fields.status.choices %}
                <label>
                    <input type="radio" name="status" value="{{ value }}"
                        {% if form.status.value == value %}checked{% endif %}>
                    {{ label }}
                </label>
            {% endfor %}
        </div>
        {% if form.status.errors %}
            <span class="error">{{ form.status.errors.0 }}</span>
        {% endif %}
    </div>
    
    <button type="submit">
        {% if form.instance.pk %}Saqlash{% else %}Qo'shish{% endif %}
    </button>
</form>
```

---

## 4. FORM VALIDATION

```python
from apps.casting.forms import StanokForm

# Foydalanuvchi ma'lumotlari
data = {
    'name': 'CNC №1',
    'status': 'active'
}

form = StanokForm(data=data)

if form.is_valid():
    print("✅ Form ma'lumotlari to'g'ri")
    stanok = form.save()
    print(f"Yaratildi: {stanok.name}")
else:
    print("❌ Form ma'lumotlarida xatolar:")
    print(form.errors)
    # Output:
    # {
    #     'name': ['Bu nomi bilan stanok allaqachon mavjud.'],
    #     'status': ['Noto\'g\'ri holat tanlanmoqda.']
    # }

# Cleaned data'ni olish
if form.is_valid():
    cleaned_name = form.cleaned_data['name']
    cleaned_status = form.cleaned_data['status']
```

---

## 5. STATUS CHOICES

```python
from apps.casting.models import Stanok

# Barcha status variantları
print(Stanok.Status.choices)
# [('active', 'Faol'), ('repair', "Ta'mirda"), ('inactive', 'Faol emas')]

# Raqamli qiymatlar
print(Stanok.Status.ACTIVE)      # 'active'
print(Stanok.Status.REPAIR)      # 'repair'
print(Stanok.Status.INACTIVE)    # 'inactive'

# Display value
stanok = Stanok.objects.first()
print(stanok.get_status_display())  # "Faol" yoki "Ta'mirda" yoki "Faol emas"

# Filter by status constant
active_stanoklar = Stanok.objects.filter(status=Stanok.Status.ACTIVE)
```

---

## 6. ADVANCED QUERIES

### Kompleks Filtrlash

```python
from django.db.models import Q

# OR logic
stanoklar = Stanok.objects.filter(
    Q(status=Stanok.Status.ACTIVE) | Q(status=Stanok.Status.REPAIR)
)

# AND + OR kombinatsiyasi
stanoklar = Stanok.objects.filter(
    (Q(status=Stanok.Status.ACTIVE) | Q(status=Stanok.Status.REPAIR))
    & Q(name__icontains="CNC")
)

# NOT logic
stanoklar = Stanok.objects.exclude(status=Stanok.Status.INACTIVE)
```

### Queryset Aggregation

```python
from django.db.models import Count

# Status bo'yicha group
status_groups = Stanok.objects.values('status').annotate(count=Count('id'))
# [{status: 'active', count: 5}, ...]

# Dictionary o'tish
status_dict = {
    'active': Stanok.objects.filter(status=Stanok.Status.ACTIVE).count(),
    'repair': Stanok.objects.filter(status=Stanok.Status.REPAIR).count(),
    'inactive': Stanok.objects.filter(status=Stanok.Status.INACTIVE).count(),
}
```

---

## 7. SIGNAL'LAR (Optional)

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.casting.models import Stanok

@receiver(post_save, sender=Stanok)
def stanok_created_or_updated(sender, instance, created, **kwargs):
    if created:
        print(f"✅ Yangi stanok yaratildi: {instance.name}")
    else:
        print(f"📝 Stanok yangilandi: {instance.name}")

@receiver(post_delete, sender=Stanok)
def stanok_deleted(sender, instance, **kwargs):
    print(f"🗑️ Stanok o'chirildi: {instance.name}")
```

---

## 8. ADMIN PANEL

```python
from django.contrib import admin
from apps.casting.models import Stanok

@admin.register(Stanok)
class StanokAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('name', 'status')
        }),
    )
```

---

## 9. EXPORT TO CSV (Django Admin Extension)

```python
from django.contrib import admin
from django.http import HttpResponse
import csv

def export_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stanoklar.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Nomi', 'Holat'])
    
    for stanok in queryset:
        writer.writerow([
            stanok.id,
            stanok.name,
            stanok.get_status_display()
        ])
    
    return response

export_to_csv.short_description = "CSV ga eksport qilish"

class StanokAdmin(admin.ModelAdmin):
    actions = [export_to_csv]
```

---

## 10. JSON API (DRF - Optional)

```python
# serializers.py
from rest_framework import serializers
from apps.casting.models import Stanok

class StanokSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display')
    
    class Meta:
        model = Stanok
        fields = ['id', 'name', 'status', 'status_display']

# views.py (APIView)
from rest_framework import status as rest_status
from rest_framework.response import Response
from rest_framework.views import APIView

class StanokListAPIView(APIView):
    def get(self, request):
        stanoklar = Stanok.objects.all()
        serializer = StanokSerializer(stanoklar, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = StanokSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=rest_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=rest_status.HTTP_400_BAD_REQUEST)
```

---

**Tahrirlandi:** 2026-04-24  
**Versiya:** 1.0  
**Til:** Uzbek (O'zbek)
