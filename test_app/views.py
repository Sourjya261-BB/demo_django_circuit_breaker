from django.shortcuts import render
from django.http import HttpResponse
from .models import Person
from demo.dbUtils import GenericDBUtils

# def get_all_users(request):
#     users = Person.objects.all()
#     user_names = ",".join([user.first_name for user in users])
#     print(users)
#     return HttpResponse(f"All User-Emails: {user_names}")

def get_all_users(request):
    # Instantiate GenericDBUtils for tenant 1 (replace with appropriate tenant ID if needed)
    db_utils = GenericDBUtils(tenant_id=1)

    # Example query to fetch all records from the "Person" table
    query = "SELECT first_name FROM test_app_person;"
    
    # Execute the query using db_utils
    db_utils.execute_raw_query(query)
    result = db_utils.fetch_all(query)

    # Process the results to create a response
    user_names = ",".join([row[0] for row in result]) if result else "No users found"
    print(result)  # Print the result for debugging purposes
    
    return HttpResponse(f"All User Names: {user_names}")