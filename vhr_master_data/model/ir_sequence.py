# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class ir_sequence(osv.osv):
    _name = 'ir.sequence'
    _inherit = 'ir.sequence'
    _description = 'ir.sequence'

    _columns = {
                'company_group_id': fields.many2one('vhr.company.group', 'Company Group', ondelete='restrict'),
    }
    
    def _next_with_company_group(self, cr, uid, seq_ids, context=None):
        if not seq_ids:
            return False
        if context is None:
            context = {}
        sequences = self.read(cr, uid, seq_ids, ['name','implementation','number_next','prefix','suffix','padding'])
        seq = sequences[0]
        if seq['implementation'] == 'standard':
            cr.execute("SELECT nextval('ir_sequence_%03d')" % seq['id'])
            seq['number_next'] = cr.fetchone()
        else:
            cr.execute("SELECT number_next FROM ir_sequence WHERE id=%s FOR UPDATE NOWAIT", (seq['id'],))
            cr.execute("UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s ", (seq['id'],))
        d = self._interpolation_dict()
        try:
            interpolated_prefix = self._interpolate(seq['prefix'], d)
            interpolated_suffix = self._interpolate(seq['suffix'], d)
        except ValueError:
            raise osv.except_osv(_('Warning'), _('Invalid prefix or suffix for sequence \'%s\'') % (seq.get('name')))
        return interpolated_prefix + '%%0%sd' % seq['padding'] % seq['number_next'] + interpolated_suffix
    
    def next_by_code_with_company_group(self, cr, uid, sequence_code, company_group_id, context=None):
        self.check_access_rights(cr, uid, 'read')
        ids = self.search(cr, uid, ['&', ('code', '=', sequence_code), ('company_group_id', '=', company_group_id)])
        return self._next_with_company_group(cr, uid, ids, context)
    
    def get_temp_next_by_code_with_company_group(self, cr, uid, sequence_code, company_group_id, context=None):
        if context is None:
            context = {}
        
        self.check_access_rights(cr, uid, 'read')
        seq_ids = self.search(cr, uid, ['&', ('code', '=', sequence_code), ('company_group_id', '=', company_group_id)])
        
        sequences = self.read(cr, uid, seq_ids, ['name','implementation','number_next','prefix','suffix','padding','number_increment'])
        seq = sequences[0]
        if seq['implementation'] == 'standard':
            cr.execute("SELECT last_value+increment_by from ir_sequence_%03d " % seq['id'])
            seq['number_next'] = cr.fetchone()
        else:
            cr.execute("SELECT number_next FROM ir_sequence WHERE id=%s FOR UPDATE NOWAIT", (seq['id'],))
            cr.execute("SELECT number_next+number_increment from ir_sequence WHERE id=%s ", (seq['id'],))
            seq['number_next'] = cr.fetchone()
        d = self._interpolation_dict()
        try:
            interpolated_prefix = self._interpolate(seq['prefix'], d)
            interpolated_suffix = self._interpolate(seq['suffix'], d)
        except ValueError:
            raise osv.except_osv(_('Warning'), _('Invalid prefix or suffix for sequence \'%s\'') % (seq.get('name')))
        return interpolated_prefix + '%%0%sd' % seq['padding'] % seq['number_next'] + interpolated_suffix



ir_sequence()