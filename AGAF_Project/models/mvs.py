# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date


class MaterialIssueVoucher(models.Model):
    _name = 'material.issue.voucher'

    name = fields.Char("MIV No.", copy=False, required=True, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('material.issue.voucher'), tracking=True)
    mrs_no = fields.Many2one('material.requisition.slip', string="MRS No.", domain=[('state','=','approved')])
    department_id = fields.Many2one(related="mrs_no.department_id", string="Department",
                                    copy=False)
    project_id = fields.Many2one(related="mrs_no.project_id", string="Project", copy=False)
    issued_date = fields.Date("Issue Date", default=date.today())
    requestor_name = fields.Many2one(related="mrs_no.requestor_name", string="Requestor Name")
    company_id = fields.Many2one(related='mrs_no.company_id', string="Company", copy=False)
    slip_line_ids = fields.One2many("material.issue.voucher.line", "slip_id",
                                    string="Material Transfer Sheet Line", copy=False, force_save=True)
    trail_ids = fields.One2many("transfer.audit.trail", "slip_id",
                                    string="Audit Trail", copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting_for_approval', 'Waiting For Approval'), ('approved', 'Approved'),
         ('rejected', 'Reject')], string="State", readonly=True, copy=False, index=True, default='draft')
    reject_reason = fields.Text('Reject Reason', copy=False)
    requested_by = fields.Many2one('res.users', string="Requested By", copy=False)
    requested_comments = fields.Char("Requested Comments", copy=False)
    approved_by = fields.Many2one('res.users', string="Approved By", copy=False)
    approved_date = fields.Datetime("Approved Date", copy=False)
    location_id = fields.Many2one('stock.location', string='From Location', domain="[('usage', '=', 'internal')]")
    location_dest_id = fields.Many2one('stock.location', string='To Location', domain="[('is_site_location', '=', True),('usage', '=', 'internal')]")
    requested_for = fields.Char("Requested for")
    task_id = fields.Many2one(related="mrs_no.task_id", string="Task")
    phase_id = fields.Many2one(related="task_id.phase_id", string="Phase")

    # @api.onchange('location_id')
    # @api.depends('location_id')
    # def check_available_qty(self):
    #     print("0-0--=-=-=-=",self._origin.location_id.name, self.location_id.name)
    #
    #     return

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('material.issue.voucher')
        vals['trail_ids'] = [(0, 0, {
                'date': datetime.now(),
                'author_id': self.env.user.id,
                'to_stage': 'draft',
                'remark': "Created By "+self.env.user.name,
            })]
        list = []
        project_task_obj = self.env['material.requisition.slip'].search([('id', '=', vals.get('mrs_no'))])
        material_estimate_obj = project_task_obj.slip_line_ids

        for line in material_estimate_obj:
            if vals.get('location_id'):
                stock_quant = self.env['stock.quant'].search([('product_id', '=',line.product_id.id),('location_id','=',vals.get('location_id'))])
                if stock_quant:
                    qty = stock_quant.quantity
                else:
                    qty = 0
            list.append((0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'available_qty': qty,
                'allocated_qty': 0,
                'uom_id': line.uom_id.id,
                'rate':line.rate,
            }))
        vals['slip_line_ids'] = list
        return super(MaterialIssueVoucher, self).create(vals)



    def write(self, vals):
        super(MaterialIssueVoucher, self).write(vals)
        if vals.get('mrs_no'):
            self.slip_line_ids.unlink()
            test = []
            # Search from different fields and add requisition depending on search
            # result
            project_task_obj = self.env['material.requisition.slip'].search(
                [('id', '=', self.mrs_no.id)])
            material_estimate_obj = project_task_obj.slip_line_ids

            for line in material_estimate_obj:
                test.append((0, 0, {
                    'slip_id':self.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'allocated_qty': 0,
                    'uom_id': line.uom_id.id,
                    'rate':line.price_unit,
                }))
            self.update({'slip_line_ids':test})
        if vals.get('location_id'):
            for data in self.slip_line_ids:
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', data.product_id.id), ('location_id', '=', vals.get('location_id'))])
                if stock_quant:
                    qty = stock_quant.quantity
                else:
                    qty = 0
                self.write({'slip_line_ids': [(1, data.id, {'available_qty': qty,'allocated_qty': 0})]})



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
            'res_model': 'transfer.reject.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': self.env.ref('AGAF_Project.transfer_reject_reason_wizard').id,
            'context': {'default_slip_id': self.id},
        }

    def action_waiting_for_approval(self):
        for rec in self.slip_line_ids:
            if rec.allocated_qty == 0 or rec.allocated_qty > rec.product_qty:
                raise UserError(_("Please Enter Valid Allocated Qty"))
            available_stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', rec.product_id.id), ('quantity', '>=', rec.allocated_qty),
                 ('location_id', '=', self.location_id.id)])
            if not available_stock_quant:
                raise UserError(_("%s Product Stock is not available on %s Location." % (
                    rec.product_id.name, self.location_id.name)))
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
        for rec in self.slip_line_ids:
            available_stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', rec.product_id.id), ('quantity', '>=', rec.allocated_qty),
                 ('location_id', '=', self.location_id.id)])
            if available_stock_quant:
                stock_move_obj = self.env['stock.move'].create({
                    'origin': self.name,
                    'name': rec.product_id.name,
                    'product_id': rec.product_id.id,
                    'product_uom': rec.uom_id.id,
                    'product_uom_qty': rec.allocated_qty,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'quantity_done': rec.allocated_qty,
                })
                if stock_move_obj:
                    stock_move_obj._action_confirm()
                    stock_move_obj._action_assign()
                    stock_move_obj.write({'state': 'done'})
                location_ids = self.env['stock.quant'].search(
                    [('product_id.id', '=', rec.product_id.id), ('location_id', '=', self.location_id.id)])
                for product in location_ids:
                    product.sudo().reserved_quantity = product.reserved_quantity - (rec.allocated_qty)
                    product.sudo().quantity = product.quantity - rec.allocated_qty
                quants = self.env['stock.quant'].create({
                    'location_id': self.location_dest_id.id,
                    'product_id': rec.product_id.id,
                    'quantity': rec.allocated_qty
                })
                # quants.action_apply_inventory()
                # for product in quants:
                #     product.sudo().reserved_quantity = product.reserved_quantity - (rec.allocated_qty)
                #     product.sudo().quantity = product.quantity - rec.allocated_qty
            else:
                raise UserError(_("%s Product Stock is not available on %s Location." % (
                rec.product_id.name, self.location_id.name)))

        self.write({'trail_ids': [(0, 0, {
            'date': datetime.now(),
            'author_id': self.env.user.id,
            'to_stage': 'approved',
            'remark': "Approved By " + self.env.user.name,
        })],
            'approved_by': self.env.user.id,
            'approved_date': datetime.now(),
            })


class MaterialIssueVoucherLine(models.Model):
    _name = 'material.issue.voucher.line'

    slip_id = fields.Many2one('material.issue.voucher', string="Voucher")
    product_id = fields.Many2one('product.product', string="Name")
    product_qty = fields.Float("Requested Qty")
    allocated_qty = fields.Float("Allocated Qty")
    rate = fields.Float(related="product_id.standard_price",string="Rate")
    amount = fields.Float("Amount")
    uom_id = fields.Many2one('uom.uom', string='UOM')
    sr_no = fields.Integer("S. No.", compute="_sequence_ref")
    remark = fields.Text("Remarks")
    available_qty = fields.Float("Available Qty")





    def _sequence_ref(self):
        no = 0
        for line in self:
            no += 1
            line.sr_no = no


class TransferAuditTrail(models.Model):
    _name = 'transfer.audit.trail'

    slip_id = fields.Many2one('material.issue.voucher', string="Slip")
    date = fields.Datetime("Date")
    author_id = fields.Many2one("res.users",string="Author")
    to_stage = fields.Selection(
        [('draft', 'Draft'), ('waiting_for_approval', 'Waiting For Approval'), ('approved', 'Approved'),
         ('rejected', 'Reject')], string="State", readonly=True, copy=False, index=True)
    remark = fields.Char("Remark")


class TransferRejectReasonWizard(models.TransientModel):
    _name = 'transfer.reject.reason.wizard'

    slip_id = fields.Many2one('material.issue.voucher')
    reason = fields.Text('Reject Reason', required=True)


    def add_reject_reason(self):
        slip_id = self.env['material.issue.voucher'].search([('id','=',self._context.get('active_id'))])
        slip_id.reject_reason = self.reason
        slip_id.state = 'rejected'
        return {'type': 'ir.actions.act_window_close'}