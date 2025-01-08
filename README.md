# Circuit Breaker Testing with Database Instances

This document explains the testing process and results for the sliding window-based circuit breaker implementation. The test involved two PostgreSQL database instances with different configurations and aimed to evaluate the circuit breaker's ability to handle failures and refresh database configurations dynamically.

## Database Setup

### Instance 1
Command to run:
```bash
sudo docker run --name postgres_1 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=test_db -p 5000:5432 -d postgres:13.5-alpine
```
- **Port**: 5000
- **Table**: `test_app_users` with columns:
  - `first_name`
  - `last_name`

### Instance 2
Command to run:
```bash
sudo docker run --name postgres_2 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=test_db -p 5432:5432 -d postgres:13.5-alpine
```
- **Port**: 5432
- **Table**: None

## Testing Process

### Initial Configuration
The initial database configuration for `tenant_id 1` was:

```python
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
```

### Steps
1. **Run `test_app.py`**: This script queries the `test_app_users` table for tenant 1 using the initial configuration.
   - As the table does not exist in the first instance, the query throws an error.
   - The circuit breaker tracks consecutive failures.

2. **Circuit Breaker Transition**:
   - Upon breaching the failure threshold, the circuit breaker transitions to the **open** state.
   - This triggers a database pool refresh, updating the configuration for tenant 1.

3. **Updated Configuration**:
   The `update_db_config_for_tenant` function updates the database configuration to:
   ```python
   DATABASES = {
       '1-default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'postgres',
           'USER': 'postgres',
           'PASSWORD': '1234',
           'HOST': 'localhost',
           'PORT': '5000',
       }
   }
   ```
   This points to the second instance, where the table exists.

4. **Run `test_breaker.py`**: Queries were sent to the `test_app_users` table after the configuration update.
   - On reaching the failure threshold, the circuit breaker transitioned back to the **closed** state after successful queries.

## Results
- **Sequential Circuit Breaker**:
  - Worked as expected but lacks thread safety.
- **Aggregator Circuit Breaker**:
  - Successfully handled multiple threads and ensured consistency.
  - Recommended for production use due to thread safety.

## Observations
- The circuit breaker effectively handled failures and dynamically updated the database configurations.
- The transition states (**closed**, **open**, **half-open**) were correctly triggered based on the error threshold and timeout.
- The aggregator circuit breaker implementation is preferred for its thread safety in multi-threaded environments.

## Notes
- The database pool refresh was verified by observing a change in the connection address.
- Ensure that proper thresholds and timeout values are configured based on the application's requirements.44
  
## Snapshots
![image](https://github.com/user-attachments/assets/fe96712d-260d-4d65-a1a3-e83341047459)
![image](https://github.com/user-attachments/assets/1717d4b6-4cc1-4491-801a-1f7139da59a7)


