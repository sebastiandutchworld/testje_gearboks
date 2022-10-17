# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Dutch World Import",
    'summary': "Change import sale orders",
    'version': '0.0.1',
    'category': 'Extra Tools',
    'license': 'GPL-3',
    'description': """
This module adds an ability to import csv/excel and modified/create contacts from sale order
    """,
    'depends': ['base', 'sale'],
    'data': [
				'security/ir.model.access.csv',
				'wizard/import_saleorder_view.xml',
				'views/import_saleorder_menu.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}