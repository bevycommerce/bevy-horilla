from django.urls import path

from . import views

urlpatterns = [
    path("popup/", views.popup, name="ws-midday-popup"),
    path("popup/<int:delivery_id>/close/", views.close, name="ws-midday-popup-close"),
    path("popup/<int:delivery_id>/midday/", views.submit_midday, name="ws-midday-popup-submit"),
    path("popup/<int:delivery_id>/skip/", views.skip_combine, name="ws-midday-popup-skip"),
    path("popup/<int:delivery_id>/sign-out/", views.sign_out, name="ws-midday-popup-sign-out"),
    path("popup/start-day/<int:delivery_id>/", views.start_day, name="ws-start-day"),
    path("popup/start-day/<int:delivery_id>/close/", views.start_day_close, name="ws-start-day-close"),
    path("popup/sign-out-update/", views.sign_out_with_update, name="ws-sign-out-update"),
]
