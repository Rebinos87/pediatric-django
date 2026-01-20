from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from dateutil.relativedelta import relativedelta
import math

class UserProfile(models.Model):
    """Extended user profile for staff/admin roles"""
    ROLE_CHOICES = [
        ('Admin', 'Administrator'),
        ('Staff', 'Medical Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Staff')
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.first_name} ({self.user_role})"
    
    class Meta:
        verbose_name_plural = "User Profiles"


class Patient(models.Model):
    """Patient demographics and contact information"""
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    
    BLOOD_TYPE_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('AB', 'AB'),
        ('O', 'O'),
    ]
    
    patient_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPE_CHOICES, null=True, blank=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    
    parent_name = models.CharField(max_length=100, blank=True, null=True)
    parent_contact = models.CharField(max_length=20, blank=True, null=True)
    
    address = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    
    medical_history = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    date_registered = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='patients_created')
    
    def __str__(self):
        return self.patient_name
    
    def get_age_months(self, reference_date=None):
        """Calculate age in months"""
        if reference_date is None:
            reference_date = date.today()
        rd = relativedelta(reference_date, self.date_of_birth)
        return rd.years * 12 + rd.months
    
    def get_age_display(self, reference_date=None):
        """Get human-readable age"""
        months = self.get_age_months(reference_date)
        years = months // 12
        rem_months = months % 12
        
        if years == 0:
            return f"{months} months"
        return f"{years} years {rem_months} months"
    
    def get_applicable_standard(self, reference_date=None):
        """Determine WHO vs CDC based on age"""
        months = self.get_age_months(reference_date)
        if months <= 24:
            return 'WHO'
        return 'CDC'
    
    class Meta:
        ordering = ['-date_registered']
    
    @property
    def latest_height(self):
        m = self.measurements.order_by('-measurement_date').first()
        return m.height if m else None
    
    @property
    def latest_weight(self):
        m = self.measurements.order_by('-measurement_date').first()
        return m.weight if m else None


class Measurement(models.Model):
    """Anthropometric measurements"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='measurements')
    measurement_date = models.DateField()
    
    height = models.FloatField(validators=[MinValueValidator(10), MaxValueValidator(250)])
    weight = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(200)])
    head_circumference = models.FloatField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_datetime = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.patient_name} - {self.measurement_date}"
    
    @property
    def age_at_measurement(self):
        return self.patient.get_age_months(self.measurement_date)
    
    @property
    def age_display(self):
        return self.patient.get_age_display(self.measurement_date)
    
    @property
    def bmi(self):
        if self.height > 0:
            height_m = self.height / 100
            return self.weight / (height_m ** 2)
        return None
    
    class Meta:
        ordering = ['-measurement_date']


class GrowthPercentile(models.Model):
    """WHO/CDC growth reference data"""
    CHART_TYPES = [
        ('Height', 'Height'),
        ('Weight', 'Weight'),
    ]
    
    STANDARDS = [
        ('WHO', 'WHO (0-24m)'),
        ('CDC', 'CDC (2-18y)'),
    ]
    
    age_in_months = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(240)])
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    chart_type = models.CharField(max_length=30, choices=CHART_TYPES)
    standard = models.CharField(max_length=20, choices=STANDARDS)
    
    percentile_2nd = models.FloatField()
    percentile_5th = models.FloatField()
    percentile_10th = models.FloatField()
    percentile_25th = models.FloatField()
    percentile_50th = models.FloatField()
    percentile_75th = models.FloatField()
    percentile_90th = models.FloatField()
    percentile_95th = models.FloatField()
    percentile_98th = models.FloatField()
    
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.chart_type} - {self.gender} - {self.age_in_months}m ({self.standard})"
    
    class Meta:
        unique_together = ('age_in_months', 'gender', 'chart_type', 'standard')
        ordering = ['age_in_months', 'gender', 'chart_type']


class LoginHistory(models.Model):
    """Audit trail for user logins"""
    STATUS_CHOICES = [
        ('Success', 'Successful Login'),
        ('Failed', 'Failed Login'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    login_datetime = models.DateTimeField(auto_now_add=True)
    logout_datetime = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    class Meta:
        ordering = ['-login_datetime']
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.status}"
# ==================== PATIENT DOCUMENTS ====================

class PatientDocument(models.Model):
    """Store patient documents (reports, tests, prescriptions, images)"""
    DOCUMENT_TYPES = [
        ('Report', 'Medical Report'),
        ('Test', 'Lab Test'),
        ('Image', 'X-Ray/Ultrasound'),
        ('Prescription', 'Prescription'),
        ('Vaccination', 'Vaccination Certificate'),
        ('Other', 'Other'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='Other')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='patient_documents/%Y/%m/%d/')
    uploaded_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-uploaded_date']
    
    def __str__(self):
        return f"{self.patient.patient_name} - {self.title}"
    
    @property
    def file_extension(self):
        """Get file extension"""
        return self.file.name.split('.')[-1].lower()
    
    @property
    def is_pdf(self):
        return self.file_extension == 'pdf'
    
    @property
    def is_image(self):
        return self.file_extension in ['jpg', 'jpeg', 'png', 'gif']


# ==================== MEDICINE PRESCRIPTIONS ====================

class MedicinePrescription(models.Model):
    """Store medicine prescriptions for patients"""
    FREQUENCY_CHOICES = [
        ('Once Daily', 'Once Daily'),
        ('Twice Daily', 'Twice Daily'),
        ('Thrice Daily', 'Thrice Daily'),
        ('Four Times Daily', 'Four Times Daily'),
        ('Every 6 Hours', 'Every 6 Hours'),
        ('Every 8 Hours', 'Every 8 Hours'),
        ('Every 12 Hours', 'Every 12 Hours'),
        ('As Needed', 'As Needed'),
    ]
    
    DURATION_UNIT_CHOICES = [
        ('Days', 'Days'),
        ('Weeks', 'Weeks'),
        ('Months', 'Months'),
    ]
    
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Discontinued', 'Discontinued'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 10ml")
    frequency = models.CharField(max_length=30, choices=FREQUENCY_CHOICES)
    duration_value = models.IntegerField(help_text="Number of days/weeks/months")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='Days')
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(blank=True, null=True)
    indication = models.TextField(blank=True, help_text="Why this medicine is prescribed")
    instructions = models.TextField(blank=True, help_text="Special instructions (e.g., take with food)")
    side_effects = models.TextField(blank=True, help_text="Known side effects")
    prescribed_by = models.CharField(max_length=200, blank=True, help_text="Doctor's name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.patient.patient_name} - {self.medicine_name}"
    
    @property
    def duration_string(self):
        """Return formatted duration"""
        return f"{self.duration_value} {self.duration_unit}"
    
    @property
    def is_active(self):
        """Check if prescription is currently active"""
        from datetime import date
        today = date.today()
        if self.status != 'Active':
            return False
        if self.end_date and today > self.end_date:
            return False
        return True
