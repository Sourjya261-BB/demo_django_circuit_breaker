# # apps.py
# from django.apps import AppConfig
# from demo.config_fetcher import DATABASES, update_db_config_for_tenant, service_tenant_settings
# from demo.connection_manager import ConnectionManager
#
# connection_manager_instance = None
#
# def get_connection_manager_instance():
#     if connection_manager_instance is None:
#         raise RuntimeError("Connection manager instance is not initialized. Make sure AppConfig.ready() has run.")
#     return connection_manager_instance
#
# class TestAppConfig(AppConfig):
#     name = 'test_app'
#
#     def ready(self):
#         global connection_manager_instance
#         if connection_manager_instance is None:  # Only initialize if not already done
#             # Initialize database settings and connection manager
#             for tenant_id, tenant_config in service_tenant_settings['config_json'].items():
#                 tenant_id = int(tenant_id)
#                 update_db_config_for_tenant(tenant_id, tenant_config)
#
#             # Create and assign the ConnectionManager instance
#             connection_manager_instance = ConnectionManager(DATABASES)
#             print("Connection_manager_instance initialized")
#
#             # Optional: Add signal for cleanup
#             from django.core.signals import request_finished
#             from django.dispatch import receiver
#
#             @receiver(request_finished)
#             def close_connections(sender, **kwargs):
#                 if connection_manager_instance:
#                     connection_manager_instance.close_connections()
