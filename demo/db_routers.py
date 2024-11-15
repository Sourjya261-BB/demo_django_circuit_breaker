import os
from django.conf import settings
from bb_async.thread_locals import get_x_tenant_id
from bb_python_django_common.middleware.threadlocals import get_replica_name


def get_x_tenant_id_or_default():
    return get_x_tenant_id() or int(os.getenv('DEFAULT_TENANT_ID', "1"))


class DBRouter:
    def __init__(self, db_type):
        db_configuration = settings.DB_ROUTER_CONFIGURATION.get(db_type)
        self.route_app_labels = db_configuration.get('route_apps')
        self.db_name = db_configuration.get('db_name')
        self.related_db = db_configuration.get('related_db')
        self.has_replica = db_configuration.get('has_replica')

    def db_for_read(self, model, **hints):
        tenant_id = get_x_tenant_id_or_default()
        db_type = self.get_db_type()
        if model._meta.app_label in self.route_app_labels:
            return f"{tenant_id}-{db_type}"

    def db_for_write(self, model, **hints):
        tenant_id = get_x_tenant_id_or_default()
        db_type = self.get_db_type()
        if model._meta.app_label in self.route_app_labels:
            return f"{tenant_id}-{db_type}"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        tenant_id = get_x_tenant_id_or_default()
        db_type = self.get_db_type()
        app_router_relations = {f"{tenant_id}-{self.related_db}", }
        db_set = {
            f"{tenant_id}-{db_type}",
            *app_router_relations,
        }
        return obj1._state.db in db_set and obj2._state.db in db_set

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        tenant_id = get_x_tenant_id_or_default()
        db_type = self.get_db_type()
        if app_label in self.route_app_labels:
            return f"{tenant_id}-{db_type}"

    def get_db_type(self):
        if self.has_replica:
            return get_replica_name() or self.db_name
        return self.db_name


DATABASE_ROUTERS = list()
for key in settings.DB_ROUTER_CONFIGURATION.keys():
    DATABASE_ROUTERS.insert(0, DBRouter(key))
