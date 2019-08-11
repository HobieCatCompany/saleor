import datetime
import cStringIO
import csv

from ..order.models import Order, OrderLine

def export_orders_ready_to_fulfill_to_csv():

    output = cStringIO.StringIO()
    writer = csv.writer(output)

    orders = Order.objects.ready_to_fulfill.all()

    for order in orders:
        for order_line in order.line_set.all():
            writer.writerow(create_csv_row(order, order_line))

    return output.getvalue()

def create_csv_row(order, order_line):
    return [
        order.id,
        'ECOMSA', #Customer Number
        '001', #Warehouse Code
        order.id, #Purchase Order Number
        datetime.date.today().strftime('%m/%d/%Y'), #Order Date
        datetime.date.today().strftime('%m/%d/%Y'), #Requested Ship Date
        '09', #Payment terms - 09 - Credit Card
        {'Standard Ground': 'FGP', 'Express': 'F3P'}[order.shipping_method.name],
        '', #Ship To Code
        order.billing_address.full_name,
        'RES', #Tax Schedule
        1, #MAS Line Type
        order_line.product_sku,
        order_line.quantity,
        order_line.unit_price_gross,
        order_line.quantity * order_line.unit_price_gross,
        '', #Comment
        order.user_email,
        order.billing_address.full_name,
        order.billing_address.street_address_1,
        order.billing_address.street_address_2,
        order.billing_address.city,
        order.billing_address.country_area,
        order.billing_address.postal_code,
        order.billing_address.country.code,
        order.shipping_address.full_name,
        order.shipping_address.street_address_1,
        order.shipping_address.street_address_2,
        order.shipping_address.city,
        order.shipping_address.country_area,
        order.shipping_address.country_area,
        order.shipping_address.country.code  
    ]