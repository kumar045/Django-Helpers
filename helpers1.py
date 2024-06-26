# credit_system/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

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
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.date}"

class CreditBalance(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - Balance: {self.balance}"

# credit_system/utils.py
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
from .models import CreditBalance, CreditUsage

def check_credit_balance(user, amount):
    balance, _ = CreditBalance.objects.get_or_create(user=user)
    return balance.balance >= amount

@transaction.atomic
def use_credits(user, amount, description, content_object):
    if check_credit_balance(user, amount):
        balance = CreditBalance.objects.get(user=user)
        balance.balance -= amount
        balance.save()

        CreditUsage.objects.create(
            user=user,
            amount=amount,
            description=description,
            content_object=content_object
        )
        return True
    return False

# credit_system/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from .models import CreditPurchase, CreditUsage, CreditBalance
from decimal import Decimal

CREDIT_PURCHASE_AMOUNT = Decimal('50.00')

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
    return render(request, 'credit_system/summary.html', context)

@login_required
@transaction.atomic
def purchase_credit(request):
    balance, created = CreditBalance.objects.get_or_create(user=request.user)
    balance.balance += CREDIT_PURCHASE_AMOUNT
    balance.save()
    
    CreditPurchase.objects.create(user=request.user, amount=CREDIT_PURCHASE_AMOUNT)
    
    messages.success(request, f"Successfully purchased {CREDIT_PURCHASE_AMOUNT} credits.")
    return redirect(reverse('credit_system:summary'))

# credit_system/urls.py
from django.urls import path
from . import views

app_name = 'credit_system'

urlpatterns = [
    path('summary/', views.credit_summary, name='summary'),
    path('purchase/', views.purchase_credit, name='purchase'),
]

# templates/credit_system/summary.html
{% extends "base.html" %}

{% block content %}
<h1>Credit Summary</h1>
<p>Total Purchased: ${{ total_purchased }}</p>
<p>Total Used: ${{ total_used }}</p>
<p>Current Balance: ${{ current_balance }}</p>

<h2>Recent Purchases</h2>
<ul>
{% for purchase in recent_purchases %}
    <li>${{ purchase.amount }} - {{ purchase.date }}</li>
{% endfor %}
</ul>

<h2>Recent Usages</h2>
<ul>
{% for usage in recent_usages %}
    <li>${{ usage.amount }} - {{ usage.date }} - {{ usage.description }}</li>
{% endfor %}
</ul>

<a href="{% url 'credit_system:purchase' %}">Purchase $50 Credits</a>
{% endblock %}

# Example usage in another app (e.g., blog_app/views.py)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from credit_system.utils import use_credits
from .models import BlogPost

@login_required
def create_blog_post(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        word_count = len(content.split())
        credits_needed = Decimal(word_count / 300).quantize(Decimal('1.'), rounding='ROUND_UP')
        
        blog_post = BlogPost(user=request.user, title=title, content=content)
        
        if use_credits(request.user, credits_needed, f"Create blog post: {title}", blog_post):
            blog_post.save()
            messages.success(request, f"Blog post created successfully. Used {credits_needed} credits.")
            return redirect(reverse('blog:post_list'))
        else:
            messages.warning(request, f"Insufficient credits. You need {credits_needed} credits to create this blog post.")
    
    return render(request, 'blog/create_blog_post.html')
