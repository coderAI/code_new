openerp_vhr_base_dashboard = function (instance) {
    var _t = instance.web._t;
    
    instance.board.AddToDashboard.include({
    	
    	do_notify: function() {
    		this._super.apply(this, arguments);
    		$('div[id^="hdScroll"]').trigger("scroll");
        },
    });
};
