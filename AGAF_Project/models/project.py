from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class project_phase_task(models.Model):
    _name = 'project.phase'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, copy=False)
    project_id = fields.Many2one('project.project')
    assignees = fields.Many2one('res.users', string='Assignee')
    partner_id = fields.Many2one(related="project_id.partner_id", string='Customer')
    dead_line = fields.Date(string='Deadline')
    description = fields.Char()
    boq_line_ids = fields.One2many(
        'boq.details.phase', 'phase_id', string='Boq Details')
    material_line_ids = fields.One2many(
        'material.details.phase', 'phase_id', string='Material')
    labour_line_ids = fields.One2many(
        'labour.details.phase', 'phase_id', string='Labour')
    equipment_line_ids = fields.One2many(
        'equipment.details.phase', 'phase_id', string='Equipment')
    sale_id = fields.Many2one('sale.order', string='Sale Order')
    checking = fields.Boolean(string='checking')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    project_cost = fields.Float(related="project_id.project_rate", string="Project Cost")
    planned_material_cost = fields.Float(string="Planned Material Cost", compute="set_planned_material_cost")
    actual_material_cost = fields.Float("Actual Material Cost", compute="set_actual_material_cost")
    utilization_cost = fields.Float("Difference", compute="set_utilization_cost")

    @api.depends('planned_material_cost','actual_material_cost')
    def set_utilization_cost(self):
        for data in self:
            if data.actual_material_cost == 0:
                data.utilization_cost = 0
            else:
                data.utilization_cost = data.planned_material_cost - data.actual_material_cost

    @api.depends('actual_material_cost')
    def set_actual_material_cost(self):
        total = 0
        for data in self:
            voucher_ids = self.env['material.issue.voucher'].search([('project_id','=',data.project_id.id),('phase_id','=',data.id),('state','=','approved')])
            for voucher in voucher_ids:
                for material in voucher.slip_line_ids:
                    total += material.allocated_qty * material.rate
            data.actual_material_cost = total
        return

    @api.depends('planned_material_cost')
    def set_planned_material_cost(self):
        total = 0
        for data in self.material_line_ids:
             total += data.price_unit * data.product_uom_qty
        self.planned_material_cost = total

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['dynamic.stages'].search([])
        return stage_ids

    stage_id = fields.Many2one(
        'dynamic.stages', string="State", group_expand='_read_group_stage_ids')

    def button_purchase(self):
        project_task_id = self.env['project.task'].search(
            [('phase_id', '=', self._origin.id)])
        if project_task_id:
            return {
                'name': "Project Task",
                        'type': 'ir.actions.act_window',
                        'view_type': 'tree,form',
                        'view_mode': 'tree,form',
                        'res_model': 'project.task',
                        'domain': [('phase_id', '=', self._origin.id)],
                        'context': "{'create': False}"

            }
        else:
            return {
                'name': "Project Task",
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'project.task',
                        'context': {'default_phase_id': self._origin.id,
                                    'default_project_id': self.project_id.id}

            }

    def phase_create_task(self):
        return {
            'name': "Project Task",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task',
            'context': {'default_phase_id': self._origin.id,
                        'default_project_id': self.project_id.id}
        }

    def button_applicant_backend(self):
        return {
            'name': 'Project Task',
            'view_mode': 'tree,form',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'domain': [('phase_id', '=', self._origin.id)]}
    position_filled_count = fields.Integer(compute="_compute_applicant_count")

    def _compute_applicant_count(self):
        for res in self:
            total_len = len(self.env['project.task'].search(
                [('phase_id', '=', res._origin.id)]))
            res.position_filled_count = total_len

    def add_components(self):
        self.ensure_one()
        material_list = []
        labour_list = []
        equipment_list = []
        boq_line_list = []
        self.material_line_ids.unlink()
        self.equipment_line_ids.unlink()
        self.labour_line_ids.unlink()
        self.boq_line_ids.unlink()
        if self.sale_id.order_line:
            for material in self.sale_id.order_line:
                boq_line_list.append((0, 0, {
                    'product_id': material.product_id.id,
                    'description': material.name,
                    'product_uom_qty': material.product_uom_qty,
                    # 'uom_id':material.uom_id.id,
                }))

        if self.sale_id.material_line_ids:
            for material in self.sale_id.material_line_ids:
                material_list.append((0, 0, {
                    'product_id': material.product_tmpl_id.id,
                    'description': material.description,
                    'product_uom_qty': material.product_uom_qty,
                    'uom_id': material.uom_id.id,
                    'price_unit':material.price_unit,
                }))
        if self.sale_id.labour_line_ids:
            for labour in self.sale_id.labour_line_ids:
                labour_list.append((0, 0, {
                    'product_id': labour.product_tmpl_id.id,
                    'description': labour.description,
                    'product_uom_qty': labour.product_uom_qty,
                    'uom_id': labour.uom_id.id,

                }))
        if self.sale_id.equipment_line_ids:
            for equ in self.sale_id.equipment_line_ids:
                equipment_list.append((0, 0, {
                    'product_id': equ.product_tmpl_id.id,
                    'description': equ.description,
                    'product_uom_qty': equ.product_uom_qty,
                    'uom_id': equ.uom_id.id,

                }))
        self.write({'material_line_ids': material_list,
                    'labour_line_ids': labour_list,
                    'equipment_line_ids': equipment_list,
                    'boq_line_ids': boq_line_list})

    def update_components(self):
        material_list = []
        new_material_list = []
        equipments_list = []
        new_equipments_list = []
        labour_list = []
        new_labour_list = []
        for material_line in self.material_line_ids:
            material_line.write({'product_uom_qty': 0})
        for labour_line in self.labour_line_ids:
            labour_line.write({'product_uom_qty': 0})
        for equipment_line in self.equipment_line_ids:
            equipment_line.write({'product_uom_qty': 0})
        for pricelist in self.boq_line_ids:
            bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', pricelist.product_id.id)])
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
                    old_product_id = self.env['material.details.phase'].search(
                        [('product_id', '=', material.product_id.id), ('phase_id', '=', self.id)])
                    if old_product_id:
                        if material not in new_material_list:
                            old_product_id.product_uom_qty += material.product_qty*pricelist.product_uom_qty

                    new_material_list.append(material)
            if len(labour_list) >= 1:
                for labour in labour_list:
                    old_labour_id = self.env['labour.details.phase'].search(
                        [('product_id', '=', labour.product_id.id), ('phase_id', '=', self.id)])
                    if old_labour_id:
                        if labour not in new_labour_list:
                            old_labour_id.product_uom_qty += labour.product_qty * pricelist.product_uom_qty
                    new_labour_list.append(labour)
            if len(equipments_list) >= 1:
                for equipment in equipments_list:
                    old_equipment_id = self.env['equipment.details.phase'].search(
                        [('product_id', '=', equipment.product_id.id), ('phase_id', '=', self.id)])
                    if old_equipment_id:
                        if equipment not in new_equipments_list:
                            old_equipment_id.product_uom_qty += equipment.product_qty * pricelist.product_uom_qty
                    new_equipments_list.append(equipment)

    def generate_picking(self):
        self.write({'checking': True})
        picking_id = self.env['picking.management'].create(
            {'phase_id': self._origin.id, 'project_id': self.project_id.id, 'warehouse_id': self.warehouse_id.id})
        if picking_id:
            for line in self.material_line_ids:
                material_line = self.env['picking.management.line'].create({'product_id': line.product_id.id,
                                                                           'description': line.description,
                                                                            'expected_qty': line.product_uom_qty,
                                                                            'picking_id': picking_id.id,
                                                                            })
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Picking Created',
                'type': 'rainbow_man',
            }
        }


class project_inherit(models.Model):
    _inherit = 'project.project'

    vehicle_count = fields.Integer(compute='compute_count')
    phase_count = fields.Integer(compute='compute_phase_counts')
    project_cost = fields.Float(related="project_rate", string="Project Cost")
    planned_material_cost = fields.Float(string="Planned Material Cost", compute="set_planned_material_cost")
    actual_material_cost = fields.Float("Actual Material Cost", compute="set_actual_material_cost")
    utilization_cost = fields.Float("Utilization Cost", compute="set_utilization_cost")


    @api.depends('planned_material_cost','actual_material_cost')
    def set_utilization_cost(self):
        for data in self:
            if data.actual_material_cost == 0:
                data.utilization_cost = 0
            else:
                data.utilization_cost = data.planned_material_cost - data.actual_material_cost


    @api.depends('actual_material_cost')
    def set_actual_material_cost(self):
        total = 0
        for data in self:
            voucher_ids = self.env['material.issue.voucher'].search([('project_id','=',data.id),('state','=','approved')])
            for voucher in voucher_ids:
                for material in voucher.slip_line_ids:
                    total += material.allocated_qty * material.rate
            data.actual_material_cost = total
        return


    @api.depends('order_id','planned_material_cost')
    def set_planned_material_cost(self):
        for data in self:
            data.planned_material_cost = data.order_id.material_total


    def project_phase_create(self):
        return {
            'name': "Project Phase",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.phase',
            'context': {'default_project_id': self._origin.id,
                        'default_sale_id': self.order_id.id}
        }

    def get_vehicles(self):
        # self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Phase',
            'view_mode': 'tree,form',
            'res_model': 'project.phase',
            'domain': [('project_id', '=', self._origin.id)],
            'context': "{'create': False}"
        }

    def compute_count(self):
        for record in self:
            record.vehicle_count = self.env['project.phase'].search_count(
                [('project_id', '=', record._origin.id)])

    def action_button_value(self):
        phase_id = self.env['project.phase'].search(
            [('project_id', '=', self._origin.id)], limit=1)
        if phase_id:
            return {
                'name': "Project Phase",
                'type': 'ir.actions.act_window',
                'view_type': 'kanban,form,tree',
                'view_mode': 'kanban,form,tree',
                'res_model': 'project.phase',
                'domain': [('project_id', '=', self._origin.id)],
                'context': "{'create': False}"}
        else:
            return {
                'name': "Project Phase",
                'type': 'ir.actions.act_window',
                'view_type': 'form,tree,kanban',
                'view_mode': 'form,tree,kanban',
                'res_model': 'project.phase',
                'context': {'default_project_id': self._origin.id}
            }

    # def action_view_tasks(self):
    #     pass
        # raise ValidationError('hello')

    def compute_phase_counts(self):
        for count in self:
            count.phase_count = self.env['project.phase'].search_count(
                [('project_id', '=', count._origin.id)])

        pass


class Dynamicstages(models.Model):
    _name = 'dynamic.stages'
    _rec_name = 'name'
    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence')
    fold = fields.Boolean(string='Folded in Kanban')
    project_id = fields.Many2one('project.project', string='Project')


class project_task(models.Model):

    _inherit = 'project.task'

    phase_id = fields.Many2one('project.phase', string='Phase')
    boq_line_ids = fields.One2many('boq.task.line', 'task_id')
    material_line_ids = fields.One2many('material.task.line', 'task_id')
    labour_line_ids = fields.One2many('labour.line.task', 'task_id')
    equipment_line_ids = fields.One2many('equipment.line.task', 'task_id')
    mrs_count = fields.Integer(compute="_compute_mrs_count")



    def show_mrs(self):
        return {
            'name': 'MRS',
            'view_mode': 'tree,form',
            'res_model': 'material.requisition.slip',
            'type': 'ir.actions.act_window',
            'domain': [('task_id', '=', self._origin.id)]}

    def _compute_mrs_count(self):
        for res in self:
            total_len = len(self.env['material.requisition.slip'].search([('task_id', '=', res._origin.id)]))
            res.mrs_count = total_len

    def add_components_material(self):
        self.ensure_one()
        material_list = []
        labour_list = []
        equipment_list = []
        boq_line_list = []
        self.material_line_ids.unlink()
        self.equipment_line_ids.unlink()
        self.labour_line_ids.unlink()
        self.boq_line_ids.unlink()
        if self.phase_id.boq_line_ids:
            for material in self.phase_id.boq_line_ids:
                boq_line_list.append((0, 0, {
                    'product_id': material.product_id.id,
                    'description': material.description,
                    'product_uom_qty': material.product_uom_qty,
                }))

        if self.phase_id.material_line_ids:
            for material in self.phase_id.material_line_ids:
                material_list.append((0, 0, {
                    'product_id': material.product_id.id,
                    'description': material.description,
                    'product_uom_qty': material.product_uom_qty,
                    'uom_id': material.uom_id.id,
                    'price_unit':material.price_unit,
                }))
        if self.phase_id.labour_line_ids:
            for labour in self.phase_id.labour_line_ids:
                labour_list.append((0, 0, {
                    'product_id': labour.product_id.id,
                    'description': labour.description,
                    'product_uom_qty': labour.product_uom_qty,
                    'uom_id': labour.uom_id.id,

                }))
        if self.phase_id.equipment_line_ids:
            for equ in self.phase_id.equipment_line_ids:
                equipment_list.append((0, 0, {
                    'product_id': equ.product_id.id,
                    'description': equ.description,
                    'product_uom_qty': equ.product_uom_qty,
                    'uom_id': equ.uom_id.id,

                }))
        self.write({'material_line_ids': material_list,
                    'labour_line_ids': labour_list,
                    'equipment_line_ids': equipment_list,
                    'boq_line_ids': boq_line_list
                    })

    def update_components(self):
        material_list = []
        new_material_list = []
        equipments_list = []
        new_equipments_list = []
        labour_list = []
        new_labour_list = []
        for material_line in self.material_line_ids:
            material_line.write({'product_uom_qty': 0})
        for labour_line in self.labour_line_ids:
            labour_line.write({'product_uom_qty': 0})
        for equipment_line in self.equipment_line_ids:
            equipment_line.write({'product_uom_qty': 0})
        for pricelist in self.boq_line_ids:
            bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', pricelist.product_id.id)])
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
                    old_product_id = self.env['material.task.line'].search(
                        [('product_id', '=', material.product_id.id), ('task_id', '=', self.id)])
                    if old_product_id:
                        if material not in new_material_list:
                            old_product_id.product_uom_qty += material.product_qty*pricelist.product_uom_qty

                    new_material_list.append(material)
            if len(labour_list) >= 1:
                for labour in labour_list:
                    old_labour_id = self.env['labour.line.task'].search(
                        [('product_id', '=', labour.product_id.id), ('task_id', '=', self.id)])
                    if old_labour_id:
                        if labour not in new_labour_list:
                            old_labour_id.product_uom_qty += labour.product_qty * pricelist.product_uom_qty
                    new_labour_list.append(labour)
            if len(equipments_list) >= 1:
                for equipment in equipments_list:
                    old_equipment_id = self.env['equipment.line.task'].search(
                        [('product_id', '=', equipment.product_id.id), ('task_id', '=', self.id)])
                    if old_equipment_id:
                        if equipment not in new_equipments_list:
                            old_equipment_id.product_uom_qty += equipment.product_qty * pricelist.product_uom_qty
                    new_equipments_list.append(equipment)

    def material_requisition(self):
        vals = []
        miv_ids = self.env['material.issue.voucher'].search([('task_id','=',self.id),('state','=','approved')])
        for line in self.material_line_ids:
            if line.allocated_qty >= line.product_uom_qty and len(vals) == 0:
                raise UserError(_("Pending value is 0 or less. MRS creation failed."))
            else:
                if self.mrs_count > 0 and miv_ids:
                        if line.pending_qty > 0:
                            vals.append((0, 0, {
                                'product_id': line.product_id.id,
                                'product_qty': line.pending_qty,
                                'uom_id': line.product_id.uom_id.id,
                                'rate': line.price_unit,
                            }))
                else:
                        if line.product_uom_qty:
                            vals.append((0, 0, {
                                'product_id': line.product_id.id,
                                'product_qty': line.product_uom_qty,
                                'uom_id': line.product_id.uom_id.id,
                                'rate': line.price_unit,
                            }))


        return {
            'name': "Material Requisition",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'material.requisition.slip',
            'context': {'default_partner_id': self.project_id.partner_id.id,
                        'default_project_id': self.project_id.id,
                        'default_request_date': fields.Datetime.now(),
                        'default_slip_line_ids': vals,
                        'default_task_id': self.id,
                        }
        }


class boq_details(models.Model):

    _name = 'boq.details.phase'
    _rec_name = 'product_id'

    phase_id = fields.Many2one('project.phase', string='Phase')
    product_id = fields.Many2one('product.template', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")


class material_details(models.Model):

    _name = 'material.details.phase'
    _rec_name = 'product_id'

    phase_id = fields.Many2one('project.phase', string='Phase')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    price_unit = fields.Float(string="Unit Price")


class labour_details(models.Model):

    _name = 'labour.details.phase'
    _rec_name = 'product_id'

    phase_id = fields.Many2one('project.phase', string='Phase')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")


class equipment_details(models.Model):

    _name = 'equipment.details.phase'
    _rec_name = 'product_id'

    phase_id = fields.Many2one('project.phase', string='Phase')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")


class picking_management(models.Model):
    _name = 'picking.management'
    _rec_name = 'name'


    name = fields.Char()
    project_id = fields.Many2one('project.project', string='Project')
    phase_id = fields.Many2one('project.phase', string='Phase')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    material_line_ids = fields.One2many('picking.management.line', 'picking_id')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    state = fields.Selection([('draft', 'Draft'),('planned','Planned'),('picked', 'Ready to Pick'),('consolidated','Consolidated')], string='Status', copy=False,
                             default='draft', tracking=True, readonly=True)
    date = fields.Date("Date")
    consolidated_project_id = fields.Many2many('project.project', string='Project')
    consolidated_phase_id = fields.Many2many('project.phase', string='Phase')


    def action_consolidated(self):
        list  = []
        material_list = []
        picking_ids = self.env['picking.management'].browse(self.env.context.get('active_ids'))

        for picking in picking_ids:
            if picking.state != 'planned':
                raise UserError(_("Please Select Planned Picking."))
            if len(picking_ids.mapped('warehouse_id')) > 1:
                raise UserError(_("Please Select Picking With Same Warehouse."))
        new_picking = self.env['picking.management'].create({
            'warehouse_id': picking_ids.mapped('warehouse_id').id,
        })
        for picking in picking_ids:
            for picking_line in picking.material_line_ids:
                material_list.append(picking_line)
        if len(material_list) >= 1:
            for material in material_list:
                old_product_id = self.env['picking.management.line'].search(
                    [('product_id', '=', material.product_id.id), ('picking_id', '=', new_picking.id)])
                if old_product_id:
                    if material not in list:
                        old_product_id.expected_qty += material.expected_qty
                        old_product_id.available_qty += material.available_qty
                        old_product_id.picking_quntity += material.picking_quntity
                else:
                    if material not in list:
                        new_picking.write({'material_line_ids': [(0, 0, {
                                    'product_id':material.product_id.id,
                                    'description':material.description,
                                    'uom_id':material.uom_id.id,
                                    'expected_qty':material.expected_qty,
                                    'available_qty':material.available_qty,
                                    'picking_quntity':material.picking_quntity,
                                })]})
                list.append(material)

        for picking in picking_ids:
            picking.state = 'picked'
        new_picking.state = 'consolidated'
        for material_data in new_picking.material_line_ids:
            if material_data.picking_quntity == 0:
                material_data.unlink()
        c_project_ids = picking_ids.mapped('project_id').ids

        c_phase_ids = picking_ids.mapped('phase_id').ids
        new_picking.write({'consolidated_project_id':[(6, 0, c_project_ids)],
                         'consolidated_phase_id':[(6, 0, c_phase_ids)]})


    def action_pdf_report(self):
        return self.env.ref('AGAF_Project.consolidated_picking_report').report_action(self)


    @api.model
    def create(self, vals):
        result = super(picking_management, self).create(vals)
        result.name = 'PICK00'+str(result.id)
        return result

    def set_stock_from_multiple_location(self, multi_location_stock_ids, rec, replace_stock ):
            if multi_location_stock_ids:
                consumed_qty = 0
                total_required_qty = rec.expected_qty
                for stock in multi_location_stock_ids:
                    if total_required_qty > stock.quantity:
                        product_uom_qty = stock.quantity
                        quantity_done = stock.quantity
                    else:
                        product_uom_qty = total_required_qty
                        quantity_done = total_required_qty
                    rec.available_qty += quantity_done
                    stock_move_obj = self.env['stock.move'].create({
                        'origin': self.name,
                        'name': rec.product_id.name,
                        'product_id': rec.product_id.id,
                        'product_uom': rec.uom_id.id,
                        'product_uom_qty': quantity_done,
                        'location_id': stock.location_id.id,
                        'location_dest_id': replace_stock.id,
                        'quantity_done': quantity_done
                    })
                    consumed_qty += product_uom_qty
                    total_required_qty -= consumed_qty
                    if stock_move_obj:
                        stock_move_obj._action_confirm()
                        stock_move_obj._action_assign()
                        stock_move_obj.write({'state': 'done'})
                    location_ids = self.env['stock.quant'].search(
                        [('product_id.id', '=', rec.product_id.id), ('location_id', '=', stock.location_id.id)])
                    for product in location_ids:
                        product.sudo().reserved_quantity = product.reserved_quantity - (quantity_done)
                        product.sudo().quantity = product.quantity - quantity_done
                    quants = self.env['stock.quant'].create({
                        'location_id': replace_stock.id,
                        'product_id': rec.product_id.id,
                        'quantity': quantity_done
                    })
                    # quants.action_apply_inventory()
                    rec.picking_quntity = rec.expected_qty - rec.available_qty
                    if consumed_qty == rec.expected_qty:
                        break


    def generate_qty(self):
        replace_stock = self.env['stock.location'].search([('is_replace_location','=',True)])
        if not replace_stock:
            raise UserError(_("Reservation location is not set for %s"%(self.warehouse_id.name)))
        else:
            for rec in self.material_line_ids:
                multi_location_stock_ids = self.env['stock.quant'].search(
                    [('warehouse_id', '=', self.warehouse_id.id), ('product_id', '=', rec.product_id.id),('location_id.is_replace_location', '!=', True),('quantity', '>', 0)])
                if multi_location_stock_ids:
                    self.set_stock_from_multiple_location(multi_location_stock_ids,rec,replace_stock)
                else:
                    rec.picking_quntity = rec.expected_qty
            self.state = 'planned'





class picking_management_line(models.Model):
    _name = 'picking.management.line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    picking_id = fields.Many2one('picking.management', 'Picking')
    expected_qty = fields.Float(string='Required quantity')
    available_qty = fields.Float(string='Available quantity',)
    picking_quntity = fields.Float(string='Picking quantity')
    total_quantity = fields.Float(string='Prev Purchase quantity')
    onhand_quantity = fields.Float(string='Onhand')
    checking = fields.Float(string='Check')
    prev_onhand = fields.Float(string='Prev Onhand')
    current_qty = fields.Float(string='current qty')


class boq_line_task(models.Model):
    _name = 'boq.task.line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    task_id = fields.Many2one('project.task', string='Task')


class material_line_task(models.Model):
    _name = 'material.task.line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Required Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    task_id = fields.Many2one('project.task', string='Task')
    price_unit = fields.Float("Price Unit")
    allocated_qty = fields.Float("Allocated Quantity", compute="set_allocated_qty_from_miv")
    pending_qty = fields.Float("Pending Quantity")

    def set_allocated_qty_from_miv(self):
        voucher_ids  = self.env['material.issue.voucher'].search([('task_id','=',self.task_id.id),('state','=','approved')])
        if voucher_ids:
            for voucher in voucher_ids:
                for material in voucher.slip_line_ids:
                    for data in self.task_id.material_line_ids:
                        if material.product_id == data.product_id:
                            data.allocated_qty += material.allocated_qty
                            data.pending_qty = data.product_uom_qty - data.allocated_qty
                        else:
                            data.allocated_qty = data.allocated_qty
                            data.pending_qty = data.product_uom_qty - data.allocated_qty
        else:
            self.allocated_qty = 0


class labour_line_task(models.Model):
    _name = 'labour.line.task'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    task_id = fields.Many2one('project.task', string='Task')


class equipment_line_task(models.Model):
    _name = 'equipment.line.task'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    task_id = fields.Many2one('project.task', string='Task')
