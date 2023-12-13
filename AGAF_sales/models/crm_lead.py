# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    enquiry_type = fields.Selection([('bid','Bid'),('fixed','Fixed')], string="Enquiry Type")
    boq_detail_ids = fields.One2many('boq.details', 'lead_id', string="Boq Details")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")


    def get_estimation_work(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        list =[]
        if self.boq_detail_ids:
            for data in self.boq_detail_ids:
                if data.product_uom_qty == 0:
                    raise ValidationError('Please Enter Valid Quantity in BOQ Details.')
                list.append((0, 0, {
                    'product_tmpl_id': data.product_tmpl_id.id,
                    'description': data.description,
                    'product_uom_qty': data.product_uom_qty,
                    'uom_id': data.uom_id.id,
                    'fixed_price_unit': data.price_unit,
                    'price_unit': data.price_unit,
                    'work_type_id': data.work_type_id.id,
                    'price_subtotal': data.total,
                }))
        else:
            raise ValidationError('Please Enter BOQ details')
        vals = {
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'email_from':self.email_from,
            'phone': self.phone,
            'enquiry_type': self.enquiry_type,
            'date_deadline':self.date_deadline,
            'company_id': self.company_id.id or self.env.company.id,
            'user_id':  self.user_id.id,
            'boq_detail_ids': list,
        }
        estimate_id = self.env['estimation.works'].create(vals)
        self.write({'estimate_id': estimate_id.id})
        message = "Estimation Created Successfully."
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Estimation Created',
                'type': 'rainbow_man',
            }
        }
        # return {
        #     'name': 'Estimation Created',
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'popup.wizard.form',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {
        #         'default_name': message,
        #     },
        # }


class WorkType(models.Model):
    _name = 'work.type'

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)


class EstimatedBOQDetails(models.Model):
    _name = 'estimated.boq.details'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_boq', '=', True)]",
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    description = fields.Text(related="product_tmpl_id.description_sale", string="Description")
    product_uom_qty = fields.Float("Quantity")
    price_unit = fields.Float( string="Unit Price")
    fixed_price_unit = fields.Float(string=" Fixed Unit Price")
    uom_id = fields.Many2one(related="product_tmpl_id.uom_id", string="UoM")
    work_type_id = fields.Many2one('work.type', string="Work Type")
    # total = fields.Float("Total")
    lead_id = fields.Many2one("crm.lead", string="Lead")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")
    margin_pr = fields.Float("Margin(%)")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        store=True, readonly=False,
        check_company=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.estimate_id.company_id.currency_id.id)
    price_subtotal = fields.Monetary("Subtotal", compute='_compute_amount_all', store=True,
        currency_field='currency_id',)
    price_tax = fields.Float("Tax", compute='_compute_amount_all', store=True)
    price_total = fields.Monetary(compute='_compute_amount_all', string='Total', store=True)

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax'].sudo()._convert_to_tax_base_line_dict(
            self,
            partner=self.estimate_id.partner_id,
            currency=self.currency_id,
            # product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            price_subtotal=self.price_subtotal,
        )



    @api.depends('tax_id','price_subtotal','price_tax','price_unit','product_uom_qty')
    def _compute_amount_all(self):
        for line in self:
            tax_total = 0.0
            tax_amount = 0.0
            line.price_subtotal = line.price_unit * line.product_uom_qty
            if line.tax_id:
                for tax in line.tax_id:
                    tax_amount += (line.price_subtotal * tax.amount) / 100
            tax_total += tax_amount
            line.price_tax = tax_total
            line.price_total = tax_total +  line.price_subtotal

    # @api.depends('product_tmpl_id', 'product_uom_qty', 'price_unit')
    # def _compute_tax_id(self):
    #     for line in self:
    #         # Replace this logic with your own tax calculation logic
    #         # For example, you can fetch taxes based on product or location
    #         taxes = line.product_tmpl_id.taxes_id.filtered(lambda r: r.company_id == line.estimate_id.company_id)
    #         line.tax_id = taxes


    @api.depends('product_uom_qty', 'price_unit')
    @api.onchange('product_uom_qty', 'price_unit')
    def calculate_total(self):
        for data in self:
            data.price_unit = data.product_tmpl_id.standard_price
            data.fixed_price_unit = data.product_tmpl_id.standard_price
            data.price_subtotal = data.product_uom_qty * data.price_unit


class EstimatedBOQMaterialDetails(models.Model):
    _name = 'estimated.boq.material.details'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_material', '=', True)]",
        )
    description = fields.Text(related="product_tmpl_id.description_sale", string="Description")
    product_uom_qty = fields.Float("Quantity")
    fixed_price_unit = fields.Float( string="Unit Price")
    price_unit = fields.Float( string="Unit Price")
    uom_id = fields.Many2one(related="product_tmpl_id.uom_id", string="UoM")
    work_type_id = fields.Many2one('work.type', string="Work Type")
    total = fields.Float("Total")
    lead_id = fields.Many2one("crm.lead", string="Lead")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")
    margin_pr = fields.Float("Margin(%)")


class EstimatedBOQLabourDetails(models.Model):
    _name = 'estimated.boq.labour.details'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_labour', '=', True)]",
        )
    description = fields.Text(related="product_tmpl_id.description_sale", string="Description")
    product_uom_qty = fields.Float("Quantity")
    price_unit = fields.Float( string="Unit Price")
    fixed_price_unit = fields.Float(string="Unit Price")
    uom_id = fields.Many2one(related="product_tmpl_id.uom_id", string="UoM")
    work_type_id = fields.Many2one('work.type', string="Work Type")
    total = fields.Float("Total")
    lead_id = fields.Many2one("crm.lead", string="Lead")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")
    margin_pr = fields.Float("Margin(%)")


class EstimatedBOQEquipmentDetails(models.Model):
    _name = 'estimated.boq.equipment.details'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_labour', '=', True)]",
        )
    description = fields.Text(related="product_tmpl_id.description_sale", string="Description")
    product_uom_qty = fields.Float("Quantity")
    price_unit = fields.Float( string="Unit Price")
    fixed_price_unit = fields.Float(string="Unit Price")
    uom_id = fields.Many2one(related="product_tmpl_id.uom_id", string="UoM")
    work_type_id = fields.Many2one('work.type', string="Work Type")
    total = fields.Float("Total")
    lead_id = fields.Many2one("crm.lead", string="Lead")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")
    margin_pr = fields.Float("Margin(%)")



class BOQDetails(models.Model):
    _name = 'boq.details'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True,
        domain="[('is_boq', '=', True)]",
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    description = fields.Text(related="product_tmpl_id.description_sale", string="Description")
    product_uom_qty = fields.Float("Quantity", default=1)
    price_unit = fields.Float( string="Unit Price")
    uom_id = fields.Many2one(related="product_tmpl_id.uom_id", string="UoM")
    work_type_id = fields.Many2one('work.type', string="Work Type")
    total = fields.Float("Total")
    lead_id = fields.Many2one("crm.lead", string="Lead")
    estimate_id = fields.Many2one("estimation.works", string="Estimation")


    @api.depends('product_uom_qty','price_unit','product_tmpl_id')
    @api.onchange('product_uom_qty', 'price_unit','product_tmpl_id')
    def calculate_total(self):
        for data in self:
            data.price_unit = data.product_tmpl_id.standard_price
            data.total = data.product_uom_qty * data.price_unit


class EstimationWorks(models.Model):
    _name = 'estimation.works'
    _inherit = ['mail.thread', 'mail.activity.mixin', ]


    name = fields.Char("Name", default=lambda self: self.env['ir.sequence'].next_by_code('estimation.works'), tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")

    email_from = fields.Char(
        'Email', tracking=40, index='trigram',
        readonly=False, store=True)
    phone = fields.Char(
        'Phone', tracking=50,
        readonly=False, store=True)
    enquiry_type = fields.Selection([('bid','Bid'),('fixed','Fixed')], string="Enquiry Type")
    user_id = fields.Many2one(
        'res.users', string='Salesperson', default=lambda self: self.env.user,
        check_company=True, index=True, tracking=True)
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.", tracking=True)
    opportunity_id = fields.Many2one('crm.lead', 'Enquiry Ref.', index=True, ondelete='set null', readonly=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company, readonly=False, store=True, tracking=True)
    margin_pr = fields.Float("Margin(%)", tracking=True)
    boq_detail_ids = fields.One2many('estimated.boq.details', 'estimate_id', string="Boq Details", tracking=True)
    material_line_ids = fields.One2many('estimated.boq.material.details', 'estimate_id', string='Materials', tracking=True)
    equipment_line_ids = fields.One2many('estimated.boq.equipment.details', 'estimate_id', string='Equipments', tracking=True)
    labour_line_ids = fields.One2many('estimated.boq.labour.details', 'estimate_id', string='Labours', tracking=True)
    tax_totals = fields.Binary(exportable=False)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id, tracking=True)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', currency_field='currency_id')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', currency_field='currency_id')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True, currency_field='currency_id')
    material_total = fields.Monetary("Total Material Cost", compute="_compute_total_cost",  store=True, tracking=True)
    labour_total = fields.Monetary("Total Labour Cost", compute="_compute_total_cost",  store=True, tracking=True)
    equipment_total = fields.Monetary("Total Civil Works", compute="_compute_total_cost",  store=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('waiting_for_approval', 'Waiting For Approval'), ('quotation_created', 'Quotation Created'), ('reject', 'Reject'), ('cancel', 'Cancel')], string='Status', readonly=True, copy=False,
                             default='draft', tracking=True)
    quotation_id = fields.Many2one('sale.order', string="Quotation", copy=False, tracking=True)
    is_revise = fields.Boolean("Is Revise?", default=False)

    def action_internal_revised(self):
        self.state = 'draft'

    def action_revise(self):
        vals = {}
        boq_list = []
        if self.boq_detail_ids:
            for data in self.boq_detail_ids:
                boq_list.append((0, 0, {
                    'product_tmpl_id': data.product_tmpl_id.id,
                    'description': data.description,
                    'product_uom_qty': data.product_uom_qty,
                    'uom_id': data.uom_id.id,
                    'fixed_price_unit': data.price_unit,
                    'price_unit': data.price_unit,
                    'work_type_id': data.work_type_id.id,
                    'price_subtotal': data.price_subtotal,
                }))
        vals.update({
            'partner_id': self.partner_id.id,
            'email_from':self.email_from,
            'phone':self.phone,
            'company_id':self.company_id.id,
            'enquiry_type':self.enquiry_type,
            'user_id':self.user_id.id,
            'date_deadline':self.date_deadline,
            'opportunity_id':self.opportunity_id.id,
            'margin_pr':self.margin_pr,
            'boq_detail_ids':boq_list,
        })
        estimation_id = self.env['estimation.works'].create(vals)
        estimation_id.add_components()
        self.is_revise = True
        self.opportunity_id.write({"estimate_id":estimation_id.id})
        view_id = self.env.ref('AGAF_sales.estimation_works_form').id

        return {
            'name': 'Estimation',
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(view_id, 'form')],
            'res_model': 'estimation.works',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': estimation_id.id,
            'target': 'current',

        }



    def action_approved(self):
        self.ensure_one()
        list = []
        quotation_value = {
            'opportunity_id': self.opportunity_id.id,
            'estimation_id':self.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id or self.env.company.id,
            'user_id': self.user_id.id,
            'margin_pr':self.margin_pr,
        }
        order_id = self.env['sale.order'].create(quotation_value)
        if self.boq_detail_ids:
            for data in self.boq_detail_ids:
                list.append((0, 0, {
                    'product_template_id': data.product_tmpl_id.id,
                    'product_id':data.product_tmpl_id.product_variant_id.id,
                    'name': data.description or "",
                    'product_uom_qty': data.product_uom_qty,
                    'price_unit': data.price_unit,
                    'price_subtotal': data.price_subtotal,
                    'order_id': order_id.id,
                    'tax_id': [(6, 0, data.tax_id.ids)],
                    'work_type_id':data.work_type_id.id,
                    'customer_lead': 1.0,
                    'margin_pr':data.margin_pr,
                }))

        order_id.write({'order_line': list})
        self.quotation_id = order_id
        self.quotation_id.add_components()
        self.quotation_id.labour_total = 0
        self.quotation_id.material_total = 0
        labour_cost = 0
        equipment_cost = 0
        for estimation in self.quotation_id:
            if estimation.material_line_ids:
                for data in estimation.material_line_ids:
                    estimation.material_total += data.total
            if estimation.labour_line_ids:
                for labour in estimation.labour_line_ids:
                    labour_cost += labour.total
            if estimation.equipment_line_ids:
                for equipment in estimation.equipment_line_ids:
                    equipment_cost += equipment.total
        self.quotation_id.labour_total = labour_cost + equipment_cost
        self.state = 'quotation_created'
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Quotation Created',
                'type': 'rainbow_man',
            }
        }



    def _get_lead_quotation_domain(self):
        return [('state', 'in', ('draft', 'sent'))]

    def action_rejected(self):
        self.state = 'reject'

    def action_waiting_for_approval(self):
        self.state = 'waiting_for_approval'

    @api.depends('material_line_ids.price_unit','labour_line_ids.price_unit','equipment_line_ids.price_unit')
    def _compute_total_cost(self):
        for estimation in self:
            if estimation.material_line_ids:
                for data in estimation.material_line_ids:
                    estimation.material_total += data.total
            if estimation.labour_line_ids:
                for labour in estimation.labour_line_ids:
                    estimation.labour_total += labour.total
            if estimation.equipment_line_ids:
                for equipment in estimation.equipment_line_ids:
                    estimation.equipment_total += equipment.total


    @api.depends('boq_detail_ids.tax_id', 'boq_detail_ids.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.boq_detail_ids
            order.tax_totals = self.env['account.tax'].sudo()._prepare_tax_totals(
                [x.sudo()._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id,
            )

    @api.depends('boq_detail_ids.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.boq_detail_ids

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax


    def add_components(self):
        material_list = []
        new_material_list = []
        equipments_list = []
        new_equipments_list = []
        labour_list = []
        new_labour_list = []
        self.material_line_ids.unlink()
        self.equipment_line_ids.unlink()
        self.labour_line_ids.unlink()
        for pricelist in self.boq_detail_ids:
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
                    old_product_id = self.env['estimated.boq.material.details'].search([('product_tmpl_id','=',material.product_id.id),('estimate_id','=',self.id)])
                    # print("-=-=-=price/list.product_uom_qty",pricelist.product_uom_qty, material.product_id.name)
                    if old_product_id:
                        if material not in new_material_list:
                            old_product_id.product_uom_qty += material.product_qty*pricelist.product_uom_qty
                            old_product_id.total = old_product_id.product_uom_qty * material.cost_price
                    else:
                        if material not in new_material_list:
                            self.write({'material_line_ids': [(0, 0, {
                                'product_tmpl_id': material.product_id.id,
                                'product_uom_qty': material.product_qty*pricelist.product_uom_qty,
                                'price_unit': material.cost_price,
                                'fixed_price_unit': material.cost_price,
                                'total':(material.product_qty*pricelist.product_uom_qty)*material.cost_price,
                            })]})
                    new_material_list.append(material)
            if len(labour_list) >= 1:
                for labour in labour_list:
                    old_labour_id = self.env['estimated.boq.labour.details'].search(
                        [('product_tmpl_id', '=', labour.product_id.id), ('estimate_id', '=', self.id)])
                    if old_labour_id:
                        if labour not in new_labour_list:
                            old_labour_id.product_uom_qty += labour.product_qty * pricelist.product_uom_qty
                            old_labour_id.total = old_labour_id.product_uom_qty * labour.cost_price
                    else:
                        if labour not in new_labour_list:
                            self.write({'labour_line_ids': [(0, 0, {
                                'product_tmpl_id': labour.product_id.id,
                                'product_uom_qty': labour.product_qty*pricelist.product_uom_qty,
                                'price_unit': labour.cost_price,
                                'fixed_price_unit':labour.cost_price,
                                'total':(labour.product_qty*pricelist.product_uom_qty)*labour.cost_price,
                            })]})
                    new_labour_list.append(labour)
            if len(equipments_list) >= 1:
                for equipment in equipments_list:
                    old_equipment_id = self.env['estimated.boq.equipment.details'].search(
                        [('product_tmpl_id', '=', equipment.product_id.id), ('estimate_id', '=', self.id)])
                    if old_equipment_id:
                        if equipment not in new_equipments_list:
                            old_equipment_id.product_uom_qty += equipment.product_qty * pricelist.product_uom_qty
                            old_equipment_id.total = old_equipment_id.product_uom_qty * equipment.cost_price
                    else:
                        if equipment not in new_equipments_list:
                            self.write({'equipment_line_ids': [(0, 0, {
                                'product_tmpl_id': equipment.product_id.id,
                                'product_uom_qty': equipment.product_qty * pricelist.product_uom_qty,
                                'price_unit': equipment.cost_price,
                                'fixed_price_unit':equipment.cost_price,
                                'total': (equipment.product_qty * pricelist.product_uom_qty) * equipment.cost_price,
                            })]})
                    new_equipments_list.append(equipment)
        self.material_total = 0
        self.labour_total = 0
        self.equipment_total = 0
        for mat in self.material_line_ids:
            self.material_total += mat.total
        for lab in self.labour_line_ids:
            self.labour_total += lab.total
        for equ in self.equipment_line_ids:
            self.equipment_total += equ.total
        self.apply_margin()



    def apply_margin(self):
        for data in self:
            # if data.margin_pr:
                if data.boq_detail_ids:
                    for boq in data.boq_detail_ids:
                        # boq.tax_id = [(6, 0, boq.tax_id.ids)]
                        boq.margin_pr = data.margin_pr
                        boq.price_unit = (boq.fixed_price_unit * boq.margin_pr)+boq.fixed_price_unit
                        boq.price_subtotal = boq.price_unit * boq.product_uom_qty
                if data.material_line_ids:
                    for material in data.material_line_ids:
                        material.margin_pr = data.margin_pr
                        material.price_unit = (material.fixed_price_unit * material.margin_pr) + material.fixed_price_unit
                        material.total = material.price_unit * material.product_uom_qty
                if data.equipment_line_ids:
                    for equipment in data.equipment_line_ids:
                        equipment.margin_pr = data.margin_pr
                        equipment.price_unit = (equipment.fixed_price_unit * equipment.margin_pr)+equipment.fixed_price_unit
                        equipment.total = equipment.price_unit * equipment.product_uom_qty
                if data.labour_line_ids:
                    for labour in data.labour_line_ids:
                        labour.margin_pr = data.margin_pr
                        labour.price_unit = (labour.fixed_price_unit * labour.margin_pr) + labour.fixed_price_unit
                        labour.total = labour.price_unit * labour.product_uom_qty
        self.material_total = 0
        self.labour_total = 0
        self.equipment_total = 0
        for mat in self.material_line_ids:
            self.material_total += mat.total
        for lab in self.labour_line_ids:
            self.labour_total += lab.total
        for equ in self.equipment_line_ids:
            self.equipment_total += equ.total



# class PopupWizardForm(models.TransientModel):
#     _name = 'popup.wizard.form'
#
#     name = fields.Text("Name")


