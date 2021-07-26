=====
Password Policies
=====

django-password-policies is an application for the Django framework that provides unicode-aware password policies on password changes and resets and a mechanism to force password changes.


Quick start
-----------

1. Add "password_policies" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'password_policies',
    ]

2.  Add "password_policies.middleware.PasswordChangeMiddleware" to your  MIDDLEWARE settings like this::

    MIDDLEWARE = (
        ...
        'password_policies.middleware.PasswordChangeMiddleware',
    )

3. Add "password_policies.context_processors.password_status" to your  TEMPLATE_CONTEXT_PROCESSORS settings like this::

    TEMPLATE_CONTEXT_PROCESSORS = (
        ...
        'password_policies.context_processors.password_status',
    )

4. Run ``python manage.py migrate`` to create the password_policies models.
