'use strict';

define(["backbone", "marionette", "HeaderLayout", "BodyLayout", "FooterLayout"],
		function(Backbone, Marionette, HeaderLayout, BodyLayout, FooterLayout) {
	
	var session = openerp.vhr_mysite.session;
	
	var application
		= openerp.vhr_mysite.application
		= new Marionette.Application({
			
			app_layouts: {
				header: new HeaderLayout({
					el: '.app-header'
				}),
				
				body: new BodyLayout({
					el: '.app-main'
				}),
				
				footer: new FooterLayout({
					el: '.app-footer'
				}),
			}
		});
	
	application.addInitializer(function(options) {
		
		Backbone.history.start();
	});
	
	application.start({});
	
	return application;
});
