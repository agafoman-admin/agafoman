from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError


import json
from odoo import http
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class PurchaseOrder_inherit(models.Model):

    _inherit = 'purchase.order'

    comparison_refs = fields.Many2one('vendor.comparison.number',string='Comparison Reference No.',required=True)


    # @api.depends("name", "comparison_ref")
    # def name_get(self):
    #     def name(r):
    #         return r.comparison_ref

    #     return [(r.id, name(r)) for r in self]
    
class vendor_comparison_number(models.Model):
    _name = 'vendor.comparison.number'
    _rec_name = 'name'
    
    name = fields.Char('Vendor Comparison Number')

    @api.model
    def create(self, values):
        check = self.search([('name','=',values.get('name'))])
        if check:
            raise ValidationError('Please give unique number')
        else:
            pass
        return super(vendor_comparison_number, self).create(values)

