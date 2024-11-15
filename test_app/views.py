# views.py
from django.http import HttpResponse
from demo.dbUtils import GenericDBUtils
from .apps import connection_manager_instance

connection_manager = connection_manager_instance

def get_all_users(request):
    tenant_id = 1
    db_utils = GenericDBUtils(tenant_id=tenant_id, connection_manager=connection_manager)

    query = "SELECT first_name FROM test_app_user;"
    try:
        result = db_utils.fetch_all(query)
        user_names = ", ".join([row[0] for row in result]) if result else "No users found"
    except Exception as e:
        print(f"Error executing query: {e}")
        return HttpResponse("An error occurred while fetching users.", status=500)

    return HttpResponse(f"All User Names: {user_names}")
