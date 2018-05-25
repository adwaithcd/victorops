from django.conf.urls import url
from django.urls import path
from web.views import UserLogin
from .views import userdetails
from .views import user_detail_update_delete_view
from .views import index
from .views import UserLogin

urlpatterns = [
    path("", index, name="index"),
    path("user/", userdetails, name="home"),
    path("user/<int:id>/", user_detail_update_delete_view, name="home"),
    path("accounts/<int:id>/",user_detail_update_delete_view, name="home" ),
    path("apikey/", user_detail_update_delete_view, name="home"),
    path("yellowantredirecturl/register/",UserLogin,name="home")
]
