# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_site_location = fields.Boolean("Site Location?", default=False)
    is_replace_location = fields.Boolean("Reservation Location?")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet")