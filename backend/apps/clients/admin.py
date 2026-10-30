from django.contrib import admin
from .models import Client, ClientContact, ClientOwnershipHistory, ClientActivity
admin.site.register([Client, ClientContact, ClientOwnershipHistory, ClientActivity])
