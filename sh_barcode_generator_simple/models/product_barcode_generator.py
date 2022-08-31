# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _
import re
import math
from odoo.exceptions import UserError
from setuptools.dist import sequence

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    field_checkbox = fields.Boolean(string="Genrate Barcode On ProductS")
 
class ResCompany(models.Model):
    _inherit = 'res.company'

    # When New Product Created than Barcode auto generates    
    generate_barcode_on_product = fields.Boolean(string="Generate Product Barcode On Product Create?")



def ean_checksum(eancode):
    """returns the checksum of an ean string of length 13, returns -1 if
    the string has the wrong length"""
    if len(eancode) != 13:
        return -1
    oddsum = 0
    evensum = 0
    eanvalue = eancode
    reversevalue = eanvalue[::-1]
    finalean = reversevalue[1:]

    for i in range(len(finalean)):
        if i % 2 == 0:
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
    total = (oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10.0)) % 10
    return check


def check_ean(eancode):
    """returns True if eancode is a valid ean13 string, or null"""
    if not eancode:
        return True
    if len(eancode) != 13:
        return False
    try:
        int(eancode)
    except:
        return False
    return ean_checksum(eancode) == int(eancode[-1])


def generate_ean(ean):
    """Creates and returns a valid ean13 from an invalid one"""
    if not ean:
        return "0000000000000"
    ean = re.sub("[A-Za-z]", "0", ean)
    ean = re.sub("[^0-9]", "", ean)
    ean = ean[:13]
    if len(ean) < 13:
        ean = ean + '0' * (13 - len(ean))
        return ean[:-1] + str(ean_checksum(ean))     

class ProductTemplate1(models.Model):
    _inherit = 'product.template'    
    

    def action_generate_barcode(self):
        if self:
            new_barcode = ''                                       

            for record in self:    
                if record.user_has_groups('sh_barcode_generator_simple.group_barcode_generator'):
                                
                    if record.id and not record.barcode:
                        new_barcode = generate_ean(str(self.id))  # self.generate_barcode_random_num(str(random_str)) 
        
                        if not record.barcode:  # Overwrite existing
                            record.barcode = generate_ean(str(self.id))
                        else:
                            if record.barcode :  # If barcode exists,then don't overwrite, Else generate New
                                record.update({'barcode': generate_ean(str(self.id))})
    
    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if vals.get('barcode', False) == False:
            if self.user_has_groups('sh_barcode_generator_simple.group_barcode_generator'):
                if self.env.user.company_id.generate_barcode_on_product == True:
                    ean = generate_ean(str(res.id))
                    res.barcode = ean
        return res  

    
class ProductProduct1(models.Model):
    _inherit = 'product.product'    
    
    # _sql_constraints = [
    #     ('barcode_uniq', '(barcode)', " !"),]
    
    
    @api.model
    def create(self, vals):
        res = super(ProductProduct1, self).create(vals)
        for val in vals:
            if vals.get("barcode", False) == False:
                if self.user_has_groups('sh_barcode_generator_simple.group_barcode_generator'):
                    if self.env.user.company_id.generate_barcode_on_product == True:
                        for re in res:            
                            ean = generate_ean(str(re.id))
                            re.barcode = ean
        return res  


    def action_generate_barcode(self):
        if self:
            for record in self:
#                 ean = generate_ean(str(rec.id))
#                 rec.barcode = ean
        
                if record.user_has_groups('sh_barcode_generator_simple.group_barcode_generator'):
                                
                    new_barcode = ''                                       
                    if record.id and not record.barcode:
                        new_barcode = generate_ean(str(self.id))  # self.generate_barcode_random_num(str(random_str)) 
        
                        if record.barcode:  # Overwrite existing
                            record.barcode = new_barcode 
                                
                        else:
                            if not record.barcode :  # If barcode exists,then don't overwrite, Else generate New
                                record.barcode = new_barcode


        
class GenerateProductBarcode(models.Model):
    _name = 'generate.product.barcode'    
    _description = 'Generate Product Barcode'

    # Generate Barcode for Existing Product
    overwrite_existing = fields.Boolean("Overwrite Barcode If Exists")
   

    def generate_barcode(self):
        
        if self.user_has_groups('sh_barcode_generator_simple.group_barcode_generator'):
       
            context = dict(self._context or {})
            active_ids = context.get('active_ids', []) or []
            active_model = context.get('active_model', []) or []
    
            if active_model == 'product.product':              
                for record in self.env['product.product'].browse(active_ids):
                            
                    new_barcode = ''                                       
                    if record.id:
                        for recorded in record:
                            new_barcode = generate_ean(str(record.id))  # self.generate_barcode_random_num(str(random_str)) 
                            if self.overwrite_existing == True:  # Overwrite existing
                                record.barcode = new_barcode 
                                
                            else:
                                if not record.barcode :  # If barcode exists,then don't overwrite, Else generate New
                                    record.barcode = new_barcode
                                
            elif active_model == 'product.template':
                for record in self.env['product.template'].browse(active_ids):                        
                    new_barcode = ''                                       
                    if record.id:
                        for recorded in record:
                            new_barcode = generate_ean(str(record.id))  # self.generate_barcode_random_num(str(random_str)) 
                        
                            if self.overwrite_existing == True:  # Overwrite existing
                                record.barcode = new_barcode
                                
                            else:
                                if not record.barcode :  # If barcode exists,then don't overwrite, Else generate New
                                    record.barcode = new_barcode
            return {'type': 'ir.actions.act_window_close'}  
                     
        else:
            raise UserError("You have not Access to generate the Barcode please contact to Administrator.")
