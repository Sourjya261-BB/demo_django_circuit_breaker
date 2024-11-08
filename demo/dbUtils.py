from django.db import connections,OperationalError, DatabaseError
import pybreaker

def refresh_tenant_secrets(tenant_id):
    print(f"{tenant_id}: refresh_secrets")

DEFAULT_PK_QUERY = "select id from %s where %s = %s;"
FAILURE_THRESHOLD = 10
RECOVERY_TIMEOUT = 30

tenant_circuit_breakers = {}

def get_circuit_breaker(tenant_id):
    if tenant_id not in tenant_circuit_breakers:
        circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=FAILURE_THRESHOLD,
            reset_timeout=RECOVERY_TIMEOUT,
            listeners=[CircuitBreakerListener(tenant_id)]
        )
        tenant_circuit_breakers[tenant_id] = circuit_breaker
    return tenant_circuit_breakers[tenant_id]

class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    # def state_change(self, cb, old_state, new_state):
    #     if new_state == "open" and old_state in ["closed", "half-open"]:
    #         refresh_tenant_secrets(self.tenant_id)
    #         print(f"Circuit breaker state changed for tenant {self.tenant_id}: {old_state} -> {new_state}")
    def state_change(self, cb, old_state, new_state):
        try:
            print(f"State change detected for tenant {self.tenant_id}: {old_state.name} -> {new_state.name}")
            if new_state == "open" and old_state in ["closed", "half-open"]:
                refresh_tenant_secrets(self.tenant_id)
                print(f"Circuit breaker state changed for tenant {self.tenant_id}: {old_state} -> {new_state.name}")
        except Exception as e:
            print(f"Error in state change for tenant {self.tenant_id}: {e}")

class GenericDBUtils:
    def __init__(self, tenant_id=None):
        tenant_id = tenant_id
        self.tenant_id = tenant_id
        self.circuit_breaker = get_circuit_breaker(tenant_id)
        self.connection = connections["default"]
        self.cursor = self.connection.cursor()

    

    def execute_query_with_circuit_breaker(self, query_fn, *args, **kwargs):
            try:
                print(f"\n\ncircuit is: {self.circuit_breaker.current_state}\n\n")
                print(f"Connection address for tenant {self.tenant_id}: {id(self.connection)}")
                return self.circuit_breaker.call(query_fn, *args, **kwargs)
            except pybreaker.CircuitBreakerError:
                print(f"Execution blocked for tenant {self.tenant_id} due to open circuit.")
                return None
            except Exception as e:
                print(f"Execution failed for tenant {self.tenant_id}: {e}")
                raise

    def execute_raw_query(self, query):
        return self.execute_query_with_circuit_breaker(self.cursor.execute, query)

    def execute_ref_pk_query(self, query, target_table, target_ref_column, ref_data):
        query = query or DEFAULT_PK_QUERY
        ref_data = (type(ref_data) is int and ref_data) or ("'%s'" % ref_data)
        query = query % (target_table, target_ref_column, ref_data)
        return self.execute_raw_query(query)

    def get_ref_pk(self, query, target_table, target_ref_column, ref_data):
        self.execute_ref_pk_query(query, target_table, target_ref_column, ref_data)
        result = self.cursor.fetchone()
        return result and result[0]

    def get_ref_pks(self, query, target_table, target_ref_column, ref_data):
        self.execute_ref_pk_query(query, target_table, target_ref_column, ref_data)
        result = self.cursor.fetchall()
        return result and list(map(lambda x: x[0], result))

    def fetch_first(self, query):
        return self.execute_query_with_circuit_breaker(self.cursor.fetchone)

    def fetch_first_row(self, query):
        return self.execute_query_with_circuit_breaker(self.cursor.fetchone)

    def fetch_all(self, query):
        return self.execute_query_with_circuit_breaker(self.cursor.fetchall)

    def fetch_all_rows(self, query):
        return self.execute_query_with_circuit_breaker(self.cursor.fetchall)
