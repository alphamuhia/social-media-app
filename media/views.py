from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.dispatch import receiver
from django.db.models.signals import post_save

from .forms import UserRegistrationForm, ProfileUpdateForm, PostForm, UserProfileForm
from .models import Profile, Post, Comment, Follow, UserProfile, Notification, Message, Report, Block, ActivityLog, Like
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            auth_login(request, user) 
            return redirect('home')
    else:
        form = UserRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            next_url = request.GET.get('next', reverse('home'))
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home') 

@login_required
def profile(request, username=None):
    if username is None:
        username = request.user.username
    user = User.objects.get(username=username)

    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=user.username)
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'profile.html', {'form': form, 'user': user})

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

def profile_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    form = UserProfileForm(request.POST or None, request.FILES or None, instance=user_profile)

    if form.is_valid():
        form.save()
        
        return redirect('profile')  

    posts = user_profile.user.posts.all()  
    return render(request, 'profile.html', {
        'user': render.user,
        'form': form,
        'posts': posts,
        'is_private': user_profile.is_private  
    })

@login_required
def create_post(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        Post.objects.create(author=request.user, content=content, image=image)
        ActivityLog.objects.create(user=request.user, action='Created a post')
        return redirect('home')

def posts_view(request):
    posts = Post.objects.all() 
    return render(request, 'posts.html', {'posts': posts})

def user_posts_view(request):
    user_posts = Post.objects.filter(author=request.user)
    return render(request, 'posts.html', {'posts': user_posts})

@login_required
def add_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            ActivityLog.objects.create(user=request.user, action='Created a post')
            return redirect('home') 
    else:
        form = PostForm()

    return render(request, 'add_post.html', {'form': form})

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        content = request.POST['content']
        Comment.objects.create(post=post, author=request.user, content=content)
    return redirect('posts')

def home(request):
    posts = Post.objects.all().order_by('-created_at')
    filtered_posts = [
        post for post in posts
        # if not post.author.profile.is_private or post.author in request.user.following.all()
    ]
    return render(request, 'home.html', {'posts': filtered_posts})


@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        Report.objects.create(user=request.user, post=post, reason=reason)
    return redirect('posts')


@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    Follow.objects.get_or_create(follower=request.user, following=user_to_follow)
    return redirect('home')


@login_required
def unfollow_user(request, user_id):
    user_to_unfollow = get_object_or_404(User, id=user_id)
    Follow.objects.filter(follower=request.user, following=user_to_unfollow).delete()
    return redirect('home')


@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {'notifications': user_notifications})

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created:  
        notification_message = f"{instance.user.username} liked your post."
        Notification.objects.create(user=instance.post.user, message=notification_message)

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created:
        notification_message = f"{instance.user.username} commented on your post."
        Notification.objects.create(user=instance.post.user, message=notification_message)

@receiver(post_save, sender=Block)
def create_block_notification(sender, instance, created, **kwargs):
    if created:
        notification_message = f"You have been blocked by {instance.blocker.username}."
        Notification.objects.create(user=instance.blocked, message=notification_message)

@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {'notifications': user_notifications})

@login_required
def mark_as_read(request, notification_id):
    notification = Notification.objects.get(id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications')

@login_required
def base_view(request):
    notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, 'base.html', {'notifications_count': notifications_count})


@login_required
def send_message(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        Message.objects.create(sender=request.user, receiver=receiver, content=content)
        return redirect('home')


@login_required
def inbox(request):
    messages = Message.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, 'inbox.html', {'messages': messages})


def search_users(request):
    users = None
    if 'username' in request.GET:
        query = request.GET['username']
        if query:
            users = User.objects.filter(username__icontains=query)
    return render(request, 'search.html', {'users': users})


def admin_required(function):
    return user_passes_test(lambda u: u.is_active and hasattr(u, 'profile') and u.profile.role == 'admin')(function)


@admin_required
def admin_dashboard(request):
    reports = Report.objects.all()
    return render(request, 'admin_dashboard.html', {'reports': reports})

@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        Report.objects.create(user=request.user, post=post, reason=reason)
    return redirect('posts')


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect('posts')

@login_required
def activity_logs(request):
    logs = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'activity_logs.html', {'logs': logs})


@login_required
def block_user(request, user_id):
    user_to_block = get_object_or_404(User, id=user_id)
    Block.objects.get_or_create(blocker=request.user, blocked=user_to_block)
    return redirect('posts')


@login_required
def unblock_user(request, user_id):
    user_to_unblock = get_object_or_404(User, id=user_id)
    Block.objects.filter(blocker=request.user, blocked=user_to_unblock).delete()
    return redirect('home')
