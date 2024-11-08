For DB connection:
```sudo docker run --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=test_db -p 5432:5432 -d postgres:13.5-alpine```
The way I tested it was - 
- Ran a series of queries using ```test_breaker.py``` and in the moddle of the execution changed working query with a faulty ```views.py```
- Observed the change in the state of the breaker and the connection address
![image](https://github.com/user-attachments/assets/c6aedae6-c198-46af-90dc-b4e1d1394b28)
![image](https://github.com/user-attachments/assets/5670cc5b-2e06-4714-8e1c-a0d4ecc97e14)

I was not able to find good documentation for the implementation of pool refresh in django and circuit_breaker options were limited. In this implementation pybreaker was used. Please let me your suggestions in this regard. 


