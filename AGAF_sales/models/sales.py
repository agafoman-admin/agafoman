# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class Product(models.Model):
    _inherit = "product.template"

    is_material = fields.Boolean("Material")
    is_labour = fields.Boolean("Labour")
    is_equipment = fields.Boolean("Equipment")
    is_boq = fields.Boolean("BOQ")
    
    


class ProductVariant(models.Model):
    _inherit = "product.product"
    _inherits = {'product.template': 'product_tmpl_id'}


    def bom_compute_func(self):
    # Find all records with is_boq=True
        boq_records = self.search([('is_boq', '=', True)])
        for record in boq_records:
            record.button_bom_cost()

class MrpBom(models.Model):
    _inherit = "mrp.bom"

    boq_price = fields.Float(string="Total BOQ", copy=False,compute='calculate_material_cost')
    # boq_price = fields.Float(string="Total BOQ", copy=False)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True, index=True,
        domain="[('type', 'in', ['product', 'consu','service']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True)
    
    @api.model_create_multi
    def create(self, vals):
        res = super(MrpBom, self).create(vals)

        if vals[0].get('product_tmpl_id'):
            product_tmpl_id = self.env['product.template'].browse(vals[0].get('product_tmpl_id'))
            product_tmpl_id.is_boq = True
        if vals[0].get('product_id'):
            product_id = self.env['product.product'].browse(vals[0].get('product_id'))
            product_id.is_boq = True
        return res

    
    @api.depends('bom_line_ids')
    @api.onchange('bom_line_ids')
    def calculate_material_cost(self):
        for line in self:
            total_material_cost = 0.0
            if line.bom_line_ids:
                for lines in line.bom_line_ids:
                    total_material_cost += lines.cost_price * lines.product_qty

                line.boq_price = total_material_cost
            else:
                line.boq_price = total_material_cost



class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    cost_price = fields.Float(related="product_id.standard_price", string="Cost")
    sales_price = fields.Float(related="product_id.list_price", string="Sales Price")
    total_price = fields.Float(string="Total Price",compute='calculate_total_amount')
    product_id = fields.Many2one('product.product', 'Component', required=True, check_company=True, domain="['|','|',('is_material', '=', True),('is_labour', '=', True),('is_equipment', '=', True)]")
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id',
                                      store=True, index=True, domain="['|','|',('is_material', '=', True),('is_labour', '=', True),('is_equipment', '=', True)]",)

    @api.depends('cost_price', 'product_qty')
    @api.onchange('cost_price', 'product_qty')
    def calculate_total_amount(self):
        test = 0
        for data in self:
            data.total_price = data.cost_price * data.product_qty
            test += data.cost_price * data.product_qty
        self.bom_id.boq_price = test



