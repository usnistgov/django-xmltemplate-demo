#!/usr/bin/python
#
import sys
from mgi import settings
from django.contrib.auth.models import User

if len(sys.argv) < 2:
    raise RuntimeError("No password given ({0})".format(str(sys.argv)))

admin = filter(lambda u: u.username == 'admin', User.objects.all())[0]
admin.set_password(sys.argv[1])
admin.save()

