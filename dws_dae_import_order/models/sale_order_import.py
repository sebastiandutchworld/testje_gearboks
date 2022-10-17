from odoo import api, fields, models
import logging
import psycopg2
_logger = logging.getLogger(__name__)


class SaleInherit(models.Model):
    _inherit = 'sale.order'

    import_batch = fields.Integer('Import batch ID')
