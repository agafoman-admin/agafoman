from odoo import models, fields, api, _
import datetime
import base64
from odoo.exceptions import ValidationError, RedirectWarning, UserError
import json
from datetime import datetime
import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero
from odoo.tools import date_utils
import io
import json
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

from datetime import datetime, timedelta
from collections import defaultdict


class VendorComparison(models.Model):

    _name = 'vendor.comparison'

    requester_types = fields.Many2one(
        'vendor.comparison.number', string='Vendor Reference Number', required=True)

    def vendor_all_details(self):

        purchase_order = self.env['purchase.order'].search(
            [('comparison_refs', '=', self.requester_types.id)])
        if purchase_order:
            purchase = []
            for m in purchase_order:
                purchase.append(m.id)
            partner_amount = []
            for amount in purchase_order:
                partner_amount.append(
                    {'partner_amounts': amount.amount_total, 'partner_value': amount.partner_id.name})

            purchase_id = self.env['purchase.order.line'].search_read([('order_id', '=', purchase)], fields=[

                'product_id', 'product_qty', 'product_uom', 'partner_id', 'price_unit', 'create_date', 'name'])
            val = []
            for j in purchase_id:
                val.append(j['name'])
            duplicate = list(set(val))
            # raise ValidationError(duplicate)
            datewise = self.env['purchase.order.line'].search([('name', '=', duplicate), (
                'order_id.state', '=', 'purchase')], order='id desc', limit=len(duplicate))
            date_record = []
            for date in datewise:
                date_record.append({'product_name': date.name,
                                   'price_rate': date.price_unit, 'create_date': date.create_date})

            purchase_date_wise = self.env['purchase.order.line'].search_read(
                [('name', '=', duplicate), ('order_id.state', '=', 'purchase')], fields=['product_id', 'price_unit', 'name'],)
            purchase_low_price = []
            for dates in purchase_date_wise:
                product = dates['name']
                price = dates['price_unit']
                date_value = {
                    'product': product,
                    'price': price,
                }

                purchase_low_price.append(date_value)
            # raise ValidationError(date_record)
            product_code = self.env['product.product'].search(
                [('name', '=', duplicate)])
            prod_code = []
            for code in product_code:
                prod_code.append(
                    {'code': code.default_code})
            # raise ValidationError(prod_code)
# Create a dictionary to store the lowest prices for each product
            lowest_prices = {}

            # Iterate through the data and update the lowest prices in the dictionary
            for item in purchase_low_price:
                product = item['product']
                price = item['price']
                if product not in lowest_prices or price < lowest_prices[product]:
                    lowest_prices[product] = price

            # Convert the dictionary back to a list of unique products with their lowest prices
            result = [{'product': product, 'price': price}
                      for product, price in lowest_prices.items()]
            # raise ValidationError(result)
            main = []
            purchase_ids = self.env['purchase.order.line'].search([('order_id','=',purchase)])
            for k in purchase_ids:
                main.append({'product_id':k.name,
                             'product_qty':k.product_qty,
                             'product_uom':k.product_uom.name,
                             'partner_id':k.partner_id.name,
                             'price_unit':k.price_unit,
                             'code':k.product_id.default_code})
                # product_id = k['name']
                # product_qty = k['product_qty']
                # product_uom = k['product_uom'][1]
                # partner_id = k['partner_id'][1]
                # pricr_unit = k['price_unit']
                # create_dates = k['create_date']
                # data = {
                #     'product_id': product_id,
                #     'product_qty': product_qty,
                #     'product_uom': product_uom,
                #     'partner_id': partner_id,
                #     'price_unit': pricr_unit,
                #     'create_date': create_dates,
                # }
                # main.append(data)
            # raise ValidationError(main)
            
            options = {
                'main': main,
                'purchase_low_price': result,
                'partner_amount': partner_amount,
                'date_record': date_record,
                'product_code': prod_code
            }

            

            return {
                'type': 'ir.actions.report',
                'data': {'model': 'vendor.comparison',
                         'options': json.dumps(options,
                                               default=date_utils.json_default),
                         'output_format': 'xlsx',
                         'report_name': 'Excel Report',
                         },
                'report_type': 'xlsx',
            }
        else:
            raise ValidationError('There is no purchase order')

    def get_xlsx_report(self, main, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        bold_format = workbook.add_format(
            {'font_size': 12, 'align': 'center', 'bold': True})
        cell_format = workbook.add_format(
            {'font_size': '12px', 'align': 'center'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px', })
        row_height = 30  # Adjust this value as needed to make the text visible
        sheet.set_row(0, row_height)  # Set the row height for the first row
        sheet.set_row(1, row_height)
        txt = workbook.add_format({'font_size': '10px', 'align': 'center'})
        sheet.merge_range('G2:M2', 'Vendor Comparison Report', head)
        unique_qty_values = set(entry['partner_id'] for entry in main['main'])
        columns = ['Sl No','Material', 'UOM', 'Qty']

        unique_products = []
        seen_product_ids = set()
        for entry in main['main']:
            product_id = entry['product_id']
            if product_id not in seen_product_ids:
                seen_product_ids.add(product_id)
                unique_products.append(entry)
        col_num = 4
        value = list(unique_qty_values)
        for partner_id in value:
            sheet.merge_range(3, col_num, 3, col_num +
                              1, partner_id, bold_format)
            col_num += 2
            sheet.write(4, col_num - 2, 'Unit Rate', cell_format)
            sheet.write(4, col_num - 1, 'Total', cell_format)

        compartive = ['Comparative Low Price']
        for low_price in compartive:
            sheet.merge_range(3, col_num, 3, col_num +
                              1, low_price, bold_format)
            col_num += 2
            sheet.write(4, col_num - 2, 'Unit Rate', cell_format)
            sheet.write(4, col_num - 1, 'Total', cell_format)
        last_purchase = ['Last Purchase Rate']
        for last in last_purchase:
            sheet.merge_range(3, col_num, 3, col_num + 1, last, bold_format)
            col_num += 2
            sheet.write(4, col_num - 2, 'Unit Rate', cell_format)
            sheet.write(4, col_num - 1, 'Total', cell_format)
        purchase_low_prices = ['Purchase Low Price']
        for low in purchase_low_prices:
            sheet.merge_range(3, col_num, 3, col_num + 1, low, bold_format)
            col_num += 2
            sheet.write(4, col_num - 2, 'Unit Rate', cell_format)
            sheet.write(4, col_num - 1, 'Total', cell_format)

        for col_num, column_name in enumerate(columns, start=0):
            sheet.write(3, col_num, column_name, bold_format)
        # sheet.write(4, 1, 'Code')
        row_num = 5
        data_by_product_partner = {}
        for entry in main['main']:
            product_id = entry['product_id']
            partner_id = entry['partner_id']
            if (product_id, partner_id) not in data_by_product_partner:
                data_by_product_partner[(product_id, partner_id)] = []
            data_by_product_partner[(product_id, partner_id)].append(entry)
        last_purchase_rate_sum = 0
        compartive_low_price = 0

        sub_total = 0
        lowest_total_sum = 0
        partner_amounts = {}
        # valu=[]
        # row_num += 1
        # for n in main['product_code']:
        #     sheet.write(row_num +1,1, n['code'], cell_format)

            
            # print(row_num,col_num)
        for sl_no, data_entry, in enumerate(unique_products, start=1):
            sheet.write(row_num, 0, sl_no, cell_format)
            # sheet.write(row_num, 1, data_entry['code'], cell_format)
            print(data_entry['code'])
            sheet.write(row_num, 1, data_entry['product_id'], cell_format)
            sheet.write(row_num, 2, data_entry['product_uom'], cell_format)
            sheet.write(row_num, 3, data_entry['product_qty'], cell_format)
            col_num = 4
            lowest_price = float('inf')
            lowest_total = float('inf')
            lowest_last_price = float('inf')
            lowest_total_last = float('inf')
            lowest_prices = float('inf')
            lowest_totals = float('inf')
            if main['purchase_low_price']:
                for purchase_order in main['purchase_low_price']:
                    if (purchase_order['product'] == data_entry['product_id']):
                        purchase_price = purchase_order['price']
                        if purchase_price < lowest_price:
                            lowest_prices = purchase_price
                            qty = data_entry['product_qty']
                            lowest_totals = qty * lowest_prices
            else:
                lowest_prices = 0
                lowest_totals = 0
            if main['date_record']:
                for datewise in main['date_record']:
                    if (datewise['product_name'] == data_entry['product_id']):
                        purchase_price_last = datewise['price_rate']
                        if purchase_price_last < lowest_price:
                            lowest_last_price = purchase_price_last
                            qty = data_entry['product_qty']
                            lowest_total_last = qty * lowest_last_price
            else:
                lowest_last_price = 0
                lowest_total_last = 0
            for partner_id in value:
                product_partner_key = (data_entry['product_id'], partner_id)
                partner_data = data_by_product_partner.get(
                    product_partner_key, [])
                for data in partner_data:

                    sheet.write(row_num, col_num,
                                data['price_unit'], cell_format)
                    qty = data_entry['product_qty']
                    unit_rate = data['price_unit']
                    subtotal = qty * unit_rate
                    if unit_rate < lowest_price:
                        lowest_price = unit_rate
                        lowest_price_partner = partner_id
                    if subtotal < lowest_total:
                        lowest_total = subtotal

                    col_num += 2
                sheet.write(row_num, col_num - 1, subtotal, cell_format)
                # print(col_num,row_num)
            sheet.write(row_num, col_num + 0, lowest_price, cell_format)
            sheet.write(row_num, col_num + 1, lowest_total, cell_format)
            sheet.write(row_num, col_num + 2, lowest_last_price, cell_format)
            sheet.write(row_num, col_num + 3, lowest_total_last, cell_format)
            sheet.write(row_num, col_num + 4, lowest_prices, cell_format)
            sheet.write(row_num, col_num + 5, lowest_totals, cell_format)
            last_purchase_rate_sum += lowest_totals
            compartive_low_price += lowest_total
            sub_total += subtotal
            lowest_total_sum += lowest_total_last
            row_num += 1

        sheet.write(row_num, 1, '', cell_format)  # Blank space
        row_num += 1
        sheet.merge_range(row_num, 0, row_num, 3, 'Total Amount', bold_format)
        sheet.write(row_num, col_num + 5, last_purchase_rate_sum, cell_format)
        sheet.write(row_num, col_num + 1, compartive_low_price, cell_format)
        # print(col_num,row_num)
        for partner_ids in value:
            product_partner_key = (data_entry['product_id'], partner_ids)
            partner_data = data_by_product_partner.get(product_partner_key, [])
            partner_amount = 0  # Initialize partner_amount to 0 for each partner
            if main['partner_amount']:
                for k in main['partner_amount']:
                    if k['partner_value'] == partner_ids:
                        # Add partner_amounts to the total for this partner
                        partner_amount += k['partner_amounts']
                partner_amounts[partner_ids] = partner_amount
        r = row_num - 4
        for partner_ids in value:
            sheet.write(row_num, r, partner_amounts.get(
                partner_ids, 0), cell_format)
            r += 2
        sheet.write(row_num, col_num + 3, lowest_total_sum, cell_format)
        row_num += 1
        sheet.merge_range(row_num, 0, row_num, 3,
                          'Difference amount w.r.t Low price', bold_format)
        sheet.write(row_num, col_num + 3, last_purchase_rate_sum -
                    lowest_total_sum, cell_format)
        sheet.write(row_num, col_num + 5, lowest_total_sum -
                    last_purchase_rate_sum, cell_format)
        s = row_num - 5
        for partner_ids in value:
            # dina = partner_amounts.get(partner_ids, 0) -100
            sheet.write(row_num, s, partner_amounts.get(
                partner_ids, 0)-last_purchase_rate_sum, cell_format)
            s += 2
            # print(last_purchase_rate_sum,'==========')
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
