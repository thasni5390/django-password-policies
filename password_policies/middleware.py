import datetime
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.messages.storage import session
from django.http import HttpResponseRedirect
from django.urls import reverse, NoReverseMatch, resolve, Resolver404
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import localtime

from .utils import Utils
from .models import PasswordChangeRequired, PasswordHistory
from .utils import PasswordCheck
from .constants import *


class PasswordChangeMiddleware(MiddlewareMixin):

    checked = SESSION_KEY_CHECKED
    expired = SESSION_KEY_EXPIRED
    last = SESSION_KEY_LAST
    required = SESSION_KEY_REQUIRED
    td = timedelta(seconds=Utils.get_setting('PASSWORD_DURATION_SECONDS'))

    def _check_history(self, request):
        if not request.session.get(self.last, None):
            newest = PasswordHistory.objects.get_newest(request.user)
            if newest:
                request.session[self.last] = newest.created.isoformat()
            else:
                request.session[self.last] = request.user.date_joined.isoformat()
        last_password_updated_time = datetime.datetime.fromisoformat(request.session[self.last])
        if last_password_updated_time < self.expiry_datetime:
            request.session[self.required] = True
            if not PasswordChangeRequired.objects.filter(user=request.user).count():
                PasswordChangeRequired.objects.create(user=request.user)
        else:
            request.session[self.required] = False

    def _check_necessary(self, request):

        if not request.session.get(self.checked, None):
            request.session[self.checked] = self.now
            #  If the PASSWORD_CHECK_ONLY_AT_LOGIN is set, then only check at the beginning of session, which we can
            #  tell by self.now time having just been set.
        if not Utils.get_setting('PASSWORD_CHECK_ONLY_AT_LOGIN') or request.session[self.checked] == self.now:
            # If a password change is enforced we won't check
            # the user's password history, thus reducing DB hits...
            if PasswordChangeRequired.objects.filter(user=request.user).count():
                request.session[self.required] = True
                return
            checked_date = datetime.datetime.fromisoformat(request.session.get(self.checked, None))
            if checked_date < self.expiry_datetime:
                try:
                    del request.session[self.last]
                    del request.session[self.checked]
                    del request.session[self.required]
                    del request.session[self.expired]
                except KeyError:
                    pass
            if Utils.get_setting('PASSWORD_USE_HISTORY'):
                self._check_history(request)
        else:
            # In the case where PASSWORD_CHECK_ONLY_AT_LOGIN is true, the required key is not removed,
            # therefore causing a never ending password update loop
            if not self.required in request.session.keys():
                request.session[self.required] = False

    def _is_excluded_path(self, actual_path):
        paths = Utils.get_setting('PASSWORD_CHANGE_MIDDLEWARE_EXCLUDED_PATHS')
        path = r'^%s$' % self.url
        paths.append(path)
        media_url = settings.MEDIA_URL
        if media_url:
            paths.append(r'^%s?' % media_url)
        static_url = settings.STATIC_URL
        if static_url:
            paths.append(r'^%s?' % static_url)
        if Utils.get_setting('PASSWORD_CHANGE_MIDDLEWARE_ALLOW_LOGOUT'):
            try:
                logout_url = reverse('logout')
            except NoReverseMatch:
                pass
            else:
                paths.append(r'^%s$' % logout_url)
            try:
                logout_url = u'/admin/logout/'
                resolve(logout_url)
            except Resolver404:
                pass
            else:
                paths.append(r'^%s$' % logout_url)
        for path in paths:
            if re.match(path, actual_path):
                return True
        return False

    def _redirect(self, request):
        REDIRECT_FIELD_NAME = Utils.get_setting('REDIRECT_FIELD_NAME')
        if request.session[self.required]:
            redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')
            if redirect_to:
                next_to = redirect_to
            else:
                next_to = request.get_full_path()
            url = "%s?%s=%s" % (self.url, REDIRECT_FIELD_NAME, next_to)
            return HttpResponseRedirect(url)

    def process_request(self, request):
        if request.method != 'GET':
            return
        try:
            resolve(request.path_info)
        except Resolver404:
            return
        self.now = timezone.now().isoformat()
        self.url = reverse('password_change')
        if Utils.get_setting('PASSWORD_DURATION_SECONDS') and \
                request.user.is_authenticated and not request.user.is_superuser and not self._is_excluded_path(request.path):
            self.check = PasswordCheck(request.user)
            self.expiry_datetime = self.check.get_expiry_datetime()
            self._check_necessary(request)
            return self._redirect(request)
