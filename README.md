For DB connection:
```sudo docker run --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=test_db -p 5432:5432 -d postgres:13.5-alpine```
The way I tested it was - 
- Ran a series of queries using ```test_breaker.py``` and in the moddle of the execution changed working query with a faulty ```views.py```
- Observed the change in the state of the breaker and the connection address
