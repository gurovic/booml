from django.http import JsonResponse

def start_api(request):
    return JsonResponse({"message": "OK"})
