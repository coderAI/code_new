from logging import getLogger

from openerp.osv import osv
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.base.ir.ir_actions import VIEW_TYPES


_logger = getLogger(__name__)
VIEW_TYPE = ('hrs_calendar', _('hrs Calendar'))
VIEW_TYPES.append(VIEW_TYPE)


class ir_ui_view(osv.Model):
    _inherit = 'ir.ui.view'

    def __init__(self, pool, cr):
        res = super(ir_ui_view, self).__init__(pool, cr)
        select = [k for k, v in self._columns['type'].selection]
        if VIEW_TYPE[0] not in select:
            self._columns['type'].selection.append(VIEW_TYPE)
        return res


ir_ui_view()