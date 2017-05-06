'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyYearEndBonusView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
			},
			
			el: '.my_year_end_bonus',
			
			template: false,
			
			ui: {
				
				select_year: '#select-year',
				
				input_bonus_search: 'input#input_bonus_search',
				
				btn_bonus_search: '#btn_bonus_search',
			},
			
			events: {
				
				'change @ui.select_year': 'changeSelectYear',
				
				'keypress @ui.input_bonus_search': 'onPressInputSearch',
				
				'click @ui.btn_bonus_search': 'onClickMySearch',
			},
			
			changeSelectYear: function(e) {
				
				var class_name = $( e.target ).val();
				
				$("[class^=year_end_bonus_]").hide();
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

				var text = $(this.ui.input_bonus_search).val();
				var query = '?q=';
				if (text != '') {
					query += text;
				}
				
				if (query != '?q=') {
					
					var year = $( this.el ).find(this.ui.select_year + ' > option:selected').html();
					if (year != '') {
						query = query + '&year=' + year;
					}
				
					document.location = '/mysite/search_year_end_bonus' + query;
				}
			},
		});
		
		return MyYearEndBonusView;
	}
);