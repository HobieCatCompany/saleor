from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        r"^export-orders/$",
        views.export_orders_to_csv
    ),
]