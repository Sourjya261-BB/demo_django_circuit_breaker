from mysql.connector.pooling import MySQLConnectionPool
from psycopg2_pool import ConnectionPool
from demo.circuit_breaker.aggregator_circuit_breaker import CircuitBreakerError

DEFAULT_PK_QUERY = "select id from %s where %s = %s;"
def get_x_tenant_id():
    return None

class GenericDBUtils:
    def __init__(self, db_type="default", tenant_id=None,connection_manager=None):
        self.tenant_id = tenant_id or get_x_tenant_id()
        self.db_name = f"{self.tenant_id}-{db_type}"
        self.connection_manager = connection_manager
        if self.connection_manager:
            self.pool, self.circuit_breaker = self.connection_manager.get_connection_with_circuit(self.db_name)
        else:
            # This will only be used if the global connection_manager instance is not provided.
            from .connection_manager import ConnectionManager
            from .config_fetcher import DATABASES
            self.connection_manager = ConnectionManager(DATABASES)
            self.pool, self.circuit_breaker = self.connection_manager.get_connection_with_circuit(self.db_name)

    def _get_connection_and_cursor(self):
        """
        Retrieve a connection and cursor from the pool based on the database type.
        """
        if isinstance(self.pool, MySQLConnectionPool):
            connection = self.pool.get_connection()
        elif isinstance(self.pool, ConnectionPool):
            connection = self.pool.getconn()
        else:
            raise ValueError("Unsupported pool type")

        cursor = connection.cursor()
        print("got connection and cursor")
        return connection, cursor

    def _release_connection(self, connection):
        """
        Release the connection back to the pool.
        """
        self.connection_manager.release_connection(self.db_name, connection)

    def execute_raw_query(self, query):
        """
        Execute a raw SQL query within the circuit breaker context.
        """
        def _execute():
            # Get a connection and cursor
            connection, cursor = self._get_connection_and_cursor()
            print(f"in _execute: connection address: {id(connection)}")
            try:
                print(f"Executing query: {query}")
                cursor.execute(query)
                return connection, cursor
            except Exception as e:
                # Close cursor and release connection in case of execution failure
                cursor.close()
                self._release_connection(connection)
                raise e

        try:
            print(f"--|Current_State: {self.circuit_breaker.current_state}, Failure_count: {self.circuit_breaker.fail_counter},Fail_Max: {self.circuit_breaker.fail_max}|--")
            if self.circuit_breaker.metadata.get("refresh_pool"):
                print(f"Pool was refreshed for {self.db_name} during execution....")
                self.circuit_breaker.metadata["refresh_pool"] = False
                self.pool, _ = self.connection_manager.get_connection_with_circuit(self.db_name)
            connection, cursor = self.circuit_breaker.call(_execute)
            return connection, cursor
        except CircuitBreakerError as e:
            raise ConnectionError(f"Circuit breaker prevented execution: {e}")
        except Exception as e:
            raise ConnectionError(f"Error executing raw query: {e}")

    def execute_ref_pk_query(self, query, target_table, target_ref_column, ref_data):
        """
        Execute a query to fetch primary key references based on the target table and reference column.
        """
        query = query or DEFAULT_PK_QUERY
        ref_data = (type(ref_data) is int and ref_data) or ("'%s'" % ref_data)
        query = query % (target_table, target_ref_column, ref_data)
        return self.execute_raw_query(query)

    def get_ref_pk(self, query, target_table, target_ref_column, ref_data):
        """
        Fetch the first primary key reference.
        """
        connection,cursor = self.execute_ref_pk_query(query, target_table, target_ref_column, ref_data)
        try:
            result = cursor.fetchone()
            return result and result[0]
        finally:
            cursor.close()
            self._release_connection(connection)


    def get_ref_pks(self, query, target_table, target_ref_column, ref_data):
        """
        Fetch all primary key references.
        """
        connection,cursor= self.execute_ref_pk_query(query, target_table, target_ref_column, ref_data)
        try:
            result = cursor.fetchall()
            return result and [row[0] for row in result]
        finally:
            cursor.close()
            self._release_connection(connection)

    def fetch_first(self, query):
        """
        Fetch the first result of a query.
        """
        connection, cursor = self.execute_raw_query(query)
        try:
            result = cursor.fetchone()
            return result and result[0]
        finally:
            cursor.close()
            self._release_connection(connection)

    def fetch_first_row(self, query):
        """
        Fetch the first row of a query result.
        """
        connection, cursor = self.execute_raw_query(query)
        try:
            result = cursor.fetchone()
            return result
        finally:
            cursor.close()
            self._release_connection(connection)


    def fetch_all(self, query):
        """
        Fetch all results as a single-column list.
        """
        connection,cursor = self.execute_raw_query(query)
        # result = cursor.fetchall()
        # return [row[0] for row in result] if result else []
        try:
            result = cursor.fetchall()
            return [row[0] for row in result] if result else []
        finally:
            cursor.close()
            self._release_connection(connection)

    def fetch_all_rows(self, query):
        """
        Fetch all rows of a query result.
        """
        connection, cursor = self.execute_raw_query(query)
        try:
            result = cursor.fetchall()
            return result or []
        finally:
            cursor.close()
            self._release_connection(connection)


    def close(self):
        """
        Closes all pools and connections in the connection manager.
        """
        self.connection_manager.close_connections()
