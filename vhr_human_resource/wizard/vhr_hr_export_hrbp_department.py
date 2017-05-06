# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from datetime import datetime
from openerp.addons.report_xlsx.utils import _render  # @UnresolvedImport
from openerp.report import report_sxw  # @UnresolvedImport
from openerp.addons.report_xlsx import report_xlsx_utils  # @UnresolvedImport

class vhr_hr_export_hrbp_department(osv.osv_memory):
    _name = 'vhr.hr.export.hrbp.department'
    _description = ' Export HRBPs List'

    _columns = {
                'organization_class_id': fields.many2one('vhr.organization.class', 'Organization Class', ondelete='restrict'),
                'data': fields.binary('File', readonly=True),
                'department_ids': fields.many2many('hr.department', 'export_hr_hrbp_department_rel', 'export_id',
                                       'department_id', 'Department'),

    }
    
    def _get_default_organization_class_id(self, cr, uid, context=None):
        '''
         If user does not belong to vhr_cb_timesheet, set admin_id = login_user(because field admin_id only use by vhr_cb_timesheet
        '''
        organization_ids = self.pool.get('vhr.organization.class').search(cr, uid, [('level','=',3)])
        return organization_ids and organization_ids[0] or False
    
    _defaults = {
                 'organization_class_id': _get_default_organization_class_id,
                 }
    
    def onchange_organization_class_id(self, cr, uid, ids, organization_class_id, context=None):
        res = {}
        domain = {}
        if organization_class_id:
            res['department_ids'] = []
            domain['department_ids'] = "[('organization_class_id','=',organization_class_id)]"
        
        return {'value': res, 'domain': domain}
    
    
    def action_export(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
            
        department_ids = []
        if ids:
            record = self.read(cr, uid, ids[0], [])
            
            organization_class_id = record.get('organization_class_id', False) and record['organization_class_id'][0]
            department_ids = record.get('department_ids', [])
            
            dept_pool = self.pool.get('hr.department')
            if not department_ids and organization_class_id:
                department_ids = dept_pool.search(cr, uid, [('organization_class_id','=',organization_class_id)])
        
        data = {}
        data['ids'] = ids
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['active_ids'] = context.get('active_ids')
        data['param'] = department_ids
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_hrbp_department',
            'datas': data,
            'name': 'Export HRBPs List'
        }
                
                

vhr_hr_export_hrbp_department()

class rpt_hr_hrbp_department_xlsx_parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(rpt_hr_hrbp_department_xlsx_parser, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'datetime': datetime,
            'get_lines_data': self.get_department_data,
        })


    def get_department_data(self, cr, uid, department_ids, context=None):
        dept_pool = self.pool.get('hr.department')
        emp_pool = self.pool.get('hr.employee')
        datas = dept_pool.read(cr, uid, department_ids, ['complete_code','parent_id','hrbps','ass_hrbps','manager_id'], context=context)
        for data in datas:
            if data.get('parent_id', False):
                parent_id = data['parent_id'][0]
                parent = dept_pool.read(cr, uid, parent_id, ['complete_code'])
                data['parent_id'] = parent.get('complete_code','')
            
            if data.get('manager_id', False):
                data['manager_id'] = data['manager_id'][1]
            else:
                data['manager_id'] = ''
            
            if data.get('hrbps',[]):
                hrbps = emp_pool.read(cr, uid, data['hrbps'], ['name','login'])
                data['hrbps'] = [ (hrbp.get('name','')+' (' +hrbp.get('login','') + ')') for hrbp in hrbps]
                data['hrbps'] = '\n'.join(data['hrbps'])
            if data.get('ass_hrbps',[]):
                ass_hrbps = emp_pool.read(cr, uid, data['ass_hrbps'], ['name','login'])
                data['ass_hrbps'] = [ (ass_hrbps.get('name','')+' (' +ass_hrbps.get('login','') + ')') for ass_hrbps in ass_hrbps]
                data['ass_hrbps'] = '\n'.join(data['ass_hrbps'])
            
        return datas


class rpt_hr_hrbp_department_xlsx(report_xlsx_utils.generic_report_xlsx_base):
    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(rpt_hr_hrbp_department_xlsx, self).__init__(name, table, rml, parser, header, store)

        self.xls_styles.update({
            'fontsize_350': 'font: height 360;'
        })

    def get_header_c_specs(self):
        header_c_specs = [
            ('col1', 1, 15, 'text', 'Department', None, self.normal_style_bold_left_borderall),
            ('col2', 1, 15, 'text', 'Dept Head', None, self.normal_style_bold_left_borderall),
            ('col3', 1, 15, 'text', 'Parent Department', None, self.normal_style_bold_left_borderall),
            ('col4', 1, 25, 'text', 'HRBPs', None, self.normal_style_bold_left_borderall),
            ('col5', 1, 25, 'text', 'Assistant to HRBP', None, self.normal_style_bold_left_borderall),
        ]
        return header_c_specs

    def generate_xls_report(self, _p, _xs, data, objects, workbook):
        # wizard_data = _p.get_data()

        report_name = u'Export HRBPs Listt'

        ws = super(rpt_hr_hrbp_department_xlsx, self).generate_xls_report(_p, _xs, data,
                                                                         objects, workbook,
                                                                         report_name)

        self.wanted_list = ['A', 'B', 'C', 'D','E']
        
        self.col_specs_template = {
            'A': {
                'lines': [1, 15, 'text', _render("line.get('complete_code','')"), None, self.normal_style_left_borderall],
            },
            'B': {
                'lines': [1, 25, 'text', _render("line.get('manager_id','')"), None, self.normal_style_left_borderall],
            },

            'C': {
                'lines': [1, 15, 'text', _render("line.get('parent_id','')"), None, self.normal_style_left_borderall],
            },

            'D': {
                'lines': [1, 25, 'text', _render("line.get('hrbps','')"), None, self.normal_style_left_borderall],
            },

            'E': {
                'lines': [1, 25, 'text', _render("line.get('ass_hrbps','')"), None, self.normal_style_left_borderall],
            },

        }

        row_pos = 0
        # Header Title 1
        ws.set_row(row_pos, 22)
        header_c_specs = self.get_header_c_specs()
        row_data = self.xls_row_template(header_c_specs, [x[0] for x in header_c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data,
                                     row_style=self.normal_style_left_borderall, set_column_size=True)
        
        
        # Get department data
        get_lines_data = _p.get_lines_data(self.cr, self.uid, data['param'])
        stt = 0
        for line in get_lines_data:  # @UnusedVariable
            stt += 1
            c_specs = map(lambda x: self.render(x, self.col_specs_template, 'lines'), self.wanted_list)
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.normal_style_borderall, set_column_size=True)
            
        workbook.close()




rpt_hr_hrbp_department_xlsx('report.report_hrbp_department', 'vhr.hr.export.hrbp.department', parser=rpt_hr_hrbp_department_xlsx_parser)