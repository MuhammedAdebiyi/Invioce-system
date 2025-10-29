from django.urls import path
from .api_views import create_and_download_invoice

urlpatterns = [
    path("create-and-download/", create_and_download_invoice, name="create_and_download_invoice"),
]
