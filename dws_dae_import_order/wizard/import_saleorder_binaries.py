# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from multiprocessing import resource_tracker
import random
import io
import xlrd
import babel
import logging
import tempfile
import binascii
import re
import time
from io import StringIO
from datetime import date, datetime
from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning, UserError, ValidationError
import threading
_logger = logging.getLogger(__name__)

try:
	import csv
except ImportError:
	_logger.debug('Cannot `import csv`.')
try:
	import xlwt
except ImportError:
	_logger.debug('Cannot `import xlwt`.')
try:
	import cStringIO
except ImportError:
	_logger.debug('Cannot `import cStringIO`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')


class SaleOrderCounter():
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def get_count(self):
        return self.count

class ImportSaleorder(models.TransientModel):
	_name = 'import.saleorder'
	_description = 'Import Saleorder'

	errors = []
	# pricelist_name, pricelist_currency = "" , ""

	#file_type = fields.Selection([('CSV', 'CSV File'),('XLS', 'XLS File')],string='File Type', default='CSV')
	file = fields.Binary(string="Upload File")

	# mandatory_fields_sale_order = [b'Contract Name', b'Customer', b'Company', b'Pricelist', b'Order Lines/Product Template/Internal Reference',
	# 	 b'Order Lines/Quantity', b'Order Lines/Unit Price', b'Internal Reference', b'Name', b'Barcode', b'NSN', b'Purchase Unit of Measure',
	# 	  b'Unit of Measure', b'Product Conditions/Code', b'Cost', b'Product Type', b'Routes', b'company_id', b'Tracking', b'Vendor',
	# 	   b'Product Template/Internal Reference', b'Vendor Product Code', b'Currency', b'Company', b'Quantity', b'Price']
	
	mandatory_fields_sale_order = ['Contract Name', 'Customer', 'Company', 'Pricelist', 'Order Lines/Product Template/Internal Reference',
		 'Order Lines/Quantity', 'Order Lines/Unit Price', 'Internal Reference', 'Name', 'Barcode', 'NSN', 'Purchase Unit of Measure',
		  'Unit of Measure', 'Product Conditions/Code', 'Cost', 'Product Type', 'Routes','company_id', 'Tracking', 'Vendor',
		   'Product Template/Internal Reference', 'Vendor Product Code', 'Vendor Product Name', 'Currency', 'Company','Quantity','Price']

	fields_sale_order_line = [b'Order Lines/Product Template/Internal Reference', b'Order Lines/Quantity',  b'Order Lines/Unit Price',
		   b'Internal Reference',b'Name',b'Barcode',b'NSN',	b'Purchase Unit of Measure', b'Unit of Measure',b'Product Conditions/Code',
			b'Cost', b'Product Type', b'Routes', b'company_id',	b'Tracking',b'Vendor',b'Product Template/Internal Reference',
			b'Vendor Product Code',	b'Vendor Product Name',	b'Currency',b'Company',	b'Quantity',b'Price']

	# def progressbar(self, sale_orders, counter, label):
	# 	j = 1
	# 	for sale_order in self.web_progress_iter(sale_orders, msg=label):
	# 		j = j + 1
	# 		while 1 == 1:
	# 			time.sleep(0.005)
	# 			if counter.get_count() > j or counter.get_count() == len(sale_orders):
	# 				break;

	def import_saleorders(self):
		
		batch_id = int(time.time())	
		error_bool = True;	
		sale_order_name = ""
		pricelist_name, pricelist_currency = "" , ""

		if not self.file:
			raise ValidationError(_("Please Upload File to Import Sale orders !"))

		try:
			file = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
			file.write(binascii.a2b_base64(self.file))
			file.seek(0)
			values = {}
			workbook = xlrd.open_workbook(file.name)
			sheet = workbook.sheet_by_index(0)
		except Exception:
			raise ValidationError(_("Please Select Valid File Format !"))

		#progress = self.progressbar(range(sheet.nrows),counter,"Importing sale orders ...")
		# x = threading.Thread(target=self.progressbar,args=(range(sheet.nrows-1), counter, "Validating data ..."))
		# x.start()

		
		
		
		for row_no in range(sheet.nrows):

			values = list(map(lambda row:row.value, sheet.row(row_no)))
			sale_order_line_values = values[4:]
			
			self.check_missing_fields(row_no, values)
			self.raise_error(enable_error_message = error_bool)
			break	
			
			self.check_values_SO(row_no, values)
			self.raise_error(enable_error_message = error_bool)
			
			self.check_values_SO_line(row_no, sale_order_line_values)
			self.raise_error(enable_error_message = error_bool)

			if row_no == 1:
				pricelist_name, pricelist_currency = self.check_if_pricelist_exists(row_no, values)
				self.raise_error(enable_error_message = error_bool)
				print("pricelist_name, pricelist_currency", pricelist_name, pricelist_currency)


			self.check_if_vendor_exist(row_no, sale_order_line_values)
			self.raise_error(enable_error_message = error_bool)

			self.check_if_partner_exist(row_no, values)
			self.raise_error(enable_error_message = error_bool)

			self.check_if_product_exists(row_no, values)
			self.raise_error(enable_error_message = error_bool)

			sale_order_name = self.check_latest_sale_order_line_create_new_name(row_no, values)
			self.raise_error(enable_error_message = error_bool)

			self.create_Sale_order(row_no, values, sale_order_name)
			self.raise_error(enable_error_message = error_bool)

			self.add_sale_order_lines(row_no, values, sale_order_name)
			self.raise_error(enable_error_message = error_bool)

			#add sale order line to sale order		
		return 0

	def check_missing_fields(self, row_no, values):
		print("row_no" + str(row_no))
		print("values = " + str(values))
		print("\n\n\nfields" + str(self.mandatory_fields_sale_order))
		if row_no == 0:
			for index, field in enumerate(self.mandatory_fields_sale_order):
				if str(field) not in values:
					print(str(index) + " val : " + values[index] + " field : " + str(field))
					self.errors.append("Missing mandatory field : " + str(field))
	
	def check_values_SO(self,row_no, values):
		if row_no == 2:
			# if len(values[self.mandatory_fields_sale_order(b'NSN')]) != 16: #length of NSN = 16 with dashes
				# self.errors.append("[" + str(row_no) + "] NSN has to be 13 characters")
			for index, value in enumerate(values):
				if value == '':
					self.errors.append("Missing sale order value for field : " + str(values[index]))				


	def check_values_SO_line(self,row_no, values):
		if row_no > 1:
			if len(values[self.fields_sale_order_line.index(b'NSN')]) != 16: #length of NSN = 16 with dashes
				self.errors.append("[" + str(row_no) + "] NSN has to be 13 characters")
			for index, value in enumerate(values):
				if value == '':
					self.errors.append("[" + str(row_no) + "][" + str(index) + "]Missing sale order line value for field : " + str(self.fields_sale_order_line[index]))
				

	
	def check_if_pricelist_exists(self, row_no, values):
		pricelist, pricelist_name, pricelist_currency = "", "", ""
		pricelist = values[self.mandatory_fields_sale_order.index(b'Pricelist')]
		pricelist_name, pricelist_currency = pricelist.split(" (")[0], pricelist.split("(")[1]
		pricelist_currency = pricelist_currency.split(")")[0]
		
		if not self.env['product.pricelist'].search([('name','=',pricelist_name)]): #,('currency_id.name','=',pricelist_currency)]):
			self.errors.append("Pricelist" + str(pricelist) + " does not exist")
			return pricelist_name, pricelist_currency
		
		return pricelist_name, pricelist_currency

	def check_if_vendor_exist(self, row_no, values):
		if row_no > 1:
			vendor = values[self.fields_sale_order_line.index(b'Vendor')]
			if not self.env['res.partner'].search([('name','=',vendor)]):
				self.errors.append("Vendor " + str(vendor) + " does not exist")

	def check_if_partner_exist(self, row_no, values):
		if row_no == 1:
			partner = values[1]
			if not self.env['res.partner'].search([('name','=',partner)]):
				self.errors.append("Partner " + str(partner) + " does not exist")
				# self.env['res.partner'].create({'name': partner})	


	def check_if_product_exists(self, row_no, values):
		if row_no >= 1:
			nsn=values[self.fields_sale_order_line.index(b'NSN')]
			barcode=values[self.fields_sale_order_line.index(b'Barcode')]

			if not self.env['product.template'].search([('nsn','=',nsn)]) and not self.env['product.template'].search([('barcode','=',barcode)]):
				self.create_missing_products(values)
				return True
			elif self.env['product.template'].search([('nsn','=',nsn)]) and not self.env['product.template'].search([('barcode','=',barcode)]):
				self.errors.append("Product with NSN " + str(nsn) + " already exists, but has no or a different barcode")
				return False
			elif not self.env['product.template'].search([('nsn','=',nsn)]) and self.env['product.template'].search([('barcode','=',barcode)]):
				self.errors.append("Product with barcode " + str(barcode) + " already exists, but has no or a different NSN")
				return False
			else:
				return True

		# track_id = self.env['product.template'].search([('tracking','=',sale_order_line_values[fields_sale_order_line.index(b'Tracking')])]).id
		track_id = self.env['product.template'].search([('tracking','=','lot')]).id
		print("track_id = " + str(track_id))

	
	def create_missing_products(self, values):
		track_id = self.env['product.template'].search([('tracking','=','lot')]).id
		print("track_id = " + str(track_id))

		product_type_string = values[self.fields_sale_order_line.index(b'Product Type')]
		if product_type_string == 'Consumable':
			product_type = 'consu'
		elif product_type_string == 'Service':
			product_type = 'service'
		elif product_type_string == 'Storable Product':
			product_type = 'product'
		
		tracking_string = values[self.fields_sale_order_line.index(b'Tracking')]
		if tracking_string == 'By Unique Serial Number':
			tracking_type = 'serial'
		elif tracking_string == 'By Lots':
			tracking_type = 'lot'
		else:
			tracking_type = 'none'

		self.env['product.template'].create({
			'nsn': values[self.fields_sale_order_line.index(b'NSN')], 
			'default_code':values[self.fields_sale_order_line.index(b'Internal Reference')],
		    'name': values[self.fields_sale_order_line.index(b'Name')],
			'barcode': values[self.fields_sale_order_line.index(b'Barcode')],
			'uom_id': self.env['uom.uom'].search([('name','=',values[self.fields_sale_order_line.index(b'Unit of Measure')])]).id,
			'uom_po_id': self.env['uom.uom'].search([('name','=',values[self.fields_sale_order_line.index(b'Purchase Unit of Measure')])]).id,
			'product_conditions':self.env['product.condition'].search([('code','=',values[self.fields_sale_order_line.index(b'Product Conditions/Code')])]).id,
			'standard_price':values[self.fields_sale_order_line.index(b'Cost')],
			'company_id':self.env['res.company'].search([('name','=',values[self.fields_sale_order_line.index(b'company_id')])]).id,
			'detailed_type':product_type,
			# 'tracking':'serial',
			# self.env['product.template'].search([('tracking','=',sale_order_line_values[fields_sale_order_line.index(b'Tracking')])]).id,
			#sale_order_line_values[fields_sale_order_line.index(b'Tracking')],				
			# 'route_ids':[(6,0,[self.env['stock.location.route'].search([('name','=',sale_order_line_values[fields_sale_order_line.index(b'Routes')])]).id])],			
			'list_price':values[self.fields_sale_order_line.index(b'Price')],
			'seller_ids': [(0, 0, {
									'name': self.env['res.partner'].search([('name','=',values[self.fields_sale_order_line.index(b'Vendor')])]).id,
									'product_code': values[self.fields_sale_order_line.index(b'Vendor Product Code')],
									'product_name': values[self.fields_sale_order_line.index(b'Vendor Product Name')],
									'currency_id': self.env['res.currency'].search([('name','=',values[self.fields_sale_order_line.index(b'Currency')])]).id,
									'price': values[self.fields_sale_order_line.index(b'Cost')],
									'product_uom': self.env['uom.uom'].search([('name','=', values[self.fields_sale_order_line.index(b'Purchase Unit of Measure')])]).id,
				
			})] 
			})

	def check_latest_sale_order_line_create_new_name(self, row_no, values):
		if row_no == 0:
			#retrieve latest saleorder number where the names starts with'SO' & 'DPT
			sale_order_name_daedaelus = self.env['sale.order'].search([('name','like','SO')], order='id desc', limit=1).name
			sale_order_name_DPT = self.env['sale.order'].search([('name','like','DPT')], order='id desc', limit=1).name

			#check if sale_order_name_daedaelus is a boolean
			if sale_order_name_daedaelus != False:
				sale_order_name_daedaelus = sale_order_name_daedaelus.split('SO')[1]
				sale_order_name_daedaelus = int(sale_order_name_daedaelus) + 1		
				sale_order_name_daedaelus = 'SO' + str(sale_order_name_daedaelus)

			if sale_order_name_DPT != False:
				sale_order_name_DPT = sale_order_name_DPT.split('DPT')[1]
				sale_order_name_DPT = int(sale_order_name_DPT) + 1
				sale_order_name_DPT = 'DPT' + str(sale_order_name_DPT)
			
			if sale_order_name_DPT == False and sale_order_name_daedaelus == False:
				sale_order_name_daedaelus = 'SO1'
				sale_order_name_DPT = 'DPT1'

			print("sale_order_name_daedaelus = " + str(sale_order_name_daedaelus))
			print("sale_order_name_DPT = " + str(sale_order_name_DPT))
			print("company id = " +str(values[self.mandatory_fields_sale_order.index(b'company_id')]))
			#if the company from values is Daedaelus, then create a sale order with the name 'SO' + the latest sale order number
			if values[self.mandatory_fields_sale_order.index(b'company_id')] == 'Daedaelus':
				return sale_order_name_daedaelus
			#if the company from values is DPT, then create a sale order with the name 'DPT' + the latest sale order number
			elif values[self.mandatory_fields_sale_order.index(b'company_id')] == 'Daedalus Project & Trade':
				return sale_order_name_DPT
			else:
				return sale_order_name_daedaelus


	def create_Sale_order(self, row_no, values, sale_order_name):
		if row_no == 1:
			SO = self.env['sale.order']		
			SO.create({'name': sale_order_name, 
				'partner_id': self.env['res.partner'].search([('name','=',values[1])]).id,
				'contract_name': values[0],
				'pricelist_id': self.env['product.pricelist'].search([('name','=',self.pricelist_name)]).id,
				#partner_invoice_id
				#partner_shipping_id
				# order_line: [(0, 0, {
					# 'product_id': self.env['product.product'].search([('name','=',values[self.fields_sale_order_line.index(b'Product')])]).id,
				})

	def add_sale_order_lines(self, row_no, values, sale_order_name):
		if row_no >= 1:
			order_id = self.env['sale.order'].search([('name','=',sale_order_name)]).id	
			product_naam = self.env['product.product'].search([('nsn','=',values[self.fields_sale_order_line.index(b'NSN')])]).name
			print("product_naam = " + str(product_naam))
			if row_no == 1:
				order_id = self.env['sale.order'].search([('name','=',sale_order_name)]).id
				self.env['sale.order.line'].create({
						'order_id': order_id,						
						'product_id': self.env['product.product'].search([('nsn','=',values[self.fields_sale_order_line.index(b'NSN')])]).id,
						'name': self.env['product.product'].search([('nsn','=',values[self.fields_sale_order_line.index(b'NSN')])]).name,
						'product_uom_qty': values[self.fields_sale_order_line.index(b'Quantity')] ,
					})
			elif row_no > 1:
				self.env['sale.order.line'].create({
					'order_id': order_id,
					'product_id': self.env['product.product'].search([('nsn','=',values[self.fields_sale_order_line.index(b'NSN')])]).id,
					'name': self.env['product.product'].search([('nsn','=',values[self.fields_sale_order_line.index(b'NSN')])]).name,
					'product_uom_qty': values[self.fields_sale_order_line.index(b'Quantity')],
					})
	
	def check_if_vendor_exists(self, values):
		vendor = values[self.fields_sale_order_line.index(b'Vendor')]
		if not self.env['res.partner'].search([('name','=',vendor)]):
			self.errors.append("Vendor " + str(vendor) + " does not exist")
	
	def print_all_values(self, values,fields):
		for index, value in enumerate(values):
			print(fields[index] + " = " + str(value))
		
	def raise_error(self, enable_error_message):
		if len(self.errors) > 0 and enable_error_message:
			all_errors = "\n".join(self.errors)
			raise ValidationError(all_errors)






