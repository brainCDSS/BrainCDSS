#!/usr/bin/env python
"""Django administrative entry point."""

import os
import sys


if __name__ == "__main__":

    # Running `python manage.py test` must never inherit the ordinary
    # local PostgreSQL / Cloud SQL configuration by accident.
    #
    # Explicit DJANGO_SETTINGS_MODULE still wins because setdefault()
    # does not overwrite an already supplied value.
    default_settings = (
        "config.settings.test"
        if len(sys.argv) > 1
        and sys.argv[1] == "test"
        else "config.settings.local"
    )

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        default_settings,
    )

    from django.core.management import (
        execute_from_command_line,
    )

    execute_from_command_line(
        sys.argv,
    )
