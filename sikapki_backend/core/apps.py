from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Pengguna dan Hak Akses'

    def ready(self):
        from . import audit  # noqa: F401
