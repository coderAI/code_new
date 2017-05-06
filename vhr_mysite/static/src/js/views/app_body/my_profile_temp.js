'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyProfileTempView = ItemView.extend({
			
			initialize: function(options) {

				var self = this;
				_super.initialize.apply(this, arguments);	
			},
			
			el: '.my_profile_temp',
			
			template: false,
			
			ui: {
				// TABS
				tab_info: 'ul#my_info_tabs_temp',
				tab_element: 'ul#my_info_tabs a',

				// TABLE
				table_education_info_temp: 'table#my_education_table',
				table_document_info: 'table#my_document_info',
				table_partner_info: 'table#my_partner_info',
			},
			
			events: {
			},
		});

		return MyProfileTempView;
	}
);
