"""
URL configuration for izouaproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from izouapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('to-admin/', views.to_admin, name='to_admin'),
    path('logout/', views.IzouaLogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('add-inventory/', views.add_inventory, name='add_inventory'),
    path('filter-order-by-status/',views.filter_orders_by_status, name='filter_order_by_status'),
    path('filter-order-by-date/',views.filter_orders_by_date, name='filter_order_by_date'),
    path('add-order/', views.add_order, name='add_order'),
    path('login/', views.IzouaLoginView.as_view(), name='login'),
    path('download-excel/', views.download_excel, name='download_excel'),
    path('display-chart/', views.get_datas_to_chart, name='display_chart'),
    path('edit-1/', views.edit_order, name='edit_order1'),
    path('edit-2/', views.edit_order_if_granted, name='edit_order2'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
