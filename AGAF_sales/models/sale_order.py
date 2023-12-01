# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models, _
import base64
import xlwt
from io import StringIO, BytesIO
import platform
from odoo.tools import html2plaintext
from odoo.tools.mimetypes import guess_mimetype
import tempfile
from PIL import Image
import os



class SOBOQMaterialDetails(models.Model):
    _name = 'so.boq.material.details'

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
    order_id = fields.Many2one('sale.order', string="Order")
    margin_pr = fields.Float("Margin(%)")
    enquiry_type = fields.Selection(related="order_id.enquiry_type", string="Enquiry Type")


class SOBOQLabourDetails(models.Model):
    _name = 'so.boq.labour.details'

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
    order_id = fields.Many2one('sale.order', string="Order")
    margin_pr = fields.Float("Margin(%)")
    enquiry_type = fields.Selection(related="order_id.enquiry_type", string="Enquiry Type")


class SOBOQEquipmentDetails(models.Model):
    _name = 'so.boq.equipment.details'

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
    order_id = fields.Many2one('sale.order',string="Order")
    margin_pr = fields.Float("Margin(%)")
    enquiry_type = fields.Selection(related="order_id.enquiry_type", string="Enquiry Type")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    material_line_ids = fields.One2many('so.boq.material.details', 'order_id', string='Materials')
    equipment_line_ids = fields.One2many('so.boq.equipment.details', 'order_id', string='Equipments')
    labour_line_ids = fields.One2many('so.boq.labour.details', 'order_id', string='Labours')
    estimation_id = fields.Many2one("estimation.works", string="Enquiry Ref.")
    material_total = fields.Monetary("Total Material Cost",  store=True)
    labour_total = fields.Monetary("Total Labour Cost", store=True)
    enquiry_type = fields.Selection(related="opportunity_id.enquiry_type", string="Enquiry Type")
    margin_pr = fields.Float("Margin(%)")
    new_project_id = fields.Many2one('project.project', string="Project")
    ref_no = fields.Char("Ref.No.")

    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state not in ('sale', 'done'):
            return self.env.ref('AGAF_sales.agaf_email_template_edi_sale', raise_if_not_found=False)
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """ Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        return self.env.ref('AGAF_sales.agaf_mail_template_sale_confirmation', raise_if_not_found=False)

    def action_excel_report(self):
        workbook = xlwt.Workbook()

        sheet = workbook.add_sheet('Quotation')
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        workbook.portrait = True

        col_index = 0  # Column index (0-based)
        new_width = 2000

        style0 = xlwt.easyxf(
            'font:bold True, height 210; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color white;alignment: horiz center, wrap True;',
            num_format_str='#,##0.000')
        style1 = xlwt.easyxf(
            'font:bold True, height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color white;alignment: horiz left,vert top, wrap True;',
            num_format_str='#,##0.000')
        style2 = xlwt.easyxf(
            'font:bold True, height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color black;alignment: horiz left,vert top, wrap True;',
            num_format_str='#,##0.000')
        style3 = xlwt.easyxf(
            'font:bold True, height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color black;alignment: horiz left,vert top, wrap True;',
            num_format_str='#,##0.000')
        style4 = xlwt.easyxf(
            'font:height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color black;alignment: horiz left,vert top, wrap True;',
            num_format_str='#,##0.000')
        style8 = xlwt.easyxf(
            'font:height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color black;alignment: horiz right,vert top, wrap True;',
            num_format_str='#,##0.000')
        style5 = xlwt.easyxf(
            'font:height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color black;alignment: horiz left,vert top, wrap True;',
            num_format_str='#,##0')
        style6 = xlwt.easyxf(
            'font: height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color white;alignment: horiz left,vert center, wrap True;',
            num_format_str='#,##0.000')
        style7 = xlwt.easyxf(
            'font: bold True, height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color white, left_color white;alignment: horiz left,vert center, wrap True;',
            num_format_str='#,##0.000')
        style9 = xlwt.easyxf(
            'font:height 180; borders:left thin, right thin, top thin, bottom thin, top_color black, bottom_color black, right_color black, left_color white;alignment: horiz left,vert center, wrap True;',
            num_format_str='#,##0.000')
        date_format = xlwt.easyxf(num_format_str='DD/MM/YYYY')
        alignment = xlwt.Alignment()
        borders = xlwt.Borders()
        borders.right = xlwt.Borders.THIN
        borders.left = xlwt.Borders.THIN
        borders.left_colour = 1
        cell_format = xlwt.easyxf('font: bold 0')  # You can add additional formatting if needed
        cell_format.num_format_str = date_format.num_format_str  # Apply the date format to the cell
        alignment.horz = xlwt.Alignment.HORZ_LEFT
        cell_format.alignment = alignment
        cell_format.borders = borders

        style11 = xlwt.easyxf(
            'font:bold True; borders:left thin, right thin, top thin, bottom thin, top_color white, bottom_color white, right_color white, left_color white;alignment: horiz left,wrap True;',
            num_format_str='#,##0.00')


        data = base64.b64decode(self.company_id.logo)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(data)
        fobj.close()
        try:
            im = Image.open(fname)
        finally:
            os.unlink(fname)
        image_parts = im.split()
        r = image_parts[0]
        g = image_parts[1]
        b = image_parts[2]
        img = Image.merge("RGB", (r, g, b))
        fo = BytesIO()
        img.save(fo, format='bmp')
        sheet.insert_bitmap_data(fo.getvalue(), 0, 0)

        sheet.write_merge(1, 1, 0, 0, '', style11)
        sheet.write_merge(2, 2, 0, 0, '', style11)
        sheet.write_merge(0, 2, 1, 4, '', style0)
        sheet.write_merge(0, 2, 5, 12, 'Quotation', style0)



        row = 3
        upto_row = 7
        # sheet.write_merge(0, 0, 0, 12, 'Quotation', style0)
        sheet.write_merge(row, upto_row, 0, 0, 'To: ', style1)
        sheet.write_merge(row, upto_row, 1, 6, self.partner_id.name, style9)
        sheet.write_merge(row, row, 7, 8, 'Quotation No.: ', style2)
        sheet.write_merge(row, row, 9, 12, self.name, style9)
        row += 1
        sheet.write_merge(row, row, 7, 8, 'Date:', style2)
        sheet.write_merge(row, row, 9, 12, self.date_order, cell_format)
        row += 1
        sheet.write_merge(row, row, 7, 8, 'REF.NO.: ', style2)
        sheet.write_merge(row, row, 9, 12, self.ref_no, cell_format)
        row += 1
        sheet.write_merge(row, row, 7, 12, '', style2)
        row += 1
        sheet.write_merge(row, row, 7, 12, '', style2)
        row += 1
        sheet.write_merge(row, row, 0, 1, 'PROJECT DESCRIPTION: ', style2)
        sheet.write_merge(row, row, 2, 12, self.estimation_id.opportunity_id.name, style9)
        row += 1
        sheet.write_merge(row, row+1, 0, 0, 'SL NO', style3)
        sheet.write_merge(row, row+1, 1, 2, 'Item Code', style3)
        sheet.write_merge(row, row+1, 3, 3, 'Description', style3)
        sheet.write_merge(row, row+1, 4, 4, 'UoM', style3)
        sheet.write_merge(row, row+1, 5, 5, 'QTY', style3)
        sheet.write_merge(row, row, 6, 9, 'UNIT RATE', style3)
        sheet.write_merge(row, row, 10, 12, 'TOTAL AMOUNT', style3)
        row += 1
        sheet.write_merge(row, row, 6, 7, 'Materials', style3)
        sheet.write_merge(row, row, 8, 9, 'Labour', style3)
        sheet.write_merge(row, row, 10, 11, 'Materials', style3)
        sheet.write_merge(row, row, 12, 12, 'Labour', style3)
        row +=1
        total_material = 0
        total_labour = 0
        vals = self.group_by_work_type()
        for data in vals:
            sheet.write_merge(row, row, 0, 12, data, style3)
            counter = 1
            row += 1
            for orderline in vals[data]:
                sheet.write_merge(row, row, 0, 0, int(counter), style5)
                if orderline.product_id.default_code:
                    sheet.write_merge(row, row, 1, 2, orderline.product_id.default_code, style4)
                else:
                    sheet.write_merge(row, row, 1, 2, '', style4)
                sheet.write_merge(row, row, 3, 3, orderline.product_id.name, style4)
                sheet.write_merge(row, row, 4, 4, orderline.product_uom.name, style4)
                sheet.write_merge(row, row, 5, 5, orderline.product_uom_qty, style4)
                sheet.write_merge(row, row, 6, 7, orderline.material_rate, style4)
                sheet.write_merge(row, row, 8, 9, orderline.labour_rate+orderline.equipment_rate, style4)
                sheet.write_merge(row, row, 10, 11, orderline.material_rate*orderline.product_uom_qty, style4)
                sheet.write_merge(row, row, 12, 12, ((orderline.labour_rate+orderline.equipment_rate)*orderline.product_uom_qty), style4)
                row += 1
                counter += 1
                total_material = total_material+(orderline.material_rate*orderline.product_uom_qty)
                total_labour =  total_labour+((orderline.labour_rate+orderline.equipment_rate)*orderline.product_uom_qty)

        sheet.write_merge(row, row, 0, 9, 'TOTAL MATERIAL & LABOUR', style8)
        sheet.write_merge(row, row, 10, 11, total_material, style4)
        sheet.write_merge(row, row, 12, 12, total_labour, style4)
        row += 1
        sheet.write_merge(row, row, 0, 9, 'Total Amount', style8)
        sheet.write_merge(row, row, 10, 12, total_material+total_labour, style4)
        row += 1
        total_tax = 0
        taxes = self.set_tax_line()
        for tax in taxes:
            sheet.write_merge(row, row, 0, 9, tax, style8)
            sheet.write_merge(row, row, 10, 12, taxes[tax], style4)
            total_tax += taxes[tax]
            row += 1
        sheet.write_merge(row, row, 0, 9, self.currency_id.amount_to_text(total_material+total_labour+total_tax), style0)
        sheet.write_merge(row, row, 10, 12, total_material+total_labour+total_tax, style0)
        row += 1
        sheet.write_merge(row, row+1, 0, 1, 'Terms & Conditions:', style7)
        if self.note:
            sheet.write_merge(row, row+1, 2, 12, html2plaintext(self.note), style6)
        else:
            sheet.write_merge(row, row + 1, 2, 12, '', style6)
        row += 2
        sheet.write_merge(row, row+1, 0, 1, 'Payment terms:', style7)
        if self.payment_term_id.name:
            sheet.write_merge(row, row+1, 2, 12, self.payment_term_id.name, style6)
        else:
            sheet.write_merge(row, row + 1, 2, 12, '', style6)
        row += 2
        sheet.write_merge(row, row+1, 0, 1, 'Prepared By:', style7)
        sheet.write_merge(row, row+1, 2, 5, self.user_id.name, style6)
        sheet.write_merge(row, row+1, 6, 7, 'Authorized Signatory:', style7)
        sheet.write_merge(row, row+1, 8, 12, '', style6)

        sheet.col(0).width = 1500
        sheet.col(1).width = 1500
        sheet.col(2).width = 1500
        sheet.col(3).width = 7500
        sheet.col(4).width = 2000
        sheet.col(5).width = 2000
        sheet.col(6).width = 2000
        sheet.col(7).width = 2000
        sheet.col(8).width = 2000
        sheet.col(9).width = 2000
        sheet.col(10).width = 2000
        sheet.col(11).width = 2000
        sheet.col(12).width = 2500


        datas = []
        output = StringIO()
        for data in datas:
            record = ';'.join(data)
            output.write(record)
            output.write("\n")
        data = base64.b64encode(bytes(output.getvalue(), "utf-8"))

        if platform.system() == 'Linux':
            filename = ('/tmp/Quotation' + '.xls')
        else:
            filename = ('Quotation' + '.xls')

        workbook.save(filename)
        fp = open(filename, "rb")
        file_data = fp.read()
        out = base64.encodebytes(file_data)

        # Files actions
        attach_vals = {
            'payslip_data': 'Quotation Excel Report' + '.xls',
            'file_name': out,
        }

        act_id = self.env['quotation.report.out'].create(attach_vals)
        fp.close()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'quotation.report.out',
            'res_id': act_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'context': self.env.context,
            'target': 'new',
        }

    def action_pdf_report(self):
        return self.env.ref('AGAF_sales.quotation_certificate_report').report_action(self)

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        if self.estimation_id:
            self.estimation_id.state = 'cancel'
        return res

    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        sequence = self.env['ir.sequence'].next_by_code('project.project.seq')
        plan_id = self.env['account.analytic.plan'].search(
            [('name', '=', 'Projects'), ('company_id', '=', self.company_id.id)])
        if not plan_id:
            plan_id = self.env['account.analytic.plan'].sudo().create(
                {'name': 'Projects', 'company_id': self.company_id.id})

        acc_id = self.env['account.analytic.account'].sudo().create(
            {'name': sequence, 'plan_id': plan_id.id, 'company_id': self.company_id.id})
        project_id = self.env['project.project'].sudo().create(
            {'name': sequence, 'analytic_account_id': acc_id.id, 'order_id': self.id, 'project_rate': self.amount_total,
             'company_id': self.company_id.id, 'partner_id':self.partner_id.id})
        self.visible_project = True
        self.new_project_id = project_id
        self.picking_ids.unlink()

    def add_components(self):
        if self.enquiry_type == 'bid':
            self.ensure_one()
            material_list = []
            labour_list = []
            equipment_list = []
            self.material_line_ids.unlink()
            self.equipment_line_ids.unlink()
            self.labour_line_ids.unlink()
            if self.estimation_id.material_line_ids:
                for material in self.estimation_id.material_line_ids:
                    material_list.append((0, 0, {
                        'product_tmpl_id': material.product_tmpl_id.id,
                        'description':material.description,
                        'product_uom_qty': material.product_uom_qty,
                        'uom_id':material.uom_id.id,
                        'price_unit': material.price_unit,
                        'fixed_price_unit': material.fixed_price_unit,
                        'total': material.total,
                        'margin_pr': material.margin_pr,
                    }))
            if self.estimation_id.labour_line_ids:
                for labour in self.estimation_id.labour_line_ids:
                    labour_list.append((0, 0, {
                        'product_tmpl_id': labour.product_tmpl_id.id,
                        'description':labour.description,
                        'product_uom_qty': labour.product_uom_qty,
                        'uom_id':labour.uom_id.id,
                        'price_unit': labour.price_unit,
                        'fixed_price_unit': labour.fixed_price_unit,
                        'total': labour.total,
                        'margin_pr': labour.margin_pr,
                    }))
            if self.estimation_id.equipment_line_ids:
                for equ in self.estimation_id.equipment_line_ids:
                    equipment_list.append((0, 0, {
                        'product_tmpl_id': equ.product_tmpl_id.id,
                        'description':equ.description,
                        'product_uom_qty': equ.product_uom_qty,
                        'uom_id':equ.uom_id.id,
                        'price_unit': equ.price_unit,
                        'fixed_price_unit': equ.fixed_price_unit,
                        'total': equ.total,
                        'margin_pr': equ.margin_pr,
                    }))
            self.write({'material_line_ids': material_list,
                        'labour_line_ids': labour_list,
                        'equipment_line_ids': equipment_list})
            self.labour_total = 0
            self.material_total = 0
            labour_cost = 0
            equipment_cost = 0
            for estimation in self:
                if estimation.material_line_ids:
                    for data in estimation.material_line_ids:
                        estimation.material_total += data.total
                if estimation.labour_line_ids:
                    for labour in estimation.labour_line_ids:
                        labour_cost += labour.total
                if estimation.equipment_line_ids:
                    for equipment in estimation.equipment_line_ids:
                        equipment_cost += equipment.total
            self.labour_total = labour_cost + equipment_cost
        if self.enquiry_type == 'fixed':
            material_list = []
            new_material_list = []
            equipments_list = []
            new_equipments_list = []
            labour_list = []
            new_labour_list = []
            self.material_line_ids.unlink()
            self.equipment_line_ids.unlink()
            self.labour_line_ids.unlink()
            if self.pricelist_id:
                for item in self.pricelist_id.item_ids:
                    product_id = item.product_tmpl_id
                    sale_product = self.env['sale.order.line'].search([('product_id','=',product_id.id),('order_id','=',self.id)])
                    if sale_product:
                        bom = self.env['mrp.bom'].search([('product_tmpl_id','=',product_id.id)])
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
                                    old_product_id = self.env['so.boq.material.details'].search(
                                        [('product_tmpl_id', '=', material.product_id.id),
                                         ('order_id', '=', self.id)])
                                    if old_product_id:
                                        if material not in new_material_list:
                                            old_product_id.product_uom_qty += material.product_qty * sale_product.product_uom_qty
                                            old_product_id.total = old_product_id.product_uom_qty * old_product_id.price_unit
                                    else:
                                        if material not in new_material_list:
                                            vals = {
                                                'product_tmpl_id': material.product_id.id,
                                                'product_uom_qty': material.product_qty * sale_product.product_uom_qty,
                                            }

                                            for pricelist_material in self.pricelist_id.material_line_ids:
                                                if material.product_id == pricelist_material.product_tmpl_id:
                                                    vals.update({'price_unit': pricelist_material.cost_price,
                                                                 'fixed_price_unit': pricelist_material.cost_price,
                                                                 'total': (material.product_qty * sale_product.product_uom_qty) * pricelist_material.cost_price,})

                                            self.write({'material_line_ids': [(0, 0, vals)]})
                                    new_material_list.append(material)

                            if len(labour_list) >= 1:
                                for labour in labour_list:
                                    old_labour_id = self.env['so.boq.labour.details'].search(
                                        [('product_tmpl_id', '=', labour.product_id.id), ('order_id', '=', self.id)])
                                    if old_labour_id:
                                        if labour not in new_labour_list:
                                            old_labour_id.product_uom_qty += labour.product_qty * sale_product.product_uom_qty
                                            old_labour_id.total = old_labour_id.product_uom_qty * old_labour_id.price_unit
                                    else:
                                        if labour not in new_labour_list:
                                            labour_vals = {
                                                'product_tmpl_id': labour.product_id.id,
                                                'product_uom_qty': labour.product_qty * sale_product.product_uom_qty,
                                            }
                                            for pricelist_labour in self.pricelist_id.labour_line_ids:
                                                if labour.product_id == pricelist_labour.product_tmpl_id:
                                                    labour_vals.update({'price_unit': pricelist_labour.cost_price,
                                                                 'fixed_price_unit': pricelist_labour.cost_price,
                                                                 'total': (labour.product_qty * sale_product.product_uom_qty) * pricelist_labour.cost_price,
                                                                 })
                                            self.write({'labour_line_ids': [(0, 0, labour_vals)]})
                                    new_labour_list.append(labour)
                            if len(equipments_list) >= 1:
                                for equipment in equipments_list:
                                    old_equipment_id = self.env['so.boq.equipment.details'].search(
                                        [('product_tmpl_id', '=', equipment.product_id.id),
                                         ('order_id', '=', self.id)])
                                    if old_equipment_id:
                                        if equipment not in new_equipments_list:
                                            old_equipment_id.product_uom_qty += equipment.product_qty * sale_product.product_uom_qty
                                            old_equipment_id.total = old_equipment_id.product_uom_qty * old_equipment_id.price_unit
                                    else:
                                        if equipment not in new_equipments_list:
                                            equipment_vals =  {
                                                'product_tmpl_id': equipment.product_id.id,
                                                'product_uom_qty': equipment.product_qty * sale_product.product_uom_qty,
                                            }

                                            for pricelist_equipment in self.pricelist_id.equipment_line_ids:
                                                if equipment.product_id == pricelist_equipment.product_tmpl_id:
                                                    equipment_vals.update({'price_unit': pricelist_equipment.cost_price,
                                                                 'fixed_price_unit': pricelist_equipment.cost_price,
                                                                 'total': (equipment.product_qty * sale_product.product_uom_qty) * pricelist_equipment.cost_price,
                                                                 })
                                            self.write({'equipment_line_ids': [(0, 0, equipment_vals)]})
                                    new_equipments_list.append(equipment)



            self.labour_total = 0
            self.material_total = 0
            labour_cost = 0
            equipment_cost = 0
            for estimation in self:
                if estimation.material_line_ids:
                    for data in estimation.material_line_ids:
                        estimation.material_total += data.total
                if estimation.labour_line_ids:
                    for labour in estimation.labour_line_ids:
                        labour_cost += labour.total
                if estimation.equipment_line_ids:
                    for equipment in estimation.equipment_line_ids:
                        equipment_cost += equipment.total
            self.labour_total = labour_cost + equipment_cost
        self.update_value()

    def update_value(self):
        for boq_product in self.order_line:
                bom = self.env['mrp.bom'].search([('product_tmpl_id','=',boq_product.product_id.product_tmpl_id.id)])
                if bom:
                    material_total = 0
                    labour_total = 0
                    equipment_total = 0
                    total = 0
                    for components in bom.bom_line_ids:
                        material = self.env['so.boq.material.details'].search([('order_id','=',self.id),('product_tmpl_id','=',components.product_id.id)])
                        if material:
                            material_total += material.price_unit * components.product_qty
                            total += material.price_unit * components.product_qty
                        labour = self.env['so.boq.labour.details'].search([('order_id', '=', self.id), ('product_tmpl_id', '=', components.product_id.id)])
                        if labour:
                            labour_total += labour.price_unit * components.product_qty
                            total += labour.price_unit * components.product_qty
                        equipment = self.env['so.boq.equipment.details'].search([('order_id', '=', self.id), ('product_tmpl_id', '=', components.product_id.id)])
                        if equipment:
                            equipment_total += equipment.price_unit * components.product_qty
                            total += equipment.price_unit * components.product_qty
                    self.write({'order_line':[(1, boq_product.id, { 'total_rate': total,
                                                                    'material_rate': material_total,
                                                                    'labour_rate': labour_total,
                                                                    'equipment_rate': equipment_total,
                                                                    })]})

    def group_by_work_type(self):
        vals = {}
        work_type_id = self.env['work.type'].search([])
        for work_type in work_type_id:
            order_line_ids = self.env['sale.order.line'].search([('order_id','=',self.id),('work_type_id','=',work_type.id)])
            if len(order_line_ids.ids) > 0:
                vals.update({work_type.name : order_line_ids})
        return vals

    def set_tax_line(self):
        dict= {}
        for data in self.order_line:
            if data.tax_id:
                for tax in data.tax_id:
                    if tax.name not in dict:
                        dict[tax.name] = data.price_subtotal * (tax.amount/100)
                    else:
                        value = dict.get(tax.name)
                        new_val = value + data.price_subtotal * (tax.amount/100)
                        dict.update({tax.name : new_val})
        return dict


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    work_type_id = fields.Many2one('work.type', string="Work Type")
    enquiry_type = fields.Selection(related="order_id.enquiry_type", string="Enquiry Type")
    margin_pr = fields.Float("Margin(%)")
    material_rate = fields.Float("Material Rate")
    labour_rate =  fields.Float("Labour Rate")
    equipment_rate = fields.Float("Equipment Rate")
    total_rate = fields.Float("Final total rate")

    def unlink(self):
        for data in self:
            boq_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', data.product_id.product_tmpl_id.id)])
            for boq_material in boq_id.bom_line_ids:
                if boq_material.product_id.is_material:
                    for pricelist_material in data.order_id.material_line_ids:
                        if pricelist_material.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_material.product_uom_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_material.sudo().unlink()
                            else:
                                pricelist_material.update({'product_uom_qty': qty, 'total': qty * pricelist_material.price_unit})
                elif boq_material.product_id.is_labour:
                    for pricelist_labour in data.order_id.labour_line_ids:
                        if pricelist_labour.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_labour.product_uom_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_labour.sudo().unlink()
                            else:
                                pricelist_labour.update({'product_uom_qty': qty, 'total': qty * pricelist_labour.price_unit})
                elif boq_material.product_id.is_equipment:
                    for pricelist_equipment in data.order_id.equipment_line_ids:
                        if pricelist_equipment.product_tmpl_id == boq_material.product_id:
                            qty = pricelist_equipment.product_uom_qty - boq_material.product_qty
                            if qty <= 0:
                                pricelist_equipment.unlink()
                            else:
                                pricelist_equipment.update({'product_uom_qty': qty, 'total': qty * pricelist_equipment.price_unit})
        self.order_id.labour_total = 0
        self.order_id.material_total = 0
        labour_cost = 0
        equipment_cost = 0
        for estimation in self.order_id:
            if estimation.material_line_ids:
                for data in estimation.material_line_ids:
                    estimation.material_total += data.total
            if estimation.labour_line_ids:
                for labour in estimation.labour_line_ids:
                    labour_cost += labour.total
            if estimation.equipment_line_ids:
                for equipment in estimation.equipment_line_ids:
                    equipment_cost += equipment.total
        self.order_id.labour_total = labour_cost + equipment_cost

        return super(SaleOrderLine, self).unlink()


class QuotationReportOut(models.Model):
    _name = 'quotation.report.out'
    _description = 'Quotation Excel report'

    payslip_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Quotation Excel Report', readonly=True)


