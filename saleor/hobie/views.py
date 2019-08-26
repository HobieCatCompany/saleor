from django.http import Http404, HttpResponse
from .utils import export_orders_ready_to_fulfill_to_csv

def export_orders_to_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment;filename="hobie_cat_orders.csv"'
    response.content = export_orders_ready_to_fulfill_to_csv()      

    if len(response.content) == 0:
        raise Http404

    return response