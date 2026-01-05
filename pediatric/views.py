from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from django.utils.decorators import method_decorator
from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.http import HttpResponse

import json

from .models import (
    Patient,
    Measurement,
    GrowthPercentile,
    UserProfile,
    LoginHistory,
    PatientDocument,
    MedicinePrescription,
)


# ==================== AUTHENTICATION ====================

from .models import UserProfile
from django.views import View
from django.utils.decorators import method_decorator

class LoginView(View):
    def get(self, request):
        """Render login form"""
        return render(request, 'auth/login.html')

    def post(self, request):
        """Handle login submission"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'user_role': 'Staff', 'is_active': True},
            )
            if profile.is_active:
                login(request, user)
                LoginHistory.objects.create(user=user, status='Success')
                return redirect('dashboard')
        LoginHistory.objects.create(
            user=User.objects.filter(username=username).first(),
            status='Failed'
        )
        return render(request, 'auth/login.html', {
            'error': 'Invalid username or password'
        })

@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')


# ==================== DASHBOARD ====================

@login_required
def dashboard(request):
    """Main dashboard"""
    total_patients = Patient.objects.count()
    recent_patients = Patient.objects.all()[:5]
    recent_measurements = Measurement.objects.select_related('patient').all()[:10]
    
    stats = {
        'total_patients': total_patients,
        'total_measurements': Measurement.objects.count(),
        'recent_patients': recent_patients,
        'recent_measurements': recent_measurements,
    }
    
    return render(request, 'dashboard/dashboard.html', stats)


# ==================== PATIENTS ====================

@login_required
def patient_list(request):
    """List all patients with search"""
    query = request.GET.get('q', '')
    
    patients = Patient.objects.all()
    
    if query:
        patients = patients.filter(
            Q(patient_name__icontains=query) |
            Q(contact_number__icontains=query) |
            Q(parent_name__icontains=query)
        )
    
    patients = patients.order_by('-date_registered')
    
    return render(request, 'patients/patient_list.html', {
        'patients': patients,
        'query': query
    })


@login_required
def patient_detail(request, pk):
    """View patient details and measurements"""
    patient = get_object_or_404(Patient, pk=pk)
    measurements = patient.measurements.all().order_by('-measurement_date')
    
    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'measurements': measurements,
    })



@login_required
def patient_create(request):
    """Create new patient"""
    if request.method == 'POST':
        patient = Patient.objects.create(
            patient_name=request.POST.get('patient_name'),
            date_of_birth=request.POST.get('date_of_birth'),
            gender=request.POST.get('gender'),
            blood_type=request.POST.get('blood_type', ''),
            contact_number=request.POST.get('contact_number', ''),
            parent_name=request.POST.get('parent_name', ''),
            parent_contact=request.POST.get('parent_contact', ''),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            country=request.POST.get('country', ''),
            medical_history=request.POST.get('medical_history', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user,
        )
        return redirect('patient_detail', pk=patient.pk)
    
    return render(request, 'patients/patient_form.html')


# ==================== MEASUREMENTS ====================

@login_required
def measurement_create(request, patient_id):
    """Record new measurement for patient"""
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        measurement = Measurement.objects.create(
            patient=patient,
            measurement_date=request.POST.get('measurement_date'),
            height=float(request.POST.get('height')),
            weight=float(request.POST.get('weight')),
            head_circumference=request.POST.get('head_circumference') or None,
            notes=request.POST.get('notes', ''),
            recorded_by=request.user,
        )
        return redirect('patient_detail', pk=patient.pk)
    
    return render(request, 'measurements/measurement_form.html', {
        'patient': patient
    })


# ==================== GROWTH CHARTS (API) ====================

@login_required
@require_GET
def api_growth_chart_data(request, patient_id, chart_type):
    """API endpoint returning growth chart data as JSON"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurements = patient.measurements.all().order_by('measurement_date')
    
    if not measurements.exists():
        return JsonResponse({'error': 'No measurements found'}, status=400)
    
    gender = patient.gender
    standard = patient.get_applicable_standard()
    
    percentiles = GrowthPercentile.objects.filter(
        gender=gender,
        chart_type=chart_type.title(),
        standard=standard
    ).order_by('age_in_months')
    
    chart_data = {
        'labels': [],
        'datasets': [
            {
                'label': 'Patient Measurement',
                'data': [],
                'borderColor': '#22c55e',
                'backgroundColor': 'rgba(34, 197, 92, 0.1)',
                'borderWidth': 3,
                'fill': False,
                'pointRadius': 5,
                'pointBackgroundColor': '#22c55e',
            },
            {
                'label': '50th Percentile (Median)',
                'data': [],
                'borderColor': '#ef4444',
                'borderWidth': 2,
                'fill': False,
                'tension': 0.4,
            },
            {
                'label': '2nd Percentile',
                'data': [],
                'borderColor': '#9ca3af',
                'borderWidth': 1,
                'borderDash': [5, 5],
                'fill': False,
                'tension': 0.4,
            },
            {
                'label': '98th Percentile',
                'data': [],
                'borderColor': '#9ca3af',
                'borderWidth': 1,
                'borderDash': [5, 5],
                'fill': False,
                'tension': 0.4,
            },
        ]
    }
    
    if chart_type.lower() == 'height':
        value_key = 'height'
        ylabel = 'Height (cm)'
    else:
        value_key = 'weight'
        ylabel = 'Weight (kg)'
    
    for m in measurements:
        age_months = m.age_at_measurement
        value = getattr(m, value_key)
        chart_data['labels'].append(age_months)
        chart_data['datasets'][0]['data'].append({
            'x': age_months,
            'y': value
        })
    
    percentile_data = {}
    for p in percentiles:
        percentile_data[p.age_in_months] = p
    
    for age_month in sorted(percentile_data.keys()):
        p = percentile_data[age_month]
        chart_data['datasets'][1]['data'].append({
            'x': age_month,
            'y': p.percentile_50th
        })
        chart_data['datasets'][2]['data'].append({
            'x': age_month,
            'y': p.percentile_2nd
        })
        chart_data['datasets'][3]['data'].append({
            'x': age_month,
            'y': p.percentile_98th
        })
    
    return JsonResponse({
        'chartData': chart_data,
        'title': f'{chart_type.title()}-for-Age ({patient.gender}, {standard})',
        'yLabel': ylabel,
        'xLabel': 'Age (months)',
    })


@login_required
def growth_chart_view(request, patient_id):
    """Display growth charts for patient"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurements_count = patient.measurements.count()

    if measurements_count == 0:
        messages.info(
            request,
            'No measurements yet for this patient. Please add a measurement to see growth charts.'
        )
        return redirect('patient_detail', pk=patient.pk)

    return render(request, 'charts/growth_charts.html', {
        'patient': patient,
    })


# ==================== ADMIN VIEWS ====================

def require_admin(func):
    """Decorator to require admin role"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.profile.user_role != 'Admin':
            return redirect('dashboard')
        return func(request, *args, **kwargs)
    return wrapper


@require_admin
@login_required
def users_list(request):
    """List all users (Admin only)"""
    users = User.objects.all().select_related('profile')
    return render(request, 'admin/users_list.html', {'users': users})


@require_admin
@login_required
def user_create(request):
    """Create new user (Admin only)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'Staff')
        
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            email=email,
            password=password,
        )
        
        UserProfile.objects.create(
            user=user,
            user_role=user_role,
        )
        
        return redirect('users_list')
    
    return render(request, 'admin/user_form.html')


# ==================== REPORTS ====================

@login_required
def patient_report(request, patient_id):
    """Generate patient report"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurements = patient.measurements.all().order_by('measurement_date')
    
    report_data = {
        'patient': patient,
        'measurements': measurements,
        'age': patient.get_age_display(),
        'latest_measurement': measurements.first(),
    }
    
    return render(request, 'reports/patient_report.html', report_data)
# ==================== PATIENT EDIT / DELETE ====================

@login_required
def patient_edit(request, pk):
    """Edit patient details"""
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        patient.patient_name = request.POST.get('patient_name')
        patient.date_of_birth = request.POST.get('date_of_birth')
        patient.gender = request.POST.get('gender')
        patient.blood_type = request.POST.get('blood_type', '')
        patient.contact_number = request.POST.get('contact_number', '')
        patient.parent_name = request.POST.get('parent_name', '')
        patient.parent_contact = request.POST.get('parent_contact', '')
        patient.address = request.POST.get('address', '')
        patient.city = request.POST.get('city', '')
        patient.country = request.POST.get('country', '')
        patient.medical_history = request.POST.get('medical_history', '')
        patient.notes = request.POST.get('notes', '')
        patient.save()
        return redirect('patient_detail', pk=patient.pk)
    
    return render(request, 'patients/patient_edit.html', {
        'patient': patient
    })


@login_required
def patient_delete(request, pk):
    """Delete patient (with confirmation)"""
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        patient.delete()
        return redirect('patient_list')
    
    return render(request, 'patients/patient_delete_confirm.html', {
        'patient': patient
    })


# ==================== MEASUREMENT EDIT / DELETE ====================

@login_required
def measurement_edit(request, patient_id, measurement_id):
    """Edit measurement"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurement = get_object_or_404(Measurement, pk=measurement_id, patient=patient)
    
    if request.method == 'POST':
        measurement.measurement_date = request.POST.get('measurement_date')
        measurement.height = float(request.POST.get('height'))
        measurement.weight = float(request.POST.get('weight'))
        measurement.head_circumference = request.POST.get('head_circumference') or None
        measurement.notes = request.POST.get('notes', '')
        measurement.save()
        return redirect('patient_detail', pk=patient.pk)
    
    return render(request, 'measurements/measurement_edit.html', {
        'patient': patient,
        'measurement': measurement
    })


@login_required
def measurement_delete(request, patient_id, measurement_id):
    """Delete measurement (with confirmation)"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurement = get_object_or_404(Measurement, pk=measurement_id, patient=patient)
    
    if request.method == 'POST':
        measurement.delete()
        return redirect('patient_detail', pk=patient.pk)
    
    return render(request, 'measurements/measurement_delete_confirm.html', {
        'patient': patient,
        'measurement': measurement
    })

@login_required
@require_GET
def api_growth_chart_bmi(request, patient_id):
    """API endpoint for BMI-for-age chart"""
    patient = get_object_or_404(Patient, pk=patient_id)
    measurements = patient.measurements.all().order_by('measurement_date')
    
    if not measurements.exists():
        return JsonResponse({'error': 'No measurements found'}, status=400)
    
    gender = patient.gender
    standard = patient.get_applicable_standard()
    
    # Get BMI percentile data (we'll use weight/height percentiles as proxy)
    percentiles = GrowthPercentile.objects.filter(
        gender=gender,
        chart_type='Weight',
        standard=standard
    ).order_by('age_in_months')
    
    chart_data = {
        'labels': [],
        'datasets': [
            {
                'label': 'Patient BMI',
                'data': [],
                'borderColor': '#3b82f6',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'borderWidth': 3,
                'fill': False,
                'pointRadius': 5,
                'pointBackgroundColor': '#3b82f6',
            },
            {
                'label': '50th Percentile',
                'data': [],
                'borderColor': '#ef4444',
                'borderWidth': 2,
                'fill': False,
                'tension': 0.4,
            },
            {
                'label': '5th Percentile',
                'data': [],
                'borderColor': '#9ca3af',
                'borderWidth': 1,
                'borderDash': [5, 5],
                'fill': False,
                'tension': 0.4,
            },
            {
                'label': '95th Percentile',
                'data': [],
                'borderColor': '#9ca3af',
                'borderWidth': 1,
                'borderDash': [5, 5],
                'fill': False,
                'tension': 0.4,
            },
        ]
    }
    
    # Add patient BMI data
    for m in measurements:
        if m.bmi:
            age_months = m.age_at_measurement
            chart_data['labels'].append(age_months)
            chart_data['datasets'][0]['data'].append({
                'x': age_months,
                'y': m.bmi
            })
    
    # Add percentile curves (approximated from weight/height)
    percentile_data = {}
    for p in percentiles:
        percentile_data[p.age_in_months] = p
    
    for age_month in sorted(percentile_data.keys()):
        p = percentile_data[age_month]
        # Approximate BMI from weight percentiles
        chart_data['datasets'][1]['data'].append({
            'x': age_month,
            'y': p.percentile_50th / (1.5)  # Rough approximation
        })
        chart_data['datasets'][2]['data'].append({
            'x': age_month,
            'y': p.percentile_5th / (1.5)
        })
        chart_data['datasets'][3]['data'].append({
            'x': age_month,
            'y': p.percentile_95th / (1.5)
        })
    
    return JsonResponse({
        'chartData': chart_data,
        'title': f'BMI-for-Age ({patient.gender}, {standard})',
        'yLabel': 'BMI (kg/m²)',
        'xLabel': 'Age (months)',
    })
from django.http import FileResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET
import os

# ==================== PATIENT DOCUMENTS ====================

@login_required
def patient_documents(request, patient_id):
    """List all documents for a patient"""
    patient = get_object_or_404(Patient, pk=patient_id)
    documents = patient.documents.all()
    
    return render(request, 'documents/patient_documents.html', {
        'patient': patient,
        'documents': documents,
    })


@login_required
def document_upload(request, patient_id):
    """Upload new document for patient"""
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        
        if file:
            doc = PatientDocument.objects.create(
                patient=patient,
                document_type=document_type,
                title=title,
                description=description,
                file=file,
                uploaded_by=request.user
            )
            messages.success(request, f'Document "{title}" uploaded successfully!')
            return redirect('patient_documents', patient_id=patient.pk)
    
    return render(request, 'documents/document_upload.html', {
        'patient': patient,
        'doc_types': PatientDocument.DOCUMENT_TYPES,
    })


@login_required
def document_delete(request, doc_id):
    """Delete a document"""
    document = get_object_or_404(PatientDocument, pk=doc_id)
    patient_id = document.patient.pk
    
    if request.method == 'POST':
        document.file.delete()  # Delete file from storage
        document.delete()
        messages.success(request, f'Document deleted!')
        return redirect('patient_documents', patient_id=patient_id)
    
    return render(request, 'documents/document_delete_confirm.html', {
        'document': document,
    })


from django.http import FileResponse, Http404
import os

@login_required
def document_download(request, doc_id):
    document = get_object_or_404(PatientDocument, pk=doc_id)
    file_field = document.file

    # Safely check that the file is configured and really exists on storage
    if not file_field or not file_field.name or not file_field.storage.exists(file_field.name):
        raise Http404("File not found")

    return FileResponse(
        file_field.open('rb'),
        as_attachment=True,
        filename=os.path.basename(file_field.name),
    )



# ==================== MEDICINE PRESCRIPTIONS ====================

@login_required
def patient_prescriptions(request, patient_id):
    """List all prescriptions for a patient"""
    patient = get_object_or_404(Patient, pk=patient_id)
    prescriptions = patient.prescriptions.all()
    
    # Separate active and inactive
    active_prescriptions = [p for p in prescriptions if p.is_active]
    inactive_prescriptions = [p for p in prescriptions if not p.is_active]
    
    return render(request, 'prescriptions/patient_prescriptions.html', {
        'patient': patient,
        'active_prescriptions': active_prescriptions,
        'inactive_prescriptions': inactive_prescriptions,
    })


@login_required
def prescription_add(request, patient_id):
    """Add new prescription"""
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        prescription = MedicinePrescription.objects.create(
            patient=patient,
            medicine_name=request.POST.get('medicine_name'),
            dosage=request.POST.get('dosage'),
            frequency=request.POST.get('frequency'),
            duration_value=int(request.POST.get('duration_value')),
            duration_unit=request.POST.get('duration_unit'),
            indication=request.POST.get('indication', ''),
            instructions=request.POST.get('instructions', ''),
            side_effects=request.POST.get('side_effects', ''),
            prescribed_by=request.POST.get('prescribed_by', ''),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, f'Prescription for {prescription.medicine_name} added!')
        return redirect('patient_prescriptions', patient_id=patient.pk)
    
    return render(request, 'prescriptions/prescription_form.html', {
        'patient': patient,
        'frequencies': MedicinePrescription.FREQUENCY_CHOICES,
        'units': MedicinePrescription.DURATION_UNIT_CHOICES,
        'is_edit': False,
    })


@login_required
def prescription_edit(request, rx_id):
    """Edit existing prescription"""
    prescription = get_object_or_404(MedicinePrescription, pk=rx_id)
    patient = prescription.patient
    
    if request.method == 'POST':
        prescription.medicine_name = request.POST.get('medicine_name')
        prescription.dosage = request.POST.get('dosage')
        prescription.frequency = request.POST.get('frequency')
        prescription.duration_value = int(request.POST.get('duration_value'))
        prescription.duration_unit = request.POST.get('duration_unit')
        prescription.indication = request.POST.get('indication', '')
        prescription.instructions = request.POST.get('instructions', '')
        prescription.side_effects = request.POST.get('side_effects', '')
        prescription.prescribed_by = request.POST.get('prescribed_by', '')
        prescription.status = request.POST.get('status')
        prescription.end_date = request.POST.get('end_date') or None
        prescription.notes = request.POST.get('notes', '')
        prescription.save()
        
        messages.success(request, f'Prescription updated!')
        return redirect('patient_prescriptions', patient_id=patient.pk)
    
    return render(request, 'prescriptions/prescription_form.html', {
        'patient': patient,
        'prescription': prescription,
        'frequencies': MedicinePrescription.FREQUENCY_CHOICES,
        'units': MedicinePrescription.DURATION_UNIT_CHOICES,
        'statuses': MedicinePrescription.STATUS_CHOICES,
        'is_edit': True,
    })


@login_required
def prescription_delete(request, rx_id):
    """Delete prescription"""
    prescription = get_object_or_404(MedicinePrescription, pk=rx_id)
    patient_id = prescription.patient.pk
    
    if request.method == 'POST':
        prescription.delete()
        messages.success(request, 'Prescription deleted!')
        return redirect('patient_prescriptions', patient_id=patient_id)
    
    return render(request, 'prescriptions/prescription_delete_confirm.html', {
        'prescription': prescription,
    })

from django.http import HttpResponse
from django.template.loader import render_to_string

@login_required
def prescription_print(request, rx_id):
    prescription = get_object_or_404(MedicinePrescription, pk=rx_id)
    patient = prescription.patient
    html = render_to_string(
        'prescriptions/prescription_print.html',
        {'patient': patient, 'prescription': prescription}
    )
    return HttpResponse(html)
@login_required

def prescription_print_all(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    prescriptions = MedicinePrescription.objects.filter(patient=patient)
    return render(request, 'prescriptions/prescription_print_all.html', {
        'patient': patient,
        'prescriptions': prescriptions,
    })

