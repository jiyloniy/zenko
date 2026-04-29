# Tosh App - Qabul Jarayonlari Xatosini Tuzatish

**Xato:** `NoReverseMatch at /tosh/stats/ - Reverse for 'qabul_list' not found`

**Sabab:** [base.html](apps/tosh/templates/tosh/base.html) shablonida `{% url 'tosh:qabul_list' %}` chaqirildi, lekin bu URL pattern va view mavjud emas edi.

---

## 📋 Yaratilgan Komponentlar

### 1. Views ([views.py](apps/tosh/views.py))

#### QabulJarayonListView
```python
- Avtomatik QabulJarayon yaratish (tosh_qadaldi holati uchun)
- Tab filterlash: kutilmoqda, ilinmoqda, ilib_bolindi, bekor_qilindi
- Search: buyurtma nomi va raqami bo'yicha
- Context: jarayonlar, counts, tab, q
```

#### QabulJarayonDetailView
```python
- Qabul jarayonining barcha ma'lumotlarini ko'rsatish
- Order, tosh jarayon, va qabul holati ro'yxati
- Qabul holatini o'zgartirish formasini ko'rsatish
```

#### QabulJarayonSetStatusView
```python
- POST endpoint holat o'zgartirishni boshqarish
- Status: kutilmoqda → ilinmoqda → ilib_bolindi yoki bekor_qilindi
- Izoh yozish imkonyati
```

### 2. URLs ([urls.py](apps/tosh/urls.py))

```python
path('qabul/', views.QabulJarayonListView.as_view(), name='qabul_list'),
path('qabul/<int:pk>/', views.QabulJarayonDetailView.as_view(), name='qabul_detail'),
path('qabul/<int:pk>/set-status/', views.QabulJarayonSetStatusView.as_view(), name='qabul_set_status'),
```

### 3. Templates

#### [qabul_list.html](apps/tosh/templates/tosh/qabul_list.html)
- Card grid layout buyurtmalar uchun
- 4 ta tab: Kutilmoqda, Ilinmoqda, Ilib bo'lindi, Bekor qilindi
- Search/filter bar
- Status inline actions

#### [qabul_detail.html](apps/tosh/templates/tosh/qabul_detail.html)
- Buyurtma ma'lumotlari (nomi, raqami, miqdori, termin, brujka)
- Tosh qadash jarayoni holati
- Qabul holati o'zgartirishni boshqarish

---

## 🔗 Model Bog'lanishlari

```
QabulJarayon (OneToOne) ← ToshQadashJarayon ← Order
                         ↓
                    ToshQadashLog (hodim, tosh par-lar)
```

**QabulJarayon Status:**
- `kutilmoqda` (gray) - Kutilmoqda
- `ilinmoqda` (orange) - Ilinmoqda  
- `ilib_bolindi` (green) - Ilib bo'lindi
- `bekor_qilindi` (red) - Bekor qilindi

---

## 📊 Chiziq Bo'yicha Jarayoni

```
1. Buyurtma yaratiladi (Order status: IN_PROCESS)
                ↓
2. Quyish tugallandi (QuyishJarayon.QUYIB_BOLINDI)
                ↓
3. Tosh qadash boshlanadi (ToshQadashJarayon yaratiladi)
                ↓
4. Hodimlar tosh qadashlari (ToshQadashLog yozuvlari)
                ↓
5. Tosh qadash tugallandi (ToshQadashJarayon.TOSH_QADALDI)
                ↓
6. **Qabul jarayoni yaratiladi (QabulJarayon yaratiladi)** ← AUTO
                ↓
7. Qabul holati o'zgartiriladi (kutilmoqda → ilinmoqda → ilib_bolindi)
                ↓
8. Buyurtma tugatiladi (Order status: READY)
```

---

## 🎨 UI Xususiyatlari

| Sahifa | Xususiyat |
|--------|-----------|
| qabul_list.html | Tab-based filtering, card grid, inline status buttons |
| qabul_detail.html | Two-column layout, read-only order info, status form |
| base.html | Navigation link: "Qabul qilish" |

---

## ✅ Tuzatilgan Xatoliklar

| Xato | Sabab | Tuzatish |
|-----|-------|----------|
| NoReverseMatch: qabul_list | URL pattern yo'q | ✅ URL va view yaratildi |
| URL mismatches in template | Loop variable `j` butun joyda | ✅ `qabul` ga o'zgartirildi |
| Template context errors | Incorrect object references | ✅ Correct references added |

---

## 📝 Fayllar O'zgartirilgan

1. ✅ [apps/tosh/views.py](apps/tosh/views.py) - 3 ta yangi view
2. ✅ [apps/tosh/urls.py](apps/tosh/urls.py) - 3 ta yangi URL pattern
3. ✅ [apps/tosh/templates/tosh/qabul_list.html](apps/tosh/templates/tosh/qabul_list.html) - Loop var fix
4. ✅ [apps/tosh/templates/tosh/qabul_detail.html](apps/tosh/templates/tosh/qabul_detail.html) - Yangi template

---

## 🚀 Natija

✨ **NoReverseMatch xatosi to'liq tuzatildi!**

```
BEFORE: NoReverseMatch at /tosh/stats/
        Reverse for 'qabul_list' not found
        
AFTER:  ✓ /tosh/qabul/ - Qabul jarayonlari ro'yhati
        ✓ /tosh/qabul/<id>/ - Detail sahifasi
        ✓ /tosh/qabul/<id>/set-status/ - Holat o'zgartirishı
```

Qabul jarayonlari to'liq tuzatildi, test qilishga tayyor! 🎉

---

*Samarali tahlil va tuzatish yakunlandi.*
