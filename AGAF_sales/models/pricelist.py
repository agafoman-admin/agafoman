# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    material_line_ids = fields.One2many('pricelist.materials', 'pricelist_id', string='Materials')
    equipment_line_ids = fields.One2many('pricelist.equipments', 'pricelist_id', string='Equipments')
    labour_line_ids = fields.One2many('pricelist.labours', 'pricelist_id', string='Labours')

    def update_value(self):
        for boq_product in self.item_ids:
                bom = self.env['mrp.bom'].search([('product_tmpl_id','=',boq_product.product_tmpl_id.id)])
                if bom:
                    material_total = 0
                    labour_total = 0
                    equipment_total = 0
                    total = 0
                    for components in bom.bom_line_ids:
                        material = self.env['pricelist.materials'].search([('pricelist_id','=',self.id),('product_tmpl_id','=',components.product_id.id)])
                        if material:
                            material_total += material.cost_price * components.product_qty
                            total += material.cost_price * components.product_qty
                        labour = self.env['pricelist.labours'].search([('pricelist_id', '=', self.id), ('product_tmpl_id', '=', components.product_id.id)])
                        if labour:
                            labour_total += labour.cost_price * components.product_qty
                            total += labour.cost_price * components.product_qty
                        equipment = self.env['pricelist.equipments'].search([('pricelist_id', '=', self.id), ('product_tmpl_id', '=', components.product_id.id)])
                        if equipment:
                            equipment_total += equipment.cost_price * components.product_qty
                            total += equipment.cost_price * components.product_qty
                    self.write({'item_ids':[(1, boq_product.id, { 'fixed_price':total })]})

    def add_components(self):
        material_list = []
        equipments_list = []
        labour_list = []
        self.material_line_ids.unlink()
        self.equipment_line_ids.unlink()
        self.labour_line_ids.unlink()
        for pricelist in self.item_ids:
            bom = self.env['mrp.bom'].search([('product_tmpl_id','=',pricelist.product_tmpl_id.id)])
            if bom:
                for components in bom.bom_line_ids:
                    if components.product_id.is_material:
                        material_list.append(components)
                    if components.product_id.is_labour:
                        labour_list.append(components)
                    if components.product_id.is_equipment:
                        equipments_list.append(components)

        if len(material_list) >= 1:
            for material in material_list:
                old_product_id = self.env['pricelist.materials'].search([('product_tmpl_id','=',material.product_id.id),('pricelist_id','=',self.id)])
                if old_product_id:
                    old_product_id.product_qty += material.product_qty
                else:
                    self.write({'material_line_ids': [(0, 0, {
                        'product_tmpl_id': material.product_id.id,
                        'product_qty': material.product_qty,
                        'cost_price': material.cost_price,
                    })]})
        if len(labour_list) >= 1:
            for labour in labour_list:
                old_labour_id = self.env['pricelist.labours'].search(
                    [('product_tmpl_id', '=', labour.product_id.id), ('pricelist_id', '=', self.id)])
                if old_labour_id:
                    old_labour_id.product_qty += labour.product_qty
                else:
                    self.write({'labour_line_ids': [(0, 0, {
                        'product_tmpl_id': labour.product_id.id,
                        'product_qty': labour.product_qty,
                        'cost_price': labour.cost_price,
                    })]})
        if len(equipments_list) >= 1:
            for equipment in equipments_list:
                old_equipment_id = self.env['pricelist.equipments'].search(
                    [('product_tmpl_id', '=', equipment.product_id.id), ('pricelist_id', '=', self.id)])
                if old_equipment_id:
                    old_equipment_id.product_qty += material.product_qty
                else:
                    self.write({'equipment_line_ids': [(0, 0, {
                        'product_tmpl_id': equipment.product_id.id,
                        'product_qty': equipment.product_qty,
                        'cost_price': equipment.cost_price,
                    })]})

    # def write(self,vals):
        # res = super(ProductPricelist, self).write(vals)
        # print("-=-=vals",vals)
        # product_id = vals.get('item_ids')[0][2].get('product_tmpl_id')
        # return res

    # While delete the line it gives the errors as well not able to add the another line
    # @api.onchange('item_ids')
    # def set_price_and_qty(self):
    #     for data in self._origin.item_ids:
    #         boq_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', data.product_tmpl_id.id)])
    #         self._origin.write({'material_line_ids':(1, data, {'min_quantity': boq_id.product_qty,'fixed_price': boq_id.boq_price})})
    #         print('test',boq_id.boq_price)


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_boq', '=', True)]",
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product Variant",
        ondelete='cascade', check_company=True,
        domain="[('is_boq', '=', True)]",
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    min_quantity = fields.Float(
        string="Min. Quantity",
        default=1,
        digits='Product Unit Of Measure',
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")


    # @api.onchange('product_tmpl_id')
    # @api.depends('product_tmpl_id')
    # def set_qty_and_price(self):
    #     for data in self:
    #         boq_id = self.env['mrp.bom'].search([('product_id','=',data.product_tmpl_id.id)])
    #         for boq in boq_id:
    #             data.min_quantity = boq.product_qty
    #             data.fixed_price = boq.boq_price


    def unlink(self):
        for data in self:
            boq_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', data.product_tmpl_id.id)])
            for boq_material in boq_id.bom_line_ids:
                if boq_material.product_id.is_material:
                    for pricelist_material in data.pricelist_id.material_line_ids:
                        if pricelist_material.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_material.product_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_material.sudo().unlink()
                            else:
                                pricelist_material.update({'product_qty': qty})
                elif boq_material.product_id.is_labour:
                    for pricelist_labour in data.pricelist_id.labour_line_ids:
                        if pricelist_labour.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_labour.product_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_labour.sudo().unlink()
                            else:
                                pricelist_labour.update({'product_qty': qty})
                elif boq_material.product_id.is_equipment:
                    for pricelist_equipment in data.pricelist_id.equipment_line_ids:
                        if pricelist_equipment.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_equipment.product_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_equipment.unlink()
                            else:
                                pricelist_equipment.update({'product_qty': qty})

        return super(ProductPricelistItem, self).unlink()


class PricelistMaterials(models.Model):
    _name = 'pricelist.materials'

    company_id = fields.Many2one('res.company', string="Company")
    product_tmpl_id = fields.Many2one('product.product', string="Products", domain="[('is_material', '=', True)]")
    # product_id = fields.Many2one('product.product', string="Variants", domain="[('is_material', '=', True)]")
    product_qty = fields.Float("Quantity", readonly=False)
    cost_price = fields.Float(string="Cost", readonly=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    @api.onchange('product_tmpl_id')
    def set_product_tmpl_price(self):
        for data in self:
            if data.product_tmpl_id:
                data.cost_price = data.product_tmpl_id.standard_price


class PricelistLabours(models.Model):
    _name = 'pricelist.labours'

    company_id = fields.Many2one('res.company', string="Company")
    product_tmpl_id = fields.Many2one('product.product', string="Products", domain="[('is_labour', '=', True)]")
    # product_id = fields.Many2one('product.product', string="Variants", domain="[('is_material', '=', True)]")
    product_qty = fields.Float("Quantity", readonly=False)
    cost_price = fields.Float(string="Cost", readonly=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    @api.onchange('product_tmpl_id')
    def set_product_tmpl_price(self):
        for data in self:
            if data.product_tmpl_id:
                data.cost_price = data.product_tmpl_id.standard_price


class PricelistEquipments(models.Model):
    _name = 'pricelist.equipments'

    company_id = fields.Many2one('res.company', string="Company")
    product_tmpl_id = fields.Many2one('product.product', string="Products", domain="[('is_equipment', '=', True)]")
    # product_id = fields.Many2one('product.product', string="Variants", domain="[('is_material', '=', True)]")
    product_qty = fields.Float("Quantity", readonly=False)
    cost_price = fields.Float(string="Cost", readonly=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    @api.onchange('product_tmpl_id')
    def set_product_tmpl_price(self):
        for data in self:
            if data.product_tmpl_id:
                data.cost_price = data.product_tmpl_id.standard_price