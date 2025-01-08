from django.apps import AppConfig
from django.core.signals import request_finished
from django.dispatch import receiver
from .startup import initialize_connections, get_connection_manager_instance

class DemoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'demo'

    def ready(self):
        # Initialize connections
        initialize_connections()

        @receiver(request_finished)
        def close_connections(sender, **kwargs):
            # Lazily fetch the connection manager instance
            try:
                connection_manager_instance = get_connection_manager_instance()
                connection_manager_instance.close_connections()
            except RuntimeError:
                # Log or handle cases where the connection manager isn't initialized
                pass
