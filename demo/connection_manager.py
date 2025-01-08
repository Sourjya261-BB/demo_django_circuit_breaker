from demo.circuit_breaker.aggregator_circuit_breaker import CircuitBreaker,CircuitBreakerListener
from mysql.connector import pooling
from psycopg2_pool import ConnectionPool
from mysql.connector.errors import DatabaseError, OperationalError, InterfaceError, ProgrammingError
from psycopg2 import OperationalError as Psycopg2OperationalError, InterfaceError as Psycopg2InterfaceError, DatabaseError as Psycopg2DatabaseError
from .config_fetcher import update_db_config_for_tenant

included_exceptions = [DatabaseError, OperationalError, InterfaceError, ProgrammingError,Psycopg2OperationalError, Psycopg2InterfaceError, Psycopg2DatabaseError]

class Listener(CircuitBreakerListener):
    def __init__(self, connection_manager, db_name, metadata):
        """
        Listener to handle state changes and update metadata on pool refresh.
        """
        self.connection_manager = connection_manager
        self.db_name = db_name
        self.metadata = metadata  # Shared state for communication

    def state_change(self, cb, old_state, new_state):
        """
        Detects state transitions and refreshes connection pool when moving from CLOSED to OPEN.
        """
        print(f"[Listener] Circuit Breaker for {self.db_name} transitioned from {old_state.name} to {new_state.name}")
        if old_state.name == "closed" and new_state.name == "open":
            # print(f"[Listener] Circuit Breaker for {self.db_name} transitioned to OPEN from CLOSED")
            if self.connection_manager.refresh_pool(self.db_name):
                print(f"[Listener] Connection pool for {self.db_name} refreshed.")
                self.metadata["refresh_pool"] = True
            else:
                print(f"[Listener] Failed to refresh connection pool for {self.db_name}.")
                self.metadata["refresh_pool"] = False


class MyCircuitBreaker(CircuitBreaker):
    def __init__(self, name, failure_threshold, recovery_timeout,connection_manager,db_name):
        self.metadata = {"refresh_pool": False}
        super().__init__(
            name = name,
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            include=included_exceptions ,
            listeners=[Listener(connection_manager,db_name,self.metadata)]
        )

# breaker  = MyCircuitBreaker(failure_threshold=10,recovery_timeout=30)
# state = breaker.state
# print(state)

class ConnectionManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, databases):
        if not hasattr(self, "initialized"):
            self.databases = databases
            self.connections = {}
            for db_name, config in databases.items():
                self._initialize_connection(db_name, config)
            self.initialized = True

    def _initialize_connection(self, db_name, config):
        db_engine = config['ENGINE']
        failure_threshold = config.get('FAILURE_THRESHOLD', 10)
        recovery_timeout = config.get('RECOVERY_TIMEOUT', 20)

        # If we already have a circuit breaker for this connection, preserve its state
        existing_circuit_breaker = None
        if db_name in self.connections:
            existing_circuit_breaker = self.connections[db_name].get("circuit_breaker")

        # Only create a new circuit breaker if we don't have an existing one
        if existing_circuit_breaker is None:
            circuit_breaker = MyCircuitBreaker(
                name = f"{db_name}",
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                connection_manager=self,
                db_name=db_name
            )
        else:
            circuit_breaker = existing_circuit_breaker

        try:
            if "mysql" in db_engine:
                dbconfig = {
                    "host": config['HOST'],
                    "port": config['PORT'],
                    "user": config['USER'],
                    "password": config['PASSWORD'],
                    "database": config['NAME'],
                }
                pool = pooling.MySQLConnectionPool(
                    pool_size=config.get('POOL_SIZE', 10),
                    pool_name=db_name,
                    pool_reset_session=True,
                    **dbconfig
                )
            elif "postgres" in db_engine:
                dbconfig = {
                    'dbname': config['NAME'],
                    'user': config['USER'],
                    'password': config['PASSWORD'],
                    'port': config['PORT'],
                    'host': config['HOST']
                }
                pool = ConnectionPool(
                    minconn=5,
                    maxconn=config.get('POOL_SIZE', 10),
                    **dbconfig
                )
            else:
                raise ValueError(f"Unsupported database type: {db_engine}")

            # Store or update the pool and circuit breaker
            self.connections[db_name] = {
                "pool": pool,
                "circuit_breaker": circuit_breaker
            }
            print(f"pool created for {db_name}")

        except Exception as e:
            # If pool creation fails and we're refreshing, maintain the circuit breaker's state
            if existing_circuit_breaker:
                self.connections[db_name] = {
                    "pool": None,
                    "circuit_breaker": existing_circuit_breaker
                }
            raise ConnectionError(f"Failed to create connection pool for {db_name}: {e}")

    def get_connection_with_circuit(self, db_name):
        """
        Get the connection pool and circuit breaker for the specified database name.
        """
        if db_name not in self.connections:
            raise ValueError(f"Connection pool for {db_name} not initialized.")

        connection_data = self.connections[db_name]
        # print(f"Providing Connection from pool {db_name}")
        return connection_data["pool"], connection_data["circuit_breaker"]

    def release_connection(self, db_name, conn):
        """
        Release a connection back to the pool.
        """
        if db_name in self.connections:
            pool = self.connections[db_name]["pool"]
            # Release connection back to the pool based on its type
            if isinstance(pool, pooling.MySQLConnectionPool):
                # print(f"release connection with address {conn.address} to pool {db_name}")
                conn.close()  # For MySQL, close releases it back to the pool
            elif isinstance(pool, ConnectionPool):
                pool.putconn(conn)

    def close_connections(self):
        """
        Closes all connections in all pools.
        """
        for conn_data in self.connections.values():
            pool = conn_data["pool"]
            if isinstance(pool, pooling.MySQLConnectionPool):
                pass  # MySQL connection pools clean up connections on deletion
            elif isinstance(pool, ConnectionPool):
                # pool.closeall()
                pass

    def refresh_pool(self, db_name):
        """
        Refreshes the connection pool while preserving circuit breaker state.
        """
        if db_name in self.connections:
            tenant_id, db_type = db_name.split('-', 1)
            try:
                # Update the database config
                self.databases = update_db_config_for_tenant(tenant_id)
                updated_config = self.databases[db_name]

                # Initialize new connection while preserving circuit breaker state
                self._initialize_connection(db_name, updated_config)
                return True
            except Exception as e:
                # print(f"Failed to refresh pool for {db_name}: {e}")
                return False
        return False