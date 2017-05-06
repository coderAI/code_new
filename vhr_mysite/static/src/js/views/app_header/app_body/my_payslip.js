'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyPayslipView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
			
			el: '.my_payslip',
			
			template: false,
			
			ui: {
				
				select_year: '#select-year',
				select_month: '#select-month',
				
				input_payslip_search: 'input#input_payslip_search',
				btn_payslip_search: 'input#btn_payslip_search',
			},
			
			events: {
				
				'change @ui.select_year': 'changeSelectYear',
				'change @ui.select_month': 'changeSelectMonth',
				
				'keypress @ui.input_payslip_search': 'onPressInputSearch',
				'click @ui.btn_payslip_search': 'onClickButtonSearch',
			},
			
			changeSelectYear: function(e) {
				this.showPayslip();
			},
			
			changeSelectMonth: function(e) {
				this.showPayslip();
			},
			
			showPayslip: function() {
				var year = $( this.el ).find(this.ui.select_year).val();
				var month = $( this.el ).find(this.ui.select_month).val();
				
				$("[class^=vhr_payslip_]").hide();
				$( '.vhr_payslip_' + year + month ).css({'display': 'inline-block'});
			},
			
			changeSelectPeriod: function(e) {
				
				var class_name = $( e.target ).val();
				
				$("[class^=total_income_]").hide();
				$( '.' + class_name ).show();
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

				var text = $(this.ui.input_payslip_search).val();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					var year = $( this.el ).find(this.ui.select_year).val();
					if (year != '') {
						query = query + '&year=' + year;
					}
					
					var month = $( this.el ).find(this.ui.select_month).val();
					if (month != '') {
						query = query + '&month=' + month;
					}
					
					document.location = '/mysite/search_payslip' + query;
				}
			},
			
		});

		return MyPayslipView;
	}
);
