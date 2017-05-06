'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var my_template = '<a class="document_row" data-type="text" data-title="Enter your phone"></a>';
		
		var DocumentAddView = ItemView.extend({
			
			initialize: function(options) {
				console.log(this);
			},

			el: '.document_row',

	        template: my_template,
		});
		
		return DocumentAddView;
		
	}
);
