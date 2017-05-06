'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
		ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var SearchItemView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				
				this.hide_tooltip();
			},
			
			el: '#my_search',
			
			ui: {
				
				input_search: 'input#my_input_search',
				
				btn_my_search: 'i#btn_my_search',
			},
			
			events: {
				
				'keypress @ui.input_search': 'onPressInputSearch',
				
				'click @ui.btn_my_search': 'onClickMySearch',
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

				var text = $(this.ui.input_search).val();
				if (text != '') {
					document.location = '/mysite/search/?q=' + text;
				}
			},
			
			hide_tooltip: function() {

				$('[data-toggle="tooltip"]').tooltip('hide');
			}
		});

		return SearchItemView;
	}
);
