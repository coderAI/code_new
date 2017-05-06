openerp_vhr_base_data = function (instance) {
    var _t = instance.web._t;
    instance.web.DataSet.include({
    	name_search: function (name, domain, operator, limit) {
        	name = name.replace(/\s+/g, " ");
        	name = name.replace(/^\s+|\s+$/g, "");
            return this._model.call('name_search', {
                name: name || '',
                args: domain || false,
                operator: operator || 'ilike',
                context: this._model.context(),
                limit: limit || 0
            });
        },
    });
    
};