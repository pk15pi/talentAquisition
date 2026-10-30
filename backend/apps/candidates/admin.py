from django.contrib import admin
from .models import Candidate, Resume, CandidateNote, CandidateConsent, DuplicateReview
admin.site.register([Candidate, Resume, CandidateNote, CandidateConsent, DuplicateReview])
