# -*-coding:utf-8-*-
import logging
import datetime

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'


        
    def _get_day_of_month(self, cr, uid, context = None):
        return (
                ('1','01'),('2','02'),('3','03'),('4','04'),
                ('5','05'),('6','06'),('7','07'),('8','08'),
                ('9','09'),('10','10'),('11','11'),('12','12'),
                ('13','13'),('14','14'),('15','15'),('16','16'),
                ('17','17'),('18','18'),('19','19'),('20','20'),
                ('21','21'),('22','22'),('23','23'),('24','24'),
                ('25','25'),('26','26'),('27','27'),('28','28'),
                ('29','29'),('30','30'),('31','31')
                )
        
    def _get_age(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        if ids:
            datas = self.read(cr, uid, ids, ['year_of_birth'])
            for data in datas:
                year_of_birth = data.get('year_of_birth',0)
                if year_of_birth:
                    current_year = datetime.date.today().year
                    res[data['id']] = current_year - int(year_of_birth)
                else:
                    res[data['id']] = 0
        return res

    def _get_id_number_info(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        document_obj = self.pool.get('vhr.personal.document')
        for res_id in ids:
            res[res_id] = False
            emp_ids = emp_obj.search(cr, uid, [('address_home_id', '=', res_id)], context=context)
            document_ids = document_obj.search(cr, uid, [('employee_id', 'in', emp_ids),
                                                         ('document_type_id.code', '=', 'ID')], context=context)
            if document_ids:
                res_pd = document_obj.browse(cr, uid, document_ids[0], context=context)
                id_number = res_pd.number
                res[res_id] = id_number
        return res
        
    _columns = {
        'ward': fields.char('Ward'),
        'city': fields.many2one('res.city', 'City'),
        'district_id': fields.many2one('res.district', 'District', ondelete='restrict'),
        'street': fields.char('Street', size=256),
        'street2': fields.char('Street2', size=256),
        'temp_address': fields.char('Address', size=256),
        'temp_ward': fields.char('Ward'),
        'temp_city_id': fields.many2one('res.city', 'City', ondelete='restrict'),
        'temp_district_id': fields.many2one('res.district', 'District', ondelete='restrict'),
        'certificates': fields.one2many('vhr.certificate.info', 'partner_id', 'Certificates/Degrees'),
        
        'gender': fields.selection([('male','Male'),
                                    ('female','Female')], 'Gender'),
                 
        'status': fields.selection([('alive','Alive'),
                                    ('dead','Dead')], 'Status'),
         
        'identity_number': fields.function(_get_id_number_info, type='char', string='Identity Number'),
        'career_id': fields.many2one('vhr.dimension', 'Career', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'CAREER'), ('active', '=', True)]),
        'working_place': fields.char('Working Place', size=64),
        'notes': fields.text('Notes'),
        'day_of_birth': fields.selection(_get_day_of_month, 'Day of Birth'),
        
        'month_of_birth': fields.selection([('1','01'),('2','02'),('3','03'),('4','04'),
                                            ('5','05'),('6','06'),('7','07'),('8','08'),
                                            ('9','09'),('10','10'),('11','11'),('12','12')], 'Month of Birth'),
                
        'year_of_birth': fields.char('Year of Birth', size=16),
        'age': fields.function(_get_age, type='integer', string='Age'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _name), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    def _get_default_country_id(self, cr, uid, context=None):
        m = self.pool.get('ir.model.data')
        return m.get_object(cr, uid, 'base', 'vn').id

    _defaults = {
        'status': 'alive',         
        'country_id': _get_default_country_id
    }
    
#     _unique_insensitive_constraints = [{'name': "Name-Phone-Identity Number are already exist!",
#                                         'phone': "Name-Phone-Identity Number are already exist!",
#                                         }]
    
    #Pay attention when override onchange_birthday in res.partner
    #Because vhr_employee_partner.onchange_birthday() go to it
    def onchange_birthday(self, cr, uid, ids, day, month, year, context=None):
        res = {}
        warning = {}
        if not year:
            res['age'] = 0
            if day and month:
                max_day = self.get_max_day_of_month(cr, uid, month, year, context)
                if int(day) > int(max_day):
                    res['day_of_birth'] = max_day
        elif year:
            today = datetime.date.today()
            
            try:
                year = int(year)
                
                res['age'] = today.year - year
                if year > today.year or year < today.year - 200:
                    warning = {'title': 'Warning',
                                'message': 'Year of Birth have to lower or equal current year and greater %s !'% (today.year - 200)}
                    res['year_of_birth'] = ''
                    res['age'] = 0
                elif day and month:
                    max_day = self.get_max_day_of_month(cr, uid, month, year, context)
                    if int(day) > int(max_day):
                        res['day_of_birth'] = max_day
                 
            except:
                warning = {'title': 'Warning',
                            'message': 'Incorrect format ! (e.g: %s)'%(today.year-50)}
                res['year_of_birth'] = ''
         
        return {'value': res, 'warning': warning}
    
    def get_max_day_of_month(self, cr, uid, month, year, context=None):
        if int(month) in [1, 3, 5, 7, 8, 10, 12]:
            return '31'
        if int(month) in [4,6,9,11]:
            return '30'
        if month == '2' and not year:
            return '29'
        else:
            year = int(year)
            if (year % 4) == 0:
               if (year % 100) == 0:
                   if (year % 400) == 0:
                       return '29'
                   else:
                       return '28'
               else:
                   return '29'
            else:
               return '28'
        
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        
        args_compute = self.get_search_argument(cr, uid, context)
        args_new.extend(args_compute)
        
        res = super(res_partner, self).name_search(cr, uid, name, args_new, operator, context, limit)
        
        return res
     
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        args_compute = self.get_search_argument(cr, uid, context)
        args.extend(args_compute)
        
        res =  super(res_partner, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def get_search_argument(self, cr, uid, context=None):
        if not context:
            context = {}
        args = []
        if not context.get('search_company', False):
            args = [('is_company', '=', False)]
        if context.get('search_for_not_system_and_company', False) == True:
            
            #Get partner_ids of employee in group_system
            employee_pool = self.pool.get('hr.employee')
            system_partner_ids = []
            system_user_ids = employee_pool.get_list_users_of_group(cr, uid, 'hrs_group_system', context)
            #get employee belong to hrs_group_system
            system_emp_ids = employee_pool.search(cr, uid, [('user_id','in',system_user_ids)])
            if system_emp_ids:
                employees = employee_pool.read(cr, uid, system_emp_ids, ['address_home_id'])
                #Get partner_ids in system employees
                for employee in employees:
                    if employee.get('address_home_id', False):
                        system_partner_ids.append(employee['address_home_id'][0])
            
            #Down show admin
            admin_partner_ids = super(res_partner, self).search(cr, uid, [('name','ilike','administrator')])
            system_partner_ids += admin_partner_ids
            args.append(('id', 'not in', system_partner_ids))
            
        return args
           
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(res_partner, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        if context is None:
            context = {}
        address_format = address.country_id and address.country_id.address_format or \
                         "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'district_name': address.district_id and address.district_id.name or '',
            'city_name': address.city and address.city.name or '',
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
            'company_name': address.parent_id and address.parent_id.name or '',
        }
        # tuannh3 doi cach lay trong man hinh hr emloyee
        if context.has_key('vhr_human_resource'):
            address_format = "%(street)s\n%(street2)s\n%(district_name)s %(city_name)s %(zip)s\n%(country_name)s"
            if address.mobile and address.phone:
                args['mobile'] = address.mobile
                args['phone'] = address.phone
                address_format = address_format + '\n%(mobile)s - %(phone)s'
            elif address.mobile:
                args['mobile'] = address.mobile
                address_format = address_format + '\n%(mobile)s'
            elif address.phone:
                args['phone'] = address.phone
                address_format = address_format + '%(phone)s'
            if address.email:
                args['email'] = address.email
                address_format = address_format + '\n%(email)s'
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    def check_permission(self, cr, uid, group, context=None):
        user_obj = self.pool.get('res.users')
        groups = user_obj.get_groups(cr, uid)
        groups = list(set(groups))
        group_access = [group]
        group_not_access = list(set(groups) - set(group_access))
        is_access = len(groups) - len(group_not_access)
        if is_access:
            return True
        return False


res_partner()