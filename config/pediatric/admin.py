from django.contrib import admin
from .models import (
    Patient,
    Measurement,
    GrowthPercentile,
    UserProfile,
    LoginHistory,
    PatientDocument,
    MedicinePrescription,
)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'date_of_birth', 'gender', 'date_registered')
    search_fields = ('patient_name', 'parent_name')
    list_filter = ('gender', 'date_registered')

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'measurement_date', 'height', 'weight', 'bmi')
    search_fields = ('patient__patient_name',)
    list_filter = ('measurement_date',)

@admin.register(GrowthPercentile)
class GrowthPercentileAdmin(admin.ModelAdmin):
    list_display = ('age_in_months', 'gender', 'chart_type', 'standard')
    list_filter = ('gender', 'chart_type', 'standard', 'age_in_months')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_role', 'is_active')

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_datetime', 'status')
    readonly_fields = ('login_datetime', 'logout_datetime')

@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'document_type', 'uploaded_date', 'uploaded_by')
    search_fields = ('patient__patient_name', 'title')
    list_filter = ('document_type', 'uploaded_date')
    readonly_fields = ('uploaded_date', 'uploaded_by')

    def save_model(self, request, obj, form, change):
        if not change and not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MedicinePrescription)
class MedicinePrescriptionAdmin(admin.ModelAdmin):
    list_display = ('medicine_name', 'patient', 'dosage', 'frequency', 'status', 'start_date')
    search_fields = ('patient__patient_name', 'medicine_name', 'prescribed_by')
    list_filter = ('status', 'start_date', 'frequency')
    readonly_fields = ('start_date',)
