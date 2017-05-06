'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			LayoutView = Marionette.LayoutView,
			_super = LayoutView.prototype;
		
		var HeaderLayout = LayoutView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
		});

		return HeaderLayout;
	}
);
