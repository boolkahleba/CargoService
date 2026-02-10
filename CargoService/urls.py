from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cargo.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('editor-ymaps/', include('editor_ymaps.urls')),
]
