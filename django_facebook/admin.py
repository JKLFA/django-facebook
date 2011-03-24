from django.contrib import admin

from django_facebook.models import FacebookProfile, Concentration, School, Attended

admin.site.register(FacebookProfile)
admin.site.register(Concentration)
admin.site.register(School)
admin.site.register(Attended)
