'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var PanelMenuItemView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				
				var wave_config = {
						
					// How long Waves effect duration 
				    // when it's clicked (in milliseconds)
				    duration: 1200,
				    
				    // Delay showing Waves effect on touch
				    // and hide the effect if user scrolls
				    // (0 to disable delay) (in milliseconds)
				    delay: 200
				}
				
				Waves.init(wave_config);
				Waves.attach('.list-group-item', ['waves-light']);
				Waves.attach('.panel-heading', ['waves-light']);
			},
			
			el: '.panel-group',
			
			ui: {
				
				menu_tab: 'li.list-group-item',
			},
			
			events: {
				
				'click @ui.menu_tab': 'onClickMenuTab',
			},
			
			onClickMenuTab: function(e) {
				
				e.stopPropagation();
				
				var link_menu = $(e.target).find('a').last();
				
				link_menu[0].click();
			}

		});

		return PanelMenuItemView;
	}
);
