from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    phase_id = fields.Many2one('project.phase', string="Phase")
    project_id = fields.Many2one("project.project", string="Project")
    is_subcontracting_po = fields.Boolean("Is Subcontracting PO", readonly=1, store=True)


class MyWizard(models.TransientModel):
    _name = 'agaf.po_wizard'

    name = fields.Char(string='Name')
    partner_id = fields.Many2one('res.partner', string="Subcontractor", domain=[('supplier_rank','>=',1)])

    def button_confirm(self):
        list = []
        phase_id = self.env['project.phase'].browse(self.env.context.get('active_ids'))
        boq_line_id = self.env['boq.details.phase'].browse(self.env.context.get('default_boq_line_ids'))
        if boq_line_id:
            for boq in boq_line_id:
                list.append((0, 0, {
                    'product_id': boq.product_id.id,
                    'product_qty': boq.product_uom_qty,
                }))
                boq_line_id.is_already_po = True
            po_id = self.env['purchase.order'].create({
                'phase_id': phase_id.id,
                'project_id': phase_id.project_id.id,
                'partner_id': self.partner_id.id,
                'is_subcontracting_po':True,
                'order_line': list,
            })
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Purchase Order Created',
                    'type': 'rainbow_man',
                }
            }
        else:
            raise UserError(_("Purchase Order is already created."))
        return {'type': 'ir.actions.act_window_close'}

