from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload, name="upload"),
    path("docs/<uuid:doc_id>/download/", views.download, name="download"),
    path("docs/<uuid:doc_id>/edit/", views.edit, name="edit"),
    path("docs/<uuid:doc_id>/delete/", views.delete, name="delete"),
    path("docs/<uuid:doc_id>/share/", views.share, name="share"),
    path("docs/<uuid:doc_id>/revoke/<int:user_id>/", views.revoke, name="revoke"),
    path("admin-activity/", views.activity, name="activity"),
]
