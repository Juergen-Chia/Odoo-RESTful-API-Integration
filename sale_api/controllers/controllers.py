# -*- coding: utf-8 -*-
import json
import logging

from odoo import http, _, exceptions
from odoo.http import request
from odoo.addons.odoo_rest_api.controllers.controllers import OdooAPI


_logger = logging.getLogger(__name__)


def error_response(error, msg):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": 200,
            "message": msg,
            "data": {
                "name": str(error),
                "debug": "",
                "message": msg,
                "arguments": list(error.args),
                "exception_type": type(error).__name__
            }
        }
    }


class SaleOrderAPI(OdooAPI):
    """ Odoo API controller """

    # This is for single record function call
    @http.route(
        '/object/<string:model>/<string:rec_id>/<string:function>',
        type='json', auth='user', methods=["POST"], csrf=False)
    def call_obj_function(self, model, rec_id, function, **post):
        if model == 'sale.order':
            try:
                record = request.env[model].sudo().get_record_id(rec_id)
                rec_id = record.id
            except Exception as e:
                raise exceptions.ValidationError(e)
        else:
            rec_id = int(rec_id)
        return super(SaleOrderAPI, self).call_obj_function(model, rec_id, function, **post)
