from django.urls import path
from . import views
from .views import patient_stats

urlpatterns = [
    # Authentication
    path('', views.LoginView.as_view(), name='login'),
    path('do-logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/new/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'),

    # Measurements
    path('patients/<int:patient_id>/measurements/new/',
         views.measurement_create, name='measurement_create'),
    path('patients/<int:patient_id>/measurements/<int:measurement_id>/edit/',
         views.measurement_edit, name='measurement_edit'),
    path('patients/<int:patient_id>/measurements/<int:measurement_id>/delete/',
         views.measurement_delete, name='measurement_delete'),

    # Growth charts
    path('patients/<int:patient_id>/growth-chart/',
         views.growth_chart_view, name='growth_chart'),
    path('api/growth-chart/<int:patient_id>/<str:chart_type>/',
         views.api_growth_chart_data, name='api_growth_chart'),
    path('api/bmi-chart/<int:patient_id>/',
         views.api_growth_chart_bmi, name='api_bmi_chart'),

    # Admin
  # pediatric/urls.py
    path('manage/users/', views.users_list, name='users_list'),
    path('manage/users/new/', views.user_create, name='user_create'),


    # Reports
    path('patients/<int:patient_id>/report/',
         views.patient_report, name='patient_report'),

    # Documents
    path('patients/<int:patient_id>/documents/',
         views.patient_documents, name='patient_documents'),
    path('patients/<int:patient_id>/documents/upload/',
         views.document_upload, name='document_upload'),
    path('documents/<int:doc_id>/delete/',
         views.document_delete, name='document_delete'),
    path('documents/<int:doc_id>/download/',
         views.document_download, name='document_download'),

    # Prescriptions
    path('patients/<int:patient_id>/prescriptions/',
         views.patient_prescriptions, name='patient_prescriptions'),
    path('patients/<int:patient_id>/prescriptions/add/',
         views.prescription_add, name='prescription_add'),
    path('prescriptions/<int:rx_id>/edit/',
         views.prescription_edit, name='prescription_edit'),
    path('prescriptions/<int:rx_id>/delete/',
         views.prescription_delete, name='prescription_delete'),
    path('prescriptions/<int:rx_id>/print/',
     views.prescription_print,
     name='prescription_print'),
    path('patients/<int:patient_id>/prescriptions/print/',
     views.prescription_print_all,
     name='prescription_print_all'),

     path("patients/stats/", patient_stats, name="patient_stats"),

]
