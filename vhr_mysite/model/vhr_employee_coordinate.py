# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_employee_coordinate(osv.osv):
    _name = 'vhr.employee.coordinate'
    _columns = {
        'name': fields.char('Name'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'lat': fields.float('Latitude', digits=(12,12)),
        'long': fields.float('Longtitude', digits=(12,12)),
        #Check if user chose their coordinate
        'active': fields.boolean('Active'),
        'note': fields.text('Note'),
        'address': fields.text('Address'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name)]),
    
    }
    _defaults = {
        'active': True
    }
    
    _unique_insensitive_constraints = [{'employee_id': "Employee is already exist!"}]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code' : ''}
        
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
            res['employee_code'] = employee.get('code', '')
        
        return {'value': res}
    
    
    def get_coordinate(self, cr, uid, context=None):
        """
        Return coordinate of user
        """
        if not context:
            context = {}
            
        res = {'lat_value': 10.76425544270746, 'long_value': 106.65625512599945, 'is_updated': False,'origin_address': ''}
        
        emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if context.get('employee_id', False):
            emp_ids = [context['employee_id']]
        if emp_ids:
            coor_ids = self.search(cr, uid, [('employee_id','in',emp_ids)])
            if coor_ids:
                coor = self.read(cr, uid, coor_ids[0], ['lat','long','address'])
                res['lat_value'] = coor.get('lat', 0)
                res['long_value'] = coor.get('long',0)
                res['is_updated'] = True
                res['origin_address'] = coor.get('address','')
        
        return res
    
    def get_all_coordinate(self, cr, uid, context=None):
        res = []
        
        sql = "SELECT employee_id from vhr_employee_coordinate where active=True"
        cr.execute(sql)
        emp_ids = [group[0] for group in cr.fetchall()]
        if emp_ids:
            for employee_id in emp_ids:
                item = self.get_coordinate(cr, uid, {"employee_id": employee_id})
                res.append(item)
        
        return res
    
    def get_campus_coordinate(self, cr, uid, context=None):
        address = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_mysite_hrs_campus_address') or ''
        address = address.split(',')
        res = {'lat_value': 10.758378, 'long_value':106.745768}
        
        try:
            if address:
                res['lat_value'] = float(address[0])
                res['long_value'] = float(address[1])
        except Exception as e:
            print e
        
        return res
        
    
    def create_update_coordinate(self, cr, uid, post, context=None):
        try:
            if post.get('lat_value', False) and post.get('long_value', False):
                vals = {'lat': float(post.get('lat_value',0)),
                        'long': float(post.get('long_value',0)),
                        'address': post.get('origin_address_default', ''),
                        'is_updated': True}
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                coor_ids = self.search(cr, uid, [('employee_id','in',emp_ids),
                                                 '|',('active','=',True),
                                                     ('active','=',False)])
                if coor_ids:
                    self.write(cr, uid, coor_ids, vals)
                elif emp_ids:
                    vals.update({'employee_id': emp_ids[0]})
                    self.create(cr, uid, vals)
        
        except Exception as e:
            print e
        
        return True
    


vhr_employee_coordinate()