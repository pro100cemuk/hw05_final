import django.conf

POSTS_PER_PAGE = getattr(django.conf.settings, 'APP_YATUBE_POSTS_PER_PAGE', 10)
