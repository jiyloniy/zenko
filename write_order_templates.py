import os

BASE = 'apps/order/templates/order'

# ── ORDER LIST ────────────────────────────────────────────────────────────────
order_list = """{% extends "ceo/base.html" %}
{% block title %}Buyurtmalar — Zenko{% endblock %}
{% block page_title %}Buyurtmalar{% endblock %}

{% block topbar_actions %}
<a href="{% url 'order:order_create' %}" class="btn btn-primary">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>
    Yangi buyurtma
</a>
{% endblock %}

{% block extra_css %}
<style>
.filter-wrap{background:var(--white);border:1px solid var(--gray-200);border-radius:14px;padding:16px 20px;margin-bottom:24px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.filter-wrap input[type=text],.filter-wrap select{padding:8px 13px;border:1.5px solid var(--gray-200);border-radius:9px;font-size:13px;background:var(--white);color:var(--black);min-width:150px;transition:border-color .18s;}
.filter-wrap input:focus,.filter-wrap select:focus{outline:none;border-color:var(--orange);}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px;}
.stat-tile{background:var(--white);border:1px solid var(--gray-200);border-radius:14px;padding:18px 20px;display:flex;align-items:center;gap:14px;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:box-shadow .2s,transform .18s;}
.stat-tile:hover{box-shadow:0 4px 16px rgba(0,0,0,.07);transform:translateY(-2px);}
.stat-tile .si{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.stat-tile .si svg{width:21px;height:21px;}
.si-all{background:#F1F5F9;color:#475569;}
.si-new{background:#EFF6FF;color:#2563EB;}
.si-proc{background:#FFF7ED;color:#EA580C;}
.si-done{background:#F0FDF4;color:#16A34A;}
.stat-tile .sv{font-size:24px;font-weight:800;color:var(--black);line-height:1;}
.stat-tile .sl{font-size:12px;color:var(--gray-500);font-weight:500;margin-top:2px;}
.order-table-wrap{background:var(--white);border:1px solid var(--gray-200);border-radius:16px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.order-table{width:100%;border-collapse:collapse;font-size:13.5px;}
.order-table th{text-align:left;padding:11px 16px;font-weight:700;color:var(--gray-500);font-size:11px;text-transform:uppercase;letter-spacing:.6px;border-bottom:2px solid var(--gray-200);background:var(--gray-50);white-space:nowrap;}
.order-table td{padding:14px 16px;border-bottom:1px solid var(--gray-100);vertical-align:middle;color:var(--gray-700);}
.order-table tbody tr:hover td{background:#FAFAFA;}
.order-table tbody tr:last-child td{border-bottom:none;}
.order-thumb{width:46px;height:46px;border-radius:10px;object-fit:cover;border:1px solid var(--gray-200);}
.order-thumb-ph{width:46px;height:46px;border-radius:10px;background:var(--gray-100);display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.order-thumb-ph svg{width:20px;height:20px;color:var(--gray-300);}
.order-name-link{text-decoration:none;}
.order-name{font-weight:700;color:var(--black);font-size:14px;}
.order-num{font-size:11px;color:var(--gray-400);margin-top:2px;font-family:monospace;}
.spill{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;font-size:11.5px;font-weight:700;}
.spill .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
.sp-new{background:#EFF6FF;color:#1D4ED8;}        .sp-new .dot{background:#3B82F6;}
.sp-accepted{background:#F0FDF4;color:#15803D;}   .sp-accepted .dot{background:#22C55E;}
.sp-in_process{background:#FFF7ED;color:#C2410C;} .sp-in_process .dot{background:#F97316;animation:blink 2s infinite;}
.sp-ready{background:#F0FDF4;color:#166534;}      .sp-ready .dot{background:#16A34A;}
.sp-delivered{background:var(--gray-100);color:var(--gray-500);} .sp-delivered .dot{background:var(--gray-300);}
.sp-cancelled{background:#FEF2F2;color:#B91C1C;}  .sp-cancelled .dot{background:#EF4444;}
.stage-tag{display:inline-block;padding:3px 9px;border-radius:6px;font-size:11px;font-weight:600;background:var(--orange-light);color:var(--orange);}
.deadline-late{color:#DC2626;font-weight:700;}
.overdue-tag{font-size:10px;color:#DC2626;font-weight:600;margin-top:2px;}
.actions-cell{display:flex;gap:5px;align-items:center;justify-content:flex-end;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.35;}}
.empty-wrap{padding:70px 20px;text-align:center;color:var(--gray-400);}
.empty-wrap svg{width:56px;height:56px;margin-bottom:16px;opacity:.28;}
.empty-wrap p{font-size:15px;margin-bottom:20px;}
.pagination{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:28px;}
.page-btn{padding:7px 13px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;background:var(--white);border:1px solid var(--gray-200);color:var(--gray-700);transition:all .18s;}
.page-btn:hover{background:var(--gray-100);}
.page-btn.active{background:var(--orange);color:#fff;border-color:var(--orange);}
@media(max-width:768px){.order-table th:nth-child(5),.order-table td:nth-child(5){display:none;}}
@media(max-width:580px){.order-table th:nth-child(4),.order-table td:nth-child(4),.order-table th:nth-child(6),.order-table td:nth-child(6){display:none;}.filter-wrap{flex-direction:column;align-items:stretch;}.filter-wrap input,.filter-wrap select{min-width:0;}}
</style>
{% endblock %}

{% block content %}
<div class="stats-row">
    <div class="stat-tile">
        <div class="si si-all"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/></svg></div>
        <div><div class="sv">{{ total }}</div><div class="sl">Jami buyurtmalar</div></div>
    </div>
    <div class="stat-tile">
        <div class="si si-new"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
        <div><div class="sv">{{ new_count }}</div><div class="sl">Yangi</div></div>
    </div>
    <div class="stat-tile">
        <div class="si si-proc"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"/></svg></div>
        <div><div class="sv">{{ in_process_count }}</div><div class="sl">Jarayonda</div></div>
    </div>
    <div class="stat-tile">
        <div class="si si-done"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
        <div><div class="sv">{{ ready_count }}</div><div class="sl">Tayyor</div></div>
    </div>
</div>

<form class="filter-wrap" method="get">
    <input type="text" name="q" value="{{ q }}" placeholder="Qidirish (nomi, raqami)...">
    <select name="status" onchange="this.form.submit()">
        <option value="">Barcha statuslar</option>
        {% for val,label in statuses %}<option value="{{ val }}" {% if val == current_status %}selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <select name="stage" onchange="this.form.submit()">
        <option value="">Barcha bosqichlar</option>
        {% for val,label in stages %}<option value="{{ val }}" {% if val == current_stage %}selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <button type="submit" class="btn btn-secondary btn-sm">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:14px;height:14px"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/></svg>
        Qidirish
    </button>
    {% if q or current_status or current_stage %}
    <a href="{% url 'order:order_list' %}" class="btn btn-sm" style="background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:13px;height:13px"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
        Tozalash
    </a>
    {% endif %}
</form>

{% if orders %}
<div class="order-table-wrap">
    <table class="order-table">
        <thead>
            <tr>
                <th style="width:54px;"></th>
                <th>Buyurtma</th>
                <th>Miqdor</th>
                <th>Muddat</th>
                <th>Bosqich</th>
                <th>Status</th>
                <th style="text-align:right;padding-right:20px;">Amallar</th>
            </tr>
        </thead>
        <tbody>
        {% for order in orders %}
        <tr>
            <td>
                {% if order.image %}
                <img src="{{ order.image.url }}" class="order-thumb" alt="">
                {% else %}
                <div class="order-thumb-ph"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"/></svg></div>
                {% endif %}
            </td>
            <td>
                <a href="{% url 'order:order_detail' order.pk %}" class="order-name-link">
                    <div class="order-name">{{ order.name }}</div>
                    <div class="order-num">{{ order.order_number }}</div>
                </a>
            </td>
            <td><strong>{{ order.quantity }}</strong> <span style="color:var(--gray-400);font-size:12px;">dona</span></td>
            <td>
                <span class="{% if order.is_overdue %}deadline-late{% endif %}">{{ order.deadline|date:"d.m.Y" }}</span>
                {% if order.is_overdue %}<div class="overdue-tag">Muddati o'tdi</div>{% endif %}
            </td>
            <td>
                {% if order.current_stage %}<span class="stage-tag">{{ order.get_current_stage_display }}</span>
                {% else %}<span style="color:var(--gray-300);">—</span>{% endif %}
            </td>
            <td>
                <span class="spill sp-{{ order.status }}"><span class="dot"></span>{{ order.get_status_display }}</span>
            </td>
            <td>
                <div class="actions-cell">
                    <a href="{% url 'order:order_detail' order.pk %}" class="btn btn-secondary btn-sm" title="Ko'rish">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:13px;height:13px"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    </a>
                    <a href="{% url 'order:order_edit' order.pk %}" class="btn btn-sm" style="background:var(--orange-light);color:var(--orange);" title="Tahrirlash">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:13px;height:13px"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z"/></svg>
                    </a>
                    <a href="{% url 'order:order_delete' order.pk %}" class="btn btn-sm" style="background:#FEF2F2;color:#EF4444;" title="O'chirish">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:13px;height:13px"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>
                    </a>
                </div>
            </td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</div>

{% if is_paginated %}
<div class="pagination">
    {% if page_obj.has_previous %}
    <a href="?page={{ page_obj.previous_page_number }}&status={{ current_status }}&stage={{ current_stage }}&q={{ q }}" class="page-btn">&laquo; Oldingi</a>
    {% endif %}
    <span class="page-btn active">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
    {% if page_obj.has_next %}
    <a href="?page={{ page_obj.next_page_number }}&status={{ current_status }}&stage={{ current_stage }}&q={{ q }}" class="page-btn">Keyingi &raquo;</a>
    {% endif %}
</div>
{% endif %}

{% else %}
<div class="empty-wrap">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/></svg>
    <p>{% if q or current_status or current_stage %}Filtr bo'yicha buyurtma topilmadi{% else %}Hali buyurtmalar yo'q{% endif %}</p>
    {% if not q and not current_status and not current_stage %}
    <a href="{% url 'order:order_create' %}" class="btn btn-primary">Birinchi buyurtmani yarating</a>
    {% else %}
    <a href="{% url 'order:order_list' %}" class="btn btn-secondary">Filterni tozalash</a>
    {% endif %}
</div>
{% endif %}
{% endblock %}"""

# ── ORDER FORM ────────────────────────────────────────────────────────────────
order_form = """{% extends "ceo/base.html" %}
{% block title %}{{ title }} — Zenko{% endblock %}
{% block page_title %}{{ title }}{% endblock %}

{% block topbar_actions %}
<a href="{% url 'order:order_list' %}" class="btn btn-secondary btn-sm">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:15px;height:15px"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"/></svg>
    Ro'yxatga qaytish
</a>
{% endblock %}

{% block extra_css %}
<style>
.form-layout{display:grid;grid-template-columns:1fr 380px;gap:24px;align-items:start;}
.form-card{background:var(--white);border:1px solid var(--gray-200);border-radius:16px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.form-card-head{background:var(--black);padding:20px 24px;display:flex;align-items:center;gap:12px;}
.form-card-head .hico{width:40px;height:40px;background:var(--orange);border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.form-card-head .hico svg{width:20px;height:20px;color:#fff;}
.form-card-head h2{font-size:16px;font-weight:700;color:#fff;}
.form-card-head p{font-size:12px;color:rgba(255,255,255,.5);margin-top:2px;}
.form-card-body{padding:24px;}
.section-sep{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--orange);margin-bottom:12px;margin-top:4px;display:flex;align-items:center;gap:8px;}
.section-sep::after{content:'';flex:1;height:1px;background:var(--gray-200);}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.f-group{margin-bottom:16px;}
.f-label{display:block;font-size:12.5px;font-weight:600;color:var(--gray-700);margin-bottom:5px;}
.f-required{color:var(--red);margin-left:2px;}
.f-input{width:100%;padding:9px 13px;border:1.5px solid var(--gray-200);border-radius:9px;font-size:13.5px;color:var(--black);background:var(--white);transition:border-color .18s,box-shadow .18s;}
.f-input:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(245,130,32,.1);}
.f-hint{font-size:11.5px;color:var(--gray-400);margin-top:4px;}
.form-actions{display:flex;gap:10px;padding-top:16px;border-top:1px solid var(--gray-200);margin-top:4px;}

/* Image upload */
.img-upload-zone{border:2px dashed var(--gray-200);border-radius:12px;padding:24px;text-align:center;cursor:pointer;transition:border-color .18s,background .18s;position:relative;}
.img-upload-zone:hover{border-color:var(--orange);background:var(--orange-light);}
.img-upload-zone input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
.img-upload-zone svg{width:36px;height:36px;color:var(--gray-300);margin-bottom:8px;}
.img-upload-zone p{font-size:13px;color:var(--gray-500);font-weight:500;}
.img-upload-zone small{font-size:11px;color:var(--gray-400);}
.img-preview-wrap{position:relative;display:inline-block;}
.img-preview-wrap img{max-width:100%;border-radius:10px;border:1px solid var(--gray-200);display:block;}
.img-clear-btn{position:absolute;top:6px;right:6px;width:26px;height:26px;background:#EF4444;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;border:none;}
.img-clear-btn svg{width:12px;height:12px;color:#fff;}

/* Side info card */
.info-card{background:var(--white);border:1px solid var(--gray-200);border-radius:16px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.info-card-head{background:var(--gray-50);padding:14px 18px;border-bottom:1px solid var(--gray-200);}
.info-card-head h4{font-size:13px;font-weight:700;color:var(--black);}
.info-card-body{padding:16px 18px;}
.info-tip{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--gray-100);font-size:12.5px;color:var(--gray-600);}
.info-tip:last-child{border-bottom:none;}
.info-tip svg{width:15px;height:15px;color:var(--orange);flex-shrink:0;margin-top:1px;}

@media(max-width:900px){.form-layout{grid-template-columns:1fr;}.two-col{grid-template-columns:1fr;}}
</style>
{% endblock %}

{% block content %}
<div class="form-layout">
    <div>
        <div class="form-card">
            <div class="form-card-head">
                <div class="hico">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/></svg>
                </div>
                <div>
                    <h2>{{ title }}</h2>
                    <p>Buyurtma ma'lumotlarini to'ldiring</p>
                </div>
            </div>
            <div class="form-card-body">
                {% if form.errors %}
                <div class="form-errors" style="margin-bottom:18px;">
                    <strong>Xatoliklar:</strong>
                    <ul style="margin:4px 0 0 16px;">
                    {% for field in form %}{% for error in field.errors %}<li>{{ field.label }}: {{ error }}</li>{% endfor %}{% endfor %}
                    {% for error in form.non_field_errors %}<li>{{ error }}</li>{% endfor %}
                    </ul>
                </div>
                {% endif %}

                <form method="post" enctype="multipart/form-data" id="orderForm">
                    {% csrf_token %}

                    <div class="section-sep">Asosiy ma'lumotlar</div>

                    <div class="f-group">
                        <label class="f-label">Buyurtma nomi <span class="f-required">*</span></label>
                        <input type="text" name="name" class="f-input" value="{{ form.name.value|default:'' }}" required placeholder="Masalan: Oltin uzuk 585...">
                    </div>

                    <div class="two-col">
                        <div class="f-group">
                            <label class="f-label">Miqdori <span class="f-required">*</span></label>
                            <input type="number" name="quantity" class="f-input" value="{{ form.quantity.value|default:'' }}" min="1" required placeholder="100">
                            <div class="f-hint">Nechta dona</div>
                        </div>
                        <div class="f-group">
                            <label class="f-label">Tayyor bo'lish sanasi <span class="f-required">*</span></label>
                            <input type="date" name="deadline" class="f-input" value="{{ form.deadline.value|default:'' }}" required>
                        </div>
                    </div>

                    <div class="section-sep">Holat va bosqich</div>

                    <div class="two-col">
                        <div class="f-group">
                            <label class="f-label">Status</label>
                            <select name="status" class="f-input">
                                {% for val,label in form.fields.status.choices %}
                                <option value="{{ val }}" {% if form.status.value == val %}selected{% endif %}>{{ label }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="f-group">
                            <label class="f-label">Joriy bosqich</label>
                            <select name="current_stage" class="f-input">
                                <option value="">— Tanlanmagan —</option>
                                {% for val,label in form.fields.current_stage.choices %}{% if val %}
                                <option value="{{ val }}" {% if form.current_stage.value == val %}selected{% endif %}>{{ label }}</option>
                                {% endif %}{% endfor %}
                            </select>
                        </div>
                    </div>

                    <div class="section-sep">Rasm va izoh</div>

                    <div class="f-group">
                        <label class="f-label">Mahsulot rasmi</label>
                        {% if order and order.image %}
                        <div class="img-preview-wrap" id="previewWrap">
                            <img src="{{ order.image.url }}" alt="{{ order.name }}" id="previewImg">
                            <button type="button" class="img-clear-btn" onclick="clearImage()">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
                            </button>
                        </div>
                        <input type="file" name="image" id="imageInput" accept="image/*" style="display:none;" onchange="previewImage(event)">
                        <button type="button" onclick="document.getElementById('imageInput').click()" class="btn btn-secondary btn-sm" style="margin-top:8px;">Rasmni almashtirish</button>
                        {% else %}
                        <div class="img-upload-zone" id="uploadZone">
                            <input type="file" name="image" id="imageInput" accept="image/*" onchange="previewImage(event)">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"/></svg>
                            <p>Rasm yuklash uchun bosing yoki tortib tashlang</p>
                            <small>PNG, JPG, WEBP — max 5MB</small>
                        </div>
                        <div id="previewWrap" style="display:none;margin-top:10px;">
                            <div class="img-preview-wrap">
                                <img id="previewImg" src="" alt="" style="max-height:200px;">
                                <button type="button" class="img-clear-btn" onclick="clearImage()">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
                                </button>
                            </div>
                        </div>
                        {% endif %}
                    </div>

                    <div class="f-group">
                        <label class="f-label">Izoh</label>
                        <textarea name="note" class="f-input" rows="3" placeholder="Qo'shimcha ma'lumotlar...">{{ form.note.value|default:'' }}</textarea>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></svg>
                            Saqlash
                        </button>
                        {% if order %}
                        <a href="{% url 'order:order_detail' order.pk %}" class="btn btn-secondary">Bekor qilish</a>
                        {% else %}
                        <a href="{% url 'order:order_list' %}" class="btn btn-secondary">Bekor qilish</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Right side info -->
    <div>
        <div class="info-card">
            <div class="info-card-head"><h4>Yordam</h4></div>
            <div class="info-card-body">
                <div class="info-tip">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/></svg>
                    Buyurtma raqami avtomatik tarzda beriladi.
                </div>
                <div class="info-tip">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0 1 12 21 8.25 8.25 0 0 1 6.038 7.047 8.287 8.287 0 0 0 9 9.601a8.983 8.983 0 0 1 3.361-6.867 8.21 8.21 0 0 0 3 2.48Z"/></svg>
                    Yangi buyurtma yaratilganda barcha bosqichlar (Quyish, Montaj, Ilish...) avtomatik yaratiladi.
                </div>
                <div class="info-tip">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"/></svg>
                    Muddat o'tib ketsa buyurtma "muddati o'tgan" deb belgilanadi.
                </div>
                <div class="info-tip">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"/></svg>
                    Rasm PNG, JPG yoki WEBP formatida bo'lishi kerak.
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function previewImage(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        const wrap = document.getElementById('previewWrap');
        const img = document.getElementById('previewImg');
        const zone = document.getElementById('uploadZone');
        img.src = e.target.result;
        if (wrap) wrap.style.display = 'block';
        if (zone) zone.style.display = 'none';
    };
    reader.readAsDataURL(file);
}
function clearImage() {
    const input = document.getElementById('imageInput');
    const wrap = document.getElementById('previewWrap');
    const zone = document.getElementById('uploadZone');
    if (input) input.value = '';
    if (wrap) wrap.style.display = 'none';
    if (zone) zone.style.display = 'block';
}
</script>
{% endblock %}"""

# ── ORDER DELETE ──────────────────────────────────────────────────────────────
order_delete = """{% extends "ceo/base.html" %}
{% block title %}Buyurtmani o'chirish{% endblock %}
{% block page_title %}O'chirishni tasdiqlash{% endblock %}

{% block content %}
<div style="max-width:480px;margin:40px auto;">
    <div style="background:var(--white);border-radius:16px;border:1px solid var(--gray-200);overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <div style="background:#FEF2F2;padding:28px;text-align:center;border-bottom:1px solid #FECACA;">
            <div style="width:56px;height:56px;background:#EF4444;border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="white" style="width:28px;height:28px"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>
            </div>
            <h2 style="font-size:18px;font-weight:800;color:#991B1B;margin-bottom:8px;">Buyurtmani o'chirish</h2>
            <p style="font-size:14px;color:#B91C1C;margin:0;">Bu amal qaytarib bo'lmaydi</p>
        </div>
        <div style="padding:24px;">
            <div style="background:var(--gray-50);border-radius:10px;padding:14px 16px;margin-bottom:20px;border:1px solid var(--gray-200);">
                <div style="font-size:12px;color:var(--gray-500);font-weight:500;margin-bottom:4px;">O'chiriladigan buyurtma</div>
                <div style="font-size:16px;font-weight:800;color:var(--black);">{{ object.name }}</div>
                <div style="font-size:12px;color:var(--gray-400);font-family:monospace;margin-top:2px;">{{ object.order_number }} · {{ object.quantity }} dona</div>
            </div>
            <p style="font-size:13.5px;color:var(--gray-600);line-height:1.6;margin-bottom:22px;">
                <strong>{{ object.name }}</strong> buyurtmasi va unga bog'liq barcha bosqich ma'lumotlari, loglar hamda sifat tekshiruvi natijalari butunlay o'chiriladi.
            </p>
            <form method="post" style="display:flex;gap:10px;">
                {% csrf_token %}
                <button type="submit" class="btn btn-danger" style="flex:1;justify-content:center;">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:16px;height:16px"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>
                    Ha, o'chirish
                </button>
                <a href="{% url 'order:order_list' %}" class="btn btn-secondary" style="flex:1;justify-content:center;">Bekor qilish</a>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""

files = {
    'order_list.html': order_list,
    'order_form.html': order_form,
    'order_confirm_delete.html': order_delete,
}

for fname, content in files.items():
    path = os.path.join(BASE, fname)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'OK: {fname}')

print('Tayyor!')
