# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    analytic_account_id = fields.Many2one('account.analytic.account', string="Project Account", copy=False,
                                          ondelete='cascade',
                                          domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                          check_company=True,
                                          required = True,
                                          help="Analytic account to which this project, its tasks and its timesheets are linked. \n"
                                               "Track the costs and revenues of your project by setting this analytic account on your related documents (e.g. sales orders, invoices, purchase orders, vendor bills, expenses etc.).\n"
                                               "This analytic account can be changed on each task individually if necessary.\n"
                                               "An analytic account is required in order to use timesheets.")
    project_rate = fields.Float("Project Rate")
    order_id = fields.Many2one('sale.order', string='Sale Order')