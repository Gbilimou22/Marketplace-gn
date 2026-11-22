import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        # Python 3.14 compatibility patch for django.template.context.BaseContext.__copy__
        # In Python 3.14, copy(super()) returns a super proxy object instead of copying self.
        if sys.version_info >= (3, 14):
            from django.template import context

            def _base_context_copy(self):
                cls = self.__class__
                duplicate = cls.__new__(cls)
                duplicate.__dict__ = self.__dict__.copy()
                duplicate.dicts = self.dicts[:]
                return duplicate

            context.BaseContext.__copy__ = _base_context_copy

