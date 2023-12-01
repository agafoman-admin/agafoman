# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date


class MaterialRequisitionSlip(models.Model):
    _name = 'material.requisition.slip'

    name = fields.Char("MRS No.", copy=False, required=True, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('material.requisition.slip'), tracking=True)
    department_id = fields.Many2one('hr.department', string="Department",
                                    readonly=True,
                                    copy=False)
    project_id = fields.Many2one('project.project', string="Project", copy=False)
    request_date = fields.Date("Request Date", default=date.today())
    requestor_name = fields.Many2one("res.users", default=lambda self: self.env.user, string="Requestor Name", copy=False, readonly=1)
    project_manager_id = fields.Many2one(related="project_id.user_id", string="Project Manager")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, copy=False, readonly=True)
    slip_line_ids = fields.One2many("material.requisition.slip.line", "slip_id",
                                    string="Material Requisition Slip Line", copy=False)
    trail_ids = fields.One2many("audit.trail", "slip_id",
                                    string="Audit Trail", copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting_for_approval', 'Waiting For Approval'), ('approved', 'Approved'),
         ('rejected', 'Reject')], string="State", readonly=True, copy=False, index=True, default='draft')
    reject_reason = fields.Text('Reject Reason', copy=False)
    requested_by = fields.Many2one('res.users', string="Requested By")
    requested_comments = fields.Char("Requested Comments")
    approved_by = fields.Many2one('res.users', string="Approved By")
    approved_date = fields.Datetime("Approved Date")
    task_id = fields.Many2one('project.task', string="Task")
    phase_id = fields.Many2one(related="task_id.phase_id", string="Phase")
    department_id = fields.Many2one('hr.department', string="Department",
                                    default=lambda self: self.env.user.employee_id.department_id.id, readonly=True,
                                    copy=False)



    def action_rejected(self):
        self.write({'trail_ids': [(0, 0, {
            'date': datetime.now(),
            'author_id': self.env.user.id,
            'to_stage': 'rejected',
            'remark': "Rejected By " + self.env.user.name,
        })]})
        return {
            'name': _('Reject Reason'),
            'view_mode': 'form',
            'res_model': 'slip.reject.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': self.env.ref('AGAF_Project.slip_reject_reason_wizard').id,
            'context': {'default_slip_id': self.id},
        }

    def action_waiting_for_approval(self):
        self.state = 'waiting_for_approval'
        self.write({'trail_ids':[(0, 0, {
            'date': datetime.now(),
            'author_id': self.env.user.id,
            'to_stage': 'waiting_for_approval',
            'remark': "Updated By   " + self.env.user.name})],
            'requested_by': self.env.user.id,
            })

    def action_approved(self):
        self.state = 'approved'
        self.write({'trail_ids': [(0, 0, {
            'date': datetime.now(),
            'author_id': self.env.user.id,
            'to_stage': 'approved',
            'remark': "Approved By" + self.env.user.name,
        })],
            'approved_by': self.env.user.id,
            'approved_date': datetime.now(),
            })


class MaterialRequisitionSlipLine(models.Model):
    _name = 'material.requisition.slip.line'

    slip_id = fields.Many2one('material.requisition.slip', string="Slip")
    product_id = fields.Many2one('product.product', string="Name")
    product_qty = fields.Float("Qty",default=1)
    rate = fields.Float("Rate")
    amount = fields.Float("Amount")
    uom_id = fields.Many2one('uom.uom', string='UOM')
    sr_no = fields.Integer("S. No.", compute="_sequence_ref",readonly=False)
    price_unit = fields.Float("Price")

    def _sequence_ref(self):
        no = 0
        for line in self:
            no += 1
            line.sr_no = no


class AuditTrail(models.Model):
    _name = 'audit.trail'

    slip_id = fields.Many2one('material.requisition.slip', string="Slip")
    date = fields.Datetime("Date")
    author_id = fields.Many2one("res.users",string="Author")
    to_stage = fields.Selection(
        [('draft', 'Draft'), ('waiting_for_approval', 'Waiting For Approval'), ('approved', 'Approved'),
         ('rejected', 'Reject')], string="State", readonly=True, copy=False, index=True)
    remark = fields.Char("Remark")


class SlipRejectReasonWizard(models.TransientModel):
    _name = 'slip.reject.reason.wizard'

    slip_id = fields.Many2one('material.requisition.slip')
    reason = fields.Text('Reject Reason', required=True)


    def add_reject_reason(self):
        slip_id = self.env['material.requisition.slip'].search([('id','=',self._context.get('active_id'))])
        slip_id.reject_reason = self.reason
        slip_id.state = 'rejected'
        return {'type': 'ir.actions.act_window_close'}