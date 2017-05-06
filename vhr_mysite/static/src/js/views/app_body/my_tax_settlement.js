'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyTaxSettlementView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
			
			el: '.my_tax_settlement',
			
			template: false,
			
			ui: {
				
				select_year: '#select-year',
				
				input_employee_search: 'input#input_employee_search',
				input_tax_settlement_search: 'input#input_tax_settlement_search',
				
				btn_employee_search: '#btn_employee_search',
				btn_tax_settlement_search: '#btn_tax_settlement_search',
			},
			
			events: {
				
				'keypress @ui.input_employee_search': 'onPressInputSearch',
				'keypress @ui.input_tax_settlement_search': 'onPressInputTaxSearch',
				
				'click @ui.btn_employee_search': 'onClickMySearch',
				'click @ui.btn_tax_settlement_search': 'onClickMyTaxSettlementSearch',
				
				'change @ui.select_year': 'changeSelectYear',
			},

			onPressInputSearch: function(e) {
				
				if(e.keyCode == 13) {
					
					this.onSearch();
				}
			},
			
			onClickMySearch: function(e) {
				
				this.onSearch();
			},
			
			onSearch: function(e) {
				
				var text = $(this.ui.input_employee_search).val();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					document.location = '/mysite/tax_settlement_auth' + query;
				}
			},
			
			onPressInputTaxSearch: function(e) {
				if(e.keyCode == 13) {
					
					this.onTaxSearch();
				}
			},
			
			onClickMyTaxSettlementSearch: function(e) {
				
				this.onTaxSearch();
			},
			
			onTaxSearch: function(e) {

				var text = $(this.ui.input_tax_settlement_search).val();
				var year = $(this.ui.select_year + '> option:selected').html();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					if (parseInt(year) > 0) {
						query += '&year=' + year.toString();
					}
				
					document.location = '/mysite/search_tax_settlement' + query;
				}
			},
			
			changeSelectYear: function(e) {
				var class_name = $( e.target ).val();
				
				$("[class^=tax_settlement_]").hide();
				$( '.' + class_name ).show();
			},
		});
		
		return MyTaxSettlementView;
	}
);