openerp_vhr_base_data = function (instance) {
    var _t = instance.web._t;
    
    instance.web.Widget.include({
    	rpc: function(url, data, options) {
	    	return this.alive(openerp.session.rpc(url, data, options)).fail(function (r) {
	    		if (typeof(r) === 'object' && r['code'] !== 200) {
	    			instance.web.redirect('/web')
	    		}
	        });
	    }
    });
    instance.web.Controller.include({
    	rpc: function(url, data, options) {
	    	return this.alive(openerp.session.rpc(url, data, options)).fail(function (r) {
	    		if (typeof(r) === 'object' && r['code'] !== 200) {
	    			instance.web.redirect('/web')
	    		}
	        });
	    }
    });
};