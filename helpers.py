# credit_tracker/models.py
from django.db import models
from django.conf import settings

class CreditPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.date}"

class CreditUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.date}"

class CreditBalance(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - Balance: {self.balance}"

# credit_tracker/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from .models import CreditPurchase, CreditUsage, CreditBalance
from decimal import Decimal

@login_required
def credit_summary(request):
    purchases = CreditPurchase.objects.filter(user=request.user)
    usages = CreditUsage.objects.filter(user=request.user)
    balance, created = CreditBalance.objects.get_or_create(user=request.user)
    
    context = {
        'total_purchased': sum(purchase.amount for purchase in purchases),
        'total_used': sum(usage.amount for usage in usages),
        'current_balance': balance.balance,
        'recent_purchases': purchases.order_by('-date')[:5],
        'recent_usages': usages.order_by('-date')[:5],
    }
    return render(request, 'credit_tracker/summary.html', context)

@login_required
@transaction.atomic
def use_credit(request, amount):
    amount = Decimal(amount)
    balance, created = CreditBalance.objects.get_or_create(user=request.user)
    
    if balance.balance >= amount:
        balance.balance -= amount
        balance.save()
        CreditUsage.objects.create(user=request.user, amount=amount, description="Credit usage")
        messages.success(request, f"Successfully used {amount} credits.")
        return redirect(reverse('credit_tracker:summary'))
    else:
        messages.warning(request, "Insufficient credits. Please purchase more.")
        return redirect(reverse('credit_tracker:purchase'))

@login_required
@transaction.atomic
def purchase_credit(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        # Here you would typically integrate with a payment gateway
        # For this example, we'll just add the credits directly
        CreditPurchase.objects.create(user=request.user, amount=amount)
        balance, created = CreditBalance.objects.get_or_create(user=request.user)
        balance.balance += amount
        balance.save()
        messages.success(request, f"Successfully purchased {amount} credits.")
        return redirect(reverse('credit_tracker:summary'))
    return render(request, 'credit_tracker/purchase.html')

# credit_tracker/admin.py
from django.contrib import admin
from .models import CreditPurchase, CreditUsage, CreditBalance

admin.site.register(CreditPurchase)
admin.site.register(CreditUsage)
admin.site.register(CreditBalance)

# credit_tracker/urls.py
from django.urls import path
from . import views

app_name = 'credit_tracker'

urlpatterns = [
    path('summary/', views.credit_summary, name='summary'),
    path('use/<str:amount>/', views.use_credit, name='use'),
    path('purchase/', views.purchase_credit, name='purchase'),
]

# templates/credit_tracker/summary.html
{% extends "base.html" %}

{% block content %}
<h1>Credit Summary</h1>
<p>Total Purchased: {{ total_purchased }}</p>
<p>Total Used: {{ total_used }}</p>
<p>Current Balance: {{ current_balance }}</p>

<h2>Recent Purchases</h2>
<ul>
{% for purchase in recent_purchases %}
    <li>{{ purchase.amount }} - {{ purchase.date }}</li>
{% endfor %}
</ul>

<h2>Recent Usages</h2>
<ul>
{% for usage in recent_usages %}
    <li>{{ usage.amount }} - {{ usage.date }} - {{ usage.description }}</li>
{% endfor %}
</ul>

<a href="{% url 'credit_tracker:purchase' %}">Purchase Credits</a>
{% endblock %}

# templates/credit_tracker/purchase.html
{% extends "base.html" %}

{% block content %}
<h1>Purchase Credits</h1>
<form method="post">
    {% csrf_token %}
    <label for="amount">Amount:</label>
    <input type="number" name="amount" id="amount" step="0.01" min="0" required>
    <button type="submit">Purchase</button>
</form>
<a href="{% url 'credit_tracker:summary' %}">Back to Summary</a>
{% endblock %}
