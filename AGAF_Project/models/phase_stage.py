# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date


class PhaseStage(models.Model):
    _name = 'phase.stage'

    name = fields.Char("Name")
    description = fields.Char("Description")


class PhaseStageTemplate(models.Model):
    _name = 'phase.stage.template'

    name = fields.Char("Template Name")
    stage_ids = fields.Many2many("phase.stage", string="Phase Stages")
    description = fields.Char("Description")



