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

class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_boosted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"

# credit_tracker/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from .models import CreditPurchase, CreditUsage, CreditBalance, Post
from decimal import Decimal

CREDIT_PURCHASE_AMOUNT = Decimal('50.00')
BOOST_COST = Decimal('1.00')

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
def purchase_credit(request):
    balance, created = CreditBalance.objects.get_or_create(user=request.user)
    balance.balance += CREDIT_PURCHASE_AMOUNT
    balance.save()
    
    CreditPurchase.objects.create(user=request.user, amount=CREDIT_PURCHASE_AMOUNT)
    
    messages.success(request, f"Successfully purchased {CREDIT_PURCHASE_AMOUNT} credits.")
    return redirect(reverse('credit_tracker:summary'))

@login_required
@transaction.atomic
def boost_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    balance, created = CreditBalance.objects.get_or_create(user=request.user)
    
    if balance.balance >= BOOST_COST:
        balance.balance -= BOOST_COST
        balance.save()
        
        post.is_boosted = True
        post.save()
        
        CreditUsage.objects.create(user=request.user, amount=BOOST_COST, description=f"Boost post (ID: {post.id})")
        
        messages.success(request, f"Successfully boosted post for {BOOST_COST} credit.")
    else:
        messages.warning(request, "Insufficient credits. Please purchase more.")
    
    return redirect(reverse('credit_tracker:post_list'))

@login_required
def post_list(request):
    posts = Post.objects.filter(user=request.user).order_by('-created_at')
    balance, _ = CreditBalance.objects.get_or_create(user=request.user)
    
    context = {
        'posts': posts,
        'current_balance': balance.balance,
    }
    return render(request, 'credit_tracker/post_list.html', context)

@login_required
def create_post(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        Post.objects.create(user=request.user, content=content)
        messages.success(request, "Post created successfully.")
        return redirect(reverse('credit_tracker:post_list'))
    return render(request, 'credit_tracker/create_post.html')

# credit_tracker/urls.py
from django.urls import path
from . import views

app_name = 'credit_tracker'

urlpatterns = [
    path('summary/', views.credit_summary, name='summary'),
    path('purchase/', views.purchase_credit, name='purchase'),
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/<int:post_id>/boost/', views.boost_post, name='boost_post'),
]

# templates/credit_tracker/summary.html
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

<a href="{% url 'credit_tracker:purchase' %}">Purchase $50 Credits</a>
<a href="{% url 'credit_tracker:post_list' %}">View Posts</a>
{% endblock %}

# templates/credit_tracker/post_list.html
{% extends "base.html" %}

{% block content %}
<h1>Your Posts</h1>
<p>Current Credit Balance: ${{ current_balance }}</p>

<a href="{% url 'credit_tracker:create_post' %}">Create New Post</a>

{% for post in posts %}
    <div>
        <p>{{ post.content }}</p>
        <p>Created at: {{ post.created_at }}</p>
        {% if post.is_boosted %}
            <p>Boosted</p>
        {% else %}
            <form method="post" action="{% url 'credit_tracker:boost_post' post.id %}">
                {% csrf_token %}
                <button type="submit">Boost Post (1 Credit)</button>
            </form>
        {% endif %}
    </div>
{% endfor %}

<a href="{% url 'credit_tracker:summary' %}">Back to Summary</a>
{% endblock %}

# templates/credit_tracker/create_post.html
{% extends "base.html" %}

{% block content %}
<h1>Create New Post</h1>
<form method="post">
    {% csrf_token %}
    <textarea name="content" required></textarea>
    <button type="submit">Create Post</button>
</form>
<a href="{% url 'credit_tracker:post_list' %}">Back to Posts</a>
{% endblock %}
