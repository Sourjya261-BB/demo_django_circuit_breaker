from django.urls import path,include
from . import views

urlpatterns = [
    path('',views.get_all_users,name="show_all_users"),
]