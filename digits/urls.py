from django.urls import path
from . import views

from users import views as users_views

app_name = 'digits'
urlpatterns = [
    path('', views.index, name='index'),
    path('start/', views.start_display, name='start_display'),      # show random number for 10s
    path('commit/', views.commit_entry, name='commit_entry'),       # after 10s JS posts to store + email
    path('list/', views.entry_list, name='entry_list'),             # simple list for admin/user
    path('reveal/<uuid:entry_id>/', views.reveal_request, name='reveal_request'),
    path('verify/<uuid:entry_id>/', views.verify_challenge, name='verify_challenge'),
    path('delete/<uuid:entry_id>/', views.delete_entry, name='delete_entry'),

   
]
