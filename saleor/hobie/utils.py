import datetime
from io import StringIO
import csv

from ..order.models import Order, OrderLine
from .models import ExportedOrder

def get_freight_order_line_dict(freight_amount):
    return {'line_type':5, 'item_code':'/FECOM', 'quantity':0, 'unit_price':0, 'extended_amount':freight_amount, 'sales_gl_account':'4200-595', 'cost_gl_account':''}

def get_tax_order_line_dict(tax_amount):
    return {'line_type':5, 'item_code':'/AVATAX', 'quantity':0, 'unit_price':0, 'extended_amount':tax_amount, 'sales_gl_account':'2170-505', 'cost_gl_account':''}

def get_item_order_line_dict(order_line):
    return {'line_type':1, 'item_code':order_line.product_sku, 'quantity':order_line.quantity, 'unit_price':order_line.unit_price_net.amount, 'extended_amount':order_line.get_total().net.amount, 'sales_gl_account':'4000-190', 'cost_gl_account':'4100-190'}


def export_orders_ready_to_fulfill_to_csv():

    output = StringIO()
    writer = csv.writer(output)

    orders = Order.objects.ready_to_capture().all()

    previously_exported_order_ids = list(ExportedOrder.objects.values_list('id', flat=True).order_by('id'))

    for order in orders:
        if not order.id in previously_exported_order_ids:
            for order_line in order.lines.all():
                writer.writerow(create_csv_row(order, get_item_order_line_dict(order_line)))
            writer.writerow(create_csv_row(order, get_freight_order_line_dict(order.shipping_price_net.amount)))
            writer.writerow(create_csv_row(order, get_tax_order_line_dict(order.total.tax.amount)))
            ExportedOrder.objects.create(order_id=order.id)

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
        ('ECS','ECE')["Express" in order.shipping_method.name], #EMS is a dummy value, of sorts
        '', #Ship To Code
        order.billing_address.full_name,
        'ECOM', #Tax Schedule
        order_line['line_type'], #MAS Line Type
        order_line['item_code'],
        order_line['quantity'],
        order_line['unit_price'],
        order_line['extended_amount'],
        '', #Comment
        order_line['sales_gl_account'], #Sales G/L Account
        order_line['cost_gl_account'], #Cost G/L Account
        order.user_email,
        order.billing_address.full_name,
        order.billing_address.street_address_1,
        order.billing_address.street_address_2,
        order.billing_address.postal_code,
        order.billing_address.city,
        order.billing_address.country_area,
        order.billing_address.country.code,
        order.shipping_address.full_name,
        order.shipping_address.street_address_1,
        order.shipping_address.street_address_2,
        order.shipping_address.postal_code,
        order.shipping_address.city,
        order.shipping_address.country_area,
        order.shipping_address.country.code,
    ]