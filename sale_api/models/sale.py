from datetime import timedelta
import json
import pytz

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo import http, _, exceptions


def error_response2(error):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": 200,
            "message": list(error.args)
        }
    }


class SaleOrder(models.Model):
    """Inherit sale.order"""
    _inherit = 'sale.order'

    def _localize_timezone(self, date_string):
        """
        Localize datetime based on timezone
        @param: date string
        @return: datetime 
        """
        timezone = self._context.get('tz') or 'UTC'
        local = pytz.timezone(timezone)
        date = fields.Datetime.from_string(date_string)
        return local.localize(date).astimezone(pytz.utc).replace(tzinfo=None)

    def prepare_data_create_api(self, data):
        """ Prepare data for sale order """
        if not data:
            return False

        # datas = data.json()
        sale = data
        partner_obj = self.env['res.partner'].sudo()
        pricelist_obj = self.env['product.pricelist'].sudo()
        currency_obj = self.env['res.currency'].sudo()
        company_obj = self.env['res.company'].sudo()
        product_obj = self.env['product.product'].sudo()
        product_category_obj = self.env['product.category'].sudo()
        sale_order_obj = self.env['sale.order'].sudo()
        order_line_obj = self.env['sale.order.line'].sudo()
        Group = self.env['product.group'].sudo()

        sale_order = {}
        sale_line_list = []
        parent_line_list = []
        # sale_line = {}
        # charge_line = {}
        # parent_line = {}
        if sale.get('origin'):
            sale_order.update({'origin': sale.get('origin')})
            if sale_order_obj.search([('origin', '=', sale.get('origin'))]):
                raise ValidationError(
                    'Sale Order with origin %s already created in Odoo'
                    % sale.get('origin')
                )
        else:
            raise ValidationError('Missing parameter: origin')

        if sale.get('partner_code'):
            partner_id = partner_obj.search([('partner_code', '=', sale.get('partner_code'))], limit=1)
            if partner_id:
                sale_order.update({
                    'partner_id': partner_id.id,
                    'partner_code': sale.get('partner_code'),
                    'partner_invoice_id': partner_id.id
                })
            else:
                raise ValidationError('Customer with code %s not found in Odoo' % sale.get('partner_code'))

            if sale.get('partner_invoice_code'):
                partner_invoice_id = partner_obj.search([
                    ('partner_code', '=', sale.get('partner_invoice_code'))], limit=1)
                if partner_invoice_id:
                    sale_order.update({
                        'partner_invoice_id': partner_invoice_id.id,
                        'partner_invoice_code': sale.get('partner_invoice_code')
                    })
        else:
            raise ValidationError('Missing parameter: partner_code')

        if sale.get('date_order'):
            date = self._localize_timezone(sale.get('date_order'))
            # sale_order.update({'date_order': sale.get('date_order')})
            sale_order.update({'date_order': date})

        if sale.get('currency_code'):
            sale_order.update({'currency_code': sale.get('currency_code')})
            currency_id = currency_obj.search([('name', '=', sale.get('currency_code'))], limit=1)
            if currency_id:
                pricelist_id = pricelist_obj.search([('currency_id', '=', currency_id.id)], limit=1)
                if pricelist_id:
                    sale_order.update({'pricelist_id': pricelist_id.id})
            else:
                raise ValidationError('Currency with code %s not found in Odoo' % sale.get('currency_code'))
        else:
            raise ValidationError('Missing parameter: currency_code')

        if sale.get('client_order_ref'):
            sale_order.update({'client_order_ref': sale.get('client_order_ref')})

        if sale.get('note'):
            sale_order.update({'note': sale.get('note')})

        # Set printai_source value or infor_source value
        if sale.get('pi_source'):
            sale_order.update({'pi_source': sale.get('pi_source')})
        if sale.get('infor_source'):
            sale_order.update({'infor_source': sale.get('infor_source')})

        # TODO: To be confirm for the company code
        company = company_obj.search([('company_code', '=', 'MPM')], limit=1)
        if sale.get('company_code'):
            # sale_order.update({'company_code': sale.get('company_code')})
            # TODO: Tambahin kolom company_code di res.company kalau ngk ada company_code,
            #  paksa company_id = id dari company MPM
            company_id = company_obj.search([('company_code', '=', sale.get('company_code'))], limit=1)
            if company_id:
                company = company_id
        if not company:
            raise ValidationError('No company code %s not found in Odoo' % sale.get('company_code'))
        sale_order.update({'company_id': company.id})

        if company:
            # TODO: add discount in sale order line, use default product configure in company
            global_discount = company.global_discount
            if not global_discount:
                raise ValidationError('Please configure company global discount product!')

        if sale.get('order_line'):
            for line in sale.get('order_line'):
                sale_line = {}
                parent_line = {}
                if order_line_obj.search([('printai_so_job', '=', line.get('printai_so_job'))]):
                    raise ValidationError(
                        'Sale Order Line with PrintAI So Job %s already created in Odoo'
                        % line.get('printai_so_job')
                    )
                if not line.get('is_parent_isbn'):
                    if line.get('product_group'):
                        group_id = Group.search([('code', '=', line.get('product_group'))])
                        if not group_id:
                            group_id = Group.create({
                                'code': line.get('product_group'),
                                'description': line.get('product_group')
                            })
                    else:
                        raise ValidationError('Missing parameter: product_group')
                    if line.get('default_code'):
                        product_id = product_obj.search([
                            ('default_code', '=', line.get('default_code'))], limit=1)
                        if not product_id:
                            if not line.get('name'):
                                raise ValidationError('No product found! Missing parameter: name')
                            category_id = product_category_obj.search([('product_type', '=', 'fg')], limit=1)
                            if not category_id:
                                raise ValidationError('Please set Product Category for Finished Goods in Odoo!')
                            # if not line.get('product_group'):
                            #     raise ValidationError('No product category found! Missing parameter: product_group')
                            # category_id = product_category_obj.search([
                            #     ('product_group', '=', line.get('product_group'))
                            # ], limit=1)
                            # if not category_id:
                            #     raise ValidationError(
                            #         'Product group %s not found in Odoo!' % line.get('product_group')
                            #     )

                            product_val = {
                                'name': line.get('name'),
                                'type': 'product',
                                'categ_id': category_id.id,
                                'invoice_policy': 'delivery',
                                'default_code': line.get('default_code'),
                                'taxes_id': [(6, 0, company.account_sale_tax_id.ids)],
                                'supplier_taxes_id': [(6, 0, company.account_purchase_tax_id.ids)],
                                'company_id': company.id,
                            }
                            product_id = product_obj.create(product_val)

                        # analytic_id = False
                        account_type = False
                        analytic_tags = False

                        if line.get('account_type'):
                            account_type = "".join(line.get('account_type').strip())

                        res = self.env['account.analytic.default'].sudo().account_get(
                            product_id=product_id.id,
                            partner_id=partner_id.id,
                            user_id=self.env.uid,
                            date=sale_order.get('date_order'),
                            company_id=company.id,
                            account_type=account_type,
                            industry_id=partner_id.industry_id.id,
                            salesperson=partner_id.salesperson_code,
                            categ_id=product_id.categ_id.id,
                            product_group_id=group_id.id,
                        )
                        if res:
                            # analytic_id = res[0].analytic_id.id
                            analytic_tags = res.analytic_tag_ids or [(6, 0, res[0].analytic_tag_ids.ids)]

                        sale_line.update({
                            'product_id': product_id.id,
                            'name': line.get('name') or product_id.name,
                            'product_uom_qty': float(line.get('product_uom_qty')) or 1.0,
                            'origin_qty': float(line.get('product_uom_qty')) or 1.0,
                            'price_unit': float(line.get('price_unit')) or 0.0,
                            'printai_so_line': line.get('printai_so_line') or False,
                            'printai_so_job': line.get('printai_so_job') or '',
                            'printai_internal_order_line': line.get(
                                'printai_internal_order_line') or False,
                            'printai_po_line': line.get('printai_po_line') or False,
                            'is_buy': line.get('is_buy') or False,
                            'analytic_tag_ids': analytic_tags,
                            'product_group_id': group_id.id,
                        })
                        if line.get('discount'):
                            sale_line.update({'discount': float(line.get('discount'))})
                        if line.get('printai_owner'):
                            owner_id = partner_obj.search([
                                ('partner_code', '=', line.get('printai_owner'))], limit=1)
                            if owner_id:
                                sale_line.update({'printai_owner': owner_id.id})
                        if line.get('run_on_price_unit'):
                            sale_line.update({
                                'run_on_price_unit': float(line.get('run_on_price_unit')) or 0.0
                            })
                        if line.get('account_type'):
                            account_type = "".join(line.get('account_type').strip())
                            sale_line.update({'account_type': account_type.lower()})
                        else:
                            raise ValidationError('Missing parameter: account_type')
                        if line.get('order_type'):
                            order_type = "".join(line.get('order_type').strip())
                            sale_line.update({'order_type': order_type.lower()})
                        else:
                            raise ValidationError('Missing parameter: order_type')

                        if sale_line:
                            sale_line_list.append((0, 0, sale_line))
                    else:
                        raise ValidationError('Missing parameter: default_code')
                else:
                    if line.get('default_code'):
                        product_id = product_obj.search([('default_code', '=', line.get('default_code'))], limit=1)
                        if product_id:
                            parent_line.update({'product_id': product_id.id,
                                                'printai_so_line': line.get('printai_so_line') or False, })
                        else:
                            raise ValidationError(
                                'Product with default_code %s not found in Odoo' % line.get('default_code')
                            )
                        if parent_line:
                            parent_line_list.append(parent_line)
                    else:
                        raise ValidationError('Missing parameter: default_code')

            # TODO: link parent_id with child_id. Should we add parent_qty and parent_price?
            if sale_line_list and parent_line_list:
                for p_line in parent_line_list:
                    for c_line in sale_line_list:
                        if p_line and c_line[2].get('printai_so_line') == p_line.get('printai_so_line'):
                            c_line[2].update({'parent_isbn': p_line.get('product_id')})

        if sale.get('global_discount'):
            disc = float(sale.get('global_discount'))
            sale_line_list.append(
                (0, 0, {
                    'product_id': global_discount.id,
                    'name': global_discount.name or 'Discount',
                    'product_uom_qty': 1.0,
                    'origin_qty': 1.0,
                    'price_unit': (disc * -1) or 0.0,
                })
            )

        if sale.get('charge_line'):
            for charge in sale.get('charge_line'):
                charge_line = {}
                if charge.get('charge_code'):
                    charge_product_id = product_obj.search([
                        ('default_code', '=', charge.get('charge_code'))], limit=1)
                    if charge_product_id:
                        if not charge_product_id.charge_ok:
                            raise ValidationError(
                                'Please make sure product %s is a charge product'
                                % charge_product_id.name
                            )
                        charge_line.update({
                            # 'printai_so_job_charge': charge.get('printai_so_job') or '',
                            'product_id': charge_product_id.id,
                            'name': charge.get('charges_description') or charge_product_id.name,
                            'price_unit': float(charge.get('price_unit')) or 0.0,
                        })
                        if sale_line_list:
                            for line in sale_line_list:
                                # if charge.get('printai_so_job') == line[2].get('printai_so_job'):
                                if charge_product_id.id == line[2].get('product_id'):
                                    charge_line.update({
                                        'order_type': line[2].get('order_type')
                                    })
                        if charge_line:
                            sale_line_list.append((0, 0, charge_line))
                    else:
                        raise ValidationError(
                            'Product with charge_code %s not found in Odoo' % charge.get('charge_code')
                        )

        if sale_line_list:
            sale_order.update({'order_line': sale_line_list})

        return sale_order

    def prepare_data_update_api(self, data):
        """ Prepare data for sale order update """
        if not data:
            return False

        sale = data
        order_line_obj = self.env['sale.order.line'].sudo()
        partner_obj = self.env['res.partner'].sudo()
        pricelist_obj = self.env['product.pricelist'].sudo()
        currency_obj = self.env['res.currency'].sudo()
        company_obj = self.env['res.company'].sudo()
        product_obj = self.env['product.product'].sudo()
        Group = self.env['product.group'].sudo()

        sale_order = {}
        sale_line_list = []
        parent_line_list = []

        if sale.get('partner_code'):
            partner_id = partner_obj.search([('partner_code', '=', sale.get('partner_code'))], limit=1)
            if partner_id:
                sale_order.update({
                    'partner_id': partner_id.id,
                    'partner_code': sale.get('partner_code'),
                    'partner_invoice_id': partner_id.id
                })
            else:
                raise ValidationError('Customer with code %s not found in Odoo' % sale.get('partner_code'))

            if sale.get('partner_invoice_code'):
                partner_invoice_id = partner_obj.search([
                    ('partner_code', '=', sale.get('partner_invoice_code'))], limit=1)
                if partner_invoice_id:
                    sale_order.update({
                        'partner_invoice_id': partner_invoice_id.id,
                        'partner_invoice_code': sale.get('partner_invoice_code')
                    })

        if sale.get('date_order'):
            date = self._localize_timezone(sale.get('date_order'))
            # sale_order.update({'date_order': sale.get('date_order')})
            sale_order.update({'date_order': date})

        if sale.get('currency_code'):
            sale_order.update({'currency_code': sale.get('currency_code')})
            currency_id = currency_obj.search([('name', '=', sale.get('currency_code'))], limit=1)
            if currency_id:
                pricelist_id = pricelist_obj.search([('currency_id', '=', currency_id.id)], limit=1)
                if pricelist_id:
                    sale_order.update({'pricelist_id': pricelist_id.id})
            else:
                raise ValidationError('Currency with code %s not found in Odoo' % sale.get('currency_code'))

        if sale.get('client_order_ref'):
            sale_order.update({'client_order_ref': sale.get('client_order_ref')})

        if sale.get('note'):
            sale_order.update({'note': sale.get('note')})

        # TODO: To be confirm for the company code
        company = company_obj.search([('company_code', '=', 'MPM')], limit=1)
        if sale.get('company_code'):
            company_id = company_obj.search([('company_code', '=', sale.get('company_code'))], limit=1)
            if company_id:
                company = company_id
        sale_order.update({'company_id': company.id})
        if not company:
            raise ValidationError('Company code %s not found in Odoo' % sale.get('company_code'))

        if company:
            # TODO: add discount in sale order line, use default product configure in company
            global_discount = company.global_discount
            if not global_discount:
                raise ValidationError('Please configure company global discount product!')

        if sale.get('order_line'):
            for line in sale.get('order_line'):
                sale_line = {}
                parent_line = {}
                if not line.get('is_parent_isbn'):
                    if line.get('default_code'):
                        product_id = product_obj.search([
                            ('default_code', '=', line.get('default_code'))], limit=1)
                        if product_id:
                            sale_line.update({'product_id': product_id.id})
                        else:
                            raise ValidationError(
                                'Product with default_code %s not found in Odoo' % line.get('default_code')
                            )
                    if line.get('name'):
                        sale_line.update({'name': line.get('name')})
                    sale_line.update({
                        'product_uom_qty': float(line.get('product_uom_qty')) or 0.0,
                        'origin_qty': float(line.get('product_uom_qty')) or 0.0
                    })
                    if line.get('discount'):
                        sale_line.update({'discount': float(line.get('discount'))})
                    if line.get('price_unit'):
                        sale_line.update({'price_unit': float(line.get('price_unit'))})
                    if line.get('printai_so_line'):
                        sale_line.update({'printai_so_line': line.get('printai_so_line')})
                    if line.get('printai_so_job'):
                        sale_line.update({'printai_so_job': line.get('printai_so_job')})
                    if line.get('printai_internal_order_line'):
                        sale_line.update({'printai_internal_order_line': line.get('printai_internal_order_line')})
                    if line.get('printai_po_line'):
                        sale_line.update({'printai_po_line': line.get('printai_po_line')})
                    if line.get('is_buy'):
                        sale_line.update({'is_buy': line.get('is_buy')})
                    if line.get('printai_owner'):
                        owner_id = partner_obj.search([
                            ('partner_code', '=', line.get('printai_owner'))], limit=1)
                        if owner_id:
                            sale_line.update({'printai_owner': owner_id.id})
                    if line.get('run_on_price_unit'):
                        sale_line.update({
                            'run_on_price_unit': float(line.get('run_on_price_unit'))
                        })
                    if line.get('account_type'):
                        account_type = "".join(line.get('account_type').strip())
                        sale_line.update({'account_type': account_type.lower()})
                    if line.get('order_type'):
                        order_type = "".join(line.get('order_type').strip())
                        sale_line.update({'order_type': order_type.lower()})
                    if line.get('product_group'):
                        group_id = Group.search([('code', '=', line.get('product_group'))])
                        if not group_id:
                            group_id = Group.create({
                                'code': line.get('product_group'),
                                'description': line.get('product_group')
                            })
                        sale_line.update({'product_group_id': group_id.id})
                    else:
                        raise ValidationError('Missing parameter: product_group')

                    if sale_line:
                        if line.get('printai_so_job'):
                            line_id = order_line_obj.search([('printai_so_job', '=', line.get('printai_so_job'))])

                            # Set analytic tags
                            analytic_tags = False

                            res = self.env['account.analytic.default'].sudo().account_get(
                                product_id=product_id.id,
                                partner_id=partner_id.id,
                                user_id=self.env.uid,
                                date=sale_order.get('date_order'),
                                company_id=company.id,
                                account_type=account_type.lower(),
                                industry_id=partner_id.industry_id.id,
                                salesperson=partner_id.salesperson_code,
                                categ_id=product_id.categ_id.id,
                                product_group_id=group_id.id,
                            )
                            if res:
                                # analytic_id = res[0].analytic_id.id
                                analytic_tags = res.analytic_tag_ids or [(6, 0, res[0].analytic_tag_ids.ids)]
                            if analytic_tags:
                                sale_line.update({'analytic_tag_ids': analytic_tags})

                            if line_id:
                                sale_line_list.append((1, line_id.id, sale_line))
                            else:
                                sale_line_list.append((0, 0, sale_line))
                else:
                    if line.get('default_code'):
                        product_id = product_obj.search([('default_code', '=', line.get('default_code'))], limit=1)
                        if product_id:
                            parent_line.update({'product_id': product_id.id,
                                                'printai_so_line': line.get('printai_so_line') or False, })
                        else:
                            raise ValidationError(
                                'Product Charge with default_code %s not found in Odoo' % line.get('default_code')
                            )
                        if parent_line:
                            parent_line_list.append(parent_line)
                    else:
                        raise ValidationError('Missing parameter for parent ISBN: default_code')

            # TODO: link parent_id with child_id. Should we add parent_qty and parent_price?
            if sale_line_list and parent_line_list:
                for p_line in parent_line_list:
                    for c_line in sale_line_list:
                        if p_line and c_line[2].get('printai_so_line') == p_line.get('printai_so_line'):
                            c_line[2].update({'parent_isbn': p_line.get('product_id')})

        if sale.get('global_discount') and self._context.get('sale_id'):
            sale_id = self.env['sale.order'].browse(self._context.get('sale_id'))
            disc = float(sale.get('global_discount'))
            if sale_id:
                line_disc = sale_id.order_line.filtered(
                    lambda sol: sol.product_id == global_discount)
                if line_disc:
                    sale_line_list.append((1, line_disc[0].id, {'price_unit': (disc * -1)}))

        if sale.get('charge_line') and self._context.get('sale_id'):
            for charge in sale.get('charge_line'):
                charge_line = {}
                if charge.get('charge_code'):
                    charge_product_id = product_obj.search([
                        ('default_code', '=', charge.get('charge_code'))], limit=1)
                    if charge_product_id:
                        if not charge_product_id.charge_ok:
                            raise ValidationError(
                                'Please make sure product %s is a charge product'
                                % charge_product_id.name
                            )
                        sale_id = self.env['sale.order'].browse(self._context.get('sale_id'))
                        if sale_id:
                            # line_charge = order_line_obj.search([
                            #     ('printai_so_job_charge', '=', charge.get('printai_so_job'))])
                            line_charge = order_line_obj.search([
                                ('product_id', '=', charge_product_id.id),
                                ('order_id', '=', sale_id.id)
                            ], limit=1)
                            charge_line.update({
                                # 'printai_so_job_charge': charge.get('printai_so_job') or '',
                                'product_id': charge_product_id.id,
                                'name': charge.get('charges_description') or charge_product_id.name,
                                'price_unit': float(charge.get('price_unit'))
                            })
                            if sale_line_list:
                                for line in sale_line_list:
                                    # if charge.get('printai_so_job') == line[2].get('printai_so_job'):
                                    if charge_product_id.id == line[2].get('product_id'):
                                        charge_line.update({'order_type': line[2].get('order_type')})
                            if line_charge:
                                sale_line_list.append((1, line_charge.id, charge_line))
                            else:
                                sale_line_list.append((0, 0, charge_line))
                    else:
                        raise ValidationError(
                            'Product with charge_code %s not found in Odoo' % charge.get('charge_code')
                        )

        if sale_line_list:
            sale_order.update({'order_line': sale_line_list})

        return sale_order

    def get_record_id(self, origin):
        """ Return sale order record """
        sale_obj = self.env['sale.order'].sudo()
        sale_id = sale_obj.search([('origin', '=', origin)], limit=1)
        if not sale_id:
            raise ValidationError(
                'Sale Order with origin %s not found in Odoo'
                % origin
            )
        return sale_id

    def create_api(self, data):
        """ Create Sale Order """
        sale_obj = self.env['sale.order'].sudo()
        values = self.prepare_data_create_api(data)
        try:
            sale_id = sale_obj.create(values)
        except Exception as e:
            raise e
            # res = error_response2(e)
            # return http.Response(
            #     json.dumps(res),
            #     status=200,
            #     mimetype='application/json'
            # )

        if sale_id:
            sale_id.action_confirm()
            sale_id.write({'date_order': values.get('date_order')})
            # else:
            #     raise ValidationError('No record created.')
            return sale_id.id

    def update_api(self, data, origin):
        """ Update sale order data """
        sale_id = self.get_record_id(origin)
        if sale_id:
            values = self.with_context(sale_id=sale_id.id).prepare_data_update_api(data)
            return sale_id.sudo().write(values)
        else:
            raise ValidationError('No record updated.')
