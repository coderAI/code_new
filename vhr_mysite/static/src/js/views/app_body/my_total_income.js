'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyTotalIncomeView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				openerp.qweb.add_template('/vhr_mysite/static/src/xml/base.xml');
			},
			
			el: '.my_total_income',
			
			template: false,
			
			ui: {
				
				select_period: '#select-year',
				
				input_income_search: 'input#input_income_search',
				
				btn_income_search: '#btn_income_search',
			},
			
			events: {
				
				'change @ui.select_period': 'changeSelectPeriod',
				
				'keypress @ui.input_income_search': 'onPressInputSearch',
				
				'click @ui.btn_income_search': 'onClickMySearch',
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
			
			onClickMySearch: function(e) {
				
				this.onSearch();
			},
			
			onSearch: function(e) {

				var text = $(this.ui.input_income_search).val();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					var period = $( this.el ).find(this.ui.select_period + ' > option:selected').html();
					if (period != '') {
						query = query + '&period=' + period;
					}
				
					document.location = '/mysite/search_total_income' + query;
				}
			},
			
		});

		return MyTotalIncomeView;
	}
);
