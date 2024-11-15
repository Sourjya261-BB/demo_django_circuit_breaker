# import datetime
# import json
# import os
# from uuid import uuid4
#
# from bb_python_secrets_manager.awssecurity.secretsmanager import SecretManager
# from bb_python_django_common.httpclient.httpclient import Communication
# from bb_python_django_common.middleware.threadlocals import set_x_project
# from bb_python_django_common.constants import DEFAULT_TENANT_ID
#
# from bb_async.suicideutils import SuicideHandler
#
# suicide_handler = SuicideHandler()
# suicide_handler.set_suicide_time()
# suicide_handler.start_suicide_timer()
#
# service_name = os.environ['SERVICE_NAME']
# x_project = os.environ.get("X_PROJECT")
# config_svc_url = f"{os.environ['CONFIG_SERVICE_DOMAIN']}/config_svc/internal/v1/global/service/"
# headers = {
#     "X-Caller": service_name,
#     "X-Timestamp": datetime.datetime.now().__str__(),
#     "X-Entry-Context-Id": "1",
#     "X-Entry-Context": "b2c",
#     "X-Tracker": uuid4().__str__()
# }
# x_project and set_x_project(x_project)
#
# local_mode = os.environ.get("LOCAL_MODE", '')
# if local_mode.lower() == "true":
#     service_tenant_settings = json.loads(os.environ.get("INFRA_CONFIG", "{}"))
# else:
#     service_tenant_settings = Communication(
#         config_svc_url, "get",
#         params={"service_slug": service_name},
#         headers=headers,
#         log_tag="Startup"
#     ).response.json()
#
# DATABASES = {}
# AEROSPIKE_CONFIG = {}
# BROKERS_CONFIG = {}
# S3_CONFIGS = {}
# OAUTH_CONFIGS = {}
# CONFIG_MAPS = {}
# SECRET_MAPS = {}
# TENANT_NAMES = {}
# CIRCUIT_BREAKER_CONFIG = {}
#
#
# def update_db_config_for_tenant(tenant_id, tenant_config=None):
#     """
#     Sets up database configuration for a tenant, including loading secrets if required.
#     If tenant_config is not provided, re-fetches the configuration for the specified tenant_id.
#     """
#     # If tenant_config is not provided, fetch the latest configuration from the config service
#     if tenant_config is None:
#         service_tenant_settings = Communication(
#             config_svc_url, "get",
#             params={"service_slug": service_name},
#             headers=headers,
#             log_tag="RefreshTenantConfig"
#         ).response.json()
#         tenant_config = service_tenant_settings['config_json'].get(str(tenant_id))
#
#     if not tenant_config:
#         raise ValueError(f"No configuration found for tenant_id {tenant_id}")
#
#     # Update circuit breaker configuration for the tenant
#     CIRCUIT_BREAKER_CONFIG[tenant_id] = {
#         "FAILURE_THRESHOLD": tenant_config.get("circuitBreakerFailureThreshold", 10),
#         "RECOVERY_TIMEOUT": tenant_config.get("circuitBreakerRecoveryTimeout", 30),
#     }
#     aws_region = tenant_config.get("awsRegion")
#
#     # Update database configuration if present
#     if tenant_config.get("db"):
#         for db_type, db_config in tenant_config["db"].items():
#             final_db_config = db_config.copy()
#             if db_config.get("secretManager"):
#                 # Retrieve database secrets from AWS Secrets Manager
#                 db_secrets = SecretManager(db_config["secretManager"], region_name=aws_region).secrets
#                 final_db_config.update({
#                     "USER": db_secrets['username'],
#                     "PASSWORD": db_secrets['password'],
#                     "HOST": db_secrets['host'],
#                     "PORT": db_secrets['port']
#                 })
#                 final_db_config.pop("secretManager", None)
#
#             # Update the DATABASES dictionary
#             DATABASES[f"{tenant_id}-{db_type}"] = final_db_config
#             if tenant_id == DEFAULT_TENANT_ID and db_type == "default":
#                 DATABASES["default"] = final_db_config
#     return DATABASES
#
#
#
# # Main script loop for handling all configurations
# for tenant_id, tenant_config in service_tenant_settings['config_json'].items():
#     tenant_id = int(tenant_id)
#     aws_region = tenant_config.get("awsRegion")
#
#     # Update tenant names and circuit breaker configuration
#     TENANT_NAMES[tenant_id] = tenant_config.get("slug")
#     # Update database configurations for the tenant
#     update_db_config_for_tenant(tenant_id, tenant_config)
#
#     # Update cache configuration
#     if tenant_config.get("cache"):
#         cache_config = tenant_config["cache"].copy()
#         if cache_config.get("secretManager"):
#             cache_secrets = SecretManager(cache_config["secretManager"], region_name=aws_region).secrets
#             cache_config.update({
#                 "user": cache_secrets['username'],
#                 "password": cache_secrets['password'],
#                 "hosts": cache_secrets['hosts'],
#                 "port": cache_secrets['port'],
#                 "tls-name": cache_secrets['tls-name'],
#                 "certificate": cache_secrets['certificate']
#             })
#             cache_config.pop("secretManager", None)
#         AEROSPIKE_CONFIG[tenant_id] = cache_config
#
#     # Update other configurations
#     BROKERS_CONFIG[tenant_id] = tenant_config.get("kafka", {})
#     S3_CONFIGS[tenant_id] = tenant_config.get("s3", {})
#     OAUTH_CONFIGS[tenant_id] = tenant_config.get("oauth", {})
#     CONFIG_MAPS[tenant_id] = tenant_config.get("configMap", {})
#
#     # Secret map configuration
#     if tenant_config.get("secretMap"):
#         SECRET_MAPS[tenant_id] = tenant_config["secretMap"]
#         if "secretManager" in tenant_config["secretMap"]:
#             db_secrets = SecretManager(tenant_config["secretMap"]["secretManager"], region_name=aws_region).secrets
#             SECRET_MAPS[tenant_id] = db_secrets
# #-----------------------------------------------------------------
## -----------For testing-------------------------------------------
DATABASES = {
        '1-default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '1234',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
service_tenant_settings  = {
'config_json':{
        '1': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '1234',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
}
def update_db_config_for_tenant(tenant_id, tenant_config=None):
    if tenant_config is None:
        tenant_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',
            'USER': 'postgres',
            'PASSWORD': '1234',
            'HOST': 'localhost',
            'PORT': '5000',
        }
    else:
        tenant_config=tenant_config
    DATABASES[f"{tenant_id}-default"]=tenant_config
    return DATABASES

