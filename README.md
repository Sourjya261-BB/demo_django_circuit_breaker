For DB connection:
```sudo docker run --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=test_db -p 5432:5432 -d postgres:13.5-alpine```
then create table ```test_app_users``` with columns ```first_name``` and ```last_name```
The way I tested it was - 
- Initially the config fetcher returns config for tenant_id 1 as follows:
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
update_db_config_for_tenant funtion updates db_config to
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

here the port is 5000, however the ostgres container exposes port 5432
- Ran a series of queries using ```test_breaker.py```  to the ```test_app_users``` after starting the server.
- Following the breach of ```error_count``` threshold for the circuit_breaker for tenant 1 the circuit_breaker changed state from ```closed``` to ```open``` leading to pool refresh (verified by the change in the connection aaddress) and the updation of db_config for that particular tenant.

![image](https://github.com/user-attachments/assets/0e3abe99-5f7b-444f-9359-fdaf15cf45b8)


There is however some issue with the breaker logic. I havent been able to find good documentation for circuitbreakers in python. Here the issue is that the cb changes state form open to closed instantly (I mean in the next request it changes state from open to closed regardless of the relaxation time) i.e half open funtionality is never executed. The change in state does however trigger the pool refresh logic which works fine.


