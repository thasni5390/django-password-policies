from .models import PasswordHistory, PasswordChangeRequired
from .constants import *


def password_update_done(user, request):
    PasswordHistory.objects.create(
        user=user,
        password=user.password
    )
    PasswordChangeRequired.objects.filter(user=user).delete()
    request.session[SESSION_KEY_REQUIRED] = False
