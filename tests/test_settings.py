from django.conf import settings


def test_django_settings_and_localization():
    """Verify that Django settings comply with Guinean context constraints."""
    assert settings.TIME_ZONE == "Africa/Conakry"
    assert settings.LANGUAGE_CODE == "fr-fr"
    assert settings.CURRENCY_CODE == "GNF"
    assert settings.USE_TZ is True


def test_core_installed_apps():
    """Verify that required apps are registered."""
    assert "apps.core.apps.CoreConfig" in settings.INSTALLED_APPS
    assert "allauth" in settings.INSTALLED_APPS
    assert "allauth.account" in settings.INSTALLED_APPS


def test_security_defaults_present():
    """Check essential security defaults."""
    assert hasattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE")
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE <= 5 * 1024 * 1024
