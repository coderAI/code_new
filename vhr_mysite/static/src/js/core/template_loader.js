define(['jquery'], function($) {
	
	var website = openerp.website;
	
	return $.when.apply($, [
	
        website.add_template_file('vhr_mysite/static/src/xml/base.xml'),
	]);
});
