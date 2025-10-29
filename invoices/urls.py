from django.urls import path
from . import api_views

urlpatterns = [
    path('extract/', api_views.extract_invoice, name='extract_invoice'),
    path('save/', api_views.save_invoice, name='save_invoice'),
    path('create-download/', api_views.create_and_download_invoice, name='create_and_download_invoice'),
]
