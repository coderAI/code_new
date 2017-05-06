'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyBenefitView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
			
			el: '.my_benefit',
			
			template: false,
			
			ui: {
				
				input_benefit_search: 'input#input_benefit_search',
				btn_benefit_search: 'input#btn_benefit_search',
			},
			
			events: {
				
				'keypress @ui.input_benefit_search': 'onPressInputSearch',
				'click @ui.btn_benefit_search': 'onClickButtonSearch',
			},
			
			
			onPressInputSearch: function(e) {
				
				if(e.keyCode == 13) {
					
					this.onSearch();
				}
			},
			
			onClickButtonSearch: function(e) {
				
				this.onSearch();
			},
			
			onSearch: function(e) {

				var text = $(this.ui.input_benefit_search).val();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					document.location = '/mysite/search_benefit' + query;
				}
			},
			
		});

		return MyBenefitView;
	}
);
