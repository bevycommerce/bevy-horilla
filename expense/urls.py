from django.urls import path

from expense import views

urlpatterns = [
    path("submit/", views.expense_submit, name="expense-submit"),
    path("log/", views.expense_log, name="expense-log"),
]
