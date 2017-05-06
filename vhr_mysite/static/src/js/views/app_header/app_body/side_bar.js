'use strict';

define(
	["marionette", "SearchItemView", "PanelMenuItemView"],
	function(Marionette, SearchItemView, PanelMenuItemView) {
		
		var vhr_mysite = openerp.vhr_mysite,
			LayoutView = Marionette.LayoutView,
			_super = LayoutView.prototype;
		
		var SideBarView = LayoutView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
			
			el: '.side-bar',
			
			views: {
				
				search: new SearchItemView(),
				
				panel_menu: new PanelMenuItemView(),
			},

		});

		return SideBarView;
	}
);
