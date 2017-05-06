'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;


        var CoordinateSumView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.coordinate_summary').length > 0) {
        	CoordinateSumView = ItemView.extend({
                initialize: function(options) {
                    _super.initialize.apply(this, arguments);
                    var self = this;
                    this.lat_value = options.lat_value;
                    this.long_value = options.long_value;
                    this.coor_data = [];

                    this.onShow();
                },

                el: '.coordinate_sum',

                template: false,

                ui: {
                },

                onShow: function (){
                	var self = this;
                	
                	openerp.jsonRpc(

        				    '/map/details', 'call', {}

    				).then(function (result) {
    					
    					this.result = result;
    					this.coor_data = this.result['coor_data'];
    					var campus_lng = this.result['campus'];
    					campus_lng = {lat: campus_lng['lat_value'], lng: campus_lng['long_value']};
    					var cp_circle = new google.maps.Circle({
							strokeColor: '#000066',
					        strokeOpacity: 0.8,
					        strokeWeight: 2,
					        fillColor: '#000066',
					        fillOpacity: 0.35,
					        center: campus_lng,
	            		    map: window.map,
	            		    radius: 200,
		            		});
    					
    					for (var index in this.coor_data){
    						var latlng = {lat: this.coor_data[index]['lat_value'], lng: this.coor_data[index]['long_value']};
    						
    						
//    						var marker = new google.maps.Marker({
//    		            		  position: latlng,
//    		            		  map: window.map,
//    		            		  title: 'Click to zoom'
//    		            		});
    						var circle = new google.maps.Circle({
    							strokeColor: '#FF0000',
						        strokeOpacity: 0.8,
						        strokeWeight: 2,
						        fillColor: '#FF0000',
						        fillOpacity: 0.35,
						        center: latlng,
  		            		    map: window.map,
  		            		    radius: 80,
  		            		});
    					}
    					
    				}).fail(function () {

    	                // TODO: bootstrap alert with error message
    	                alert("Could not load data");
    	            });

                },

                });

            };
        

		return CoordinateSumView;
	}
	
	
);


