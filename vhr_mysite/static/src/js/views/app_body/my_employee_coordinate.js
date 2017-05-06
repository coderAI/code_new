'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;



        var MyCoordinateView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.employee_coordinate').length > 0) {
        	MyCoordinateView = ItemView.extend({
                initialize: function(options) {
                    _super.initialize.apply(this, arguments);
                    var self = this;
                    this.lat_value = options.lat_value;
                    this.long_value = options.long_value;


//                    this.onShow();
                },

                el: '.employee_coordinate',

                template: false,

                ui: {
                    //input
                    input_long_value: 'input#long_value',
                    input_lat_value: 'input#lat_value',

                    //button
                    btn_confirm: 'button#btn_confirm',

                    form: 'form#emp_coor'
                },
                events: {
                	'click @ui.btn_confirm': 'onClickButtonConfirm',
                },

                onShow: function (){
                	var self = this;
                	$(self.ui.form).submit(function(e) {
                		 self.lat_value = $(self.ui.input_lat_value).html();
                         try{
                        	 lat_value = parseFloat(lat_value);
                         }
                         catch(err){
                         	alert("Latitude phải ở dạng số!");
                             e.preventDefault(); return;
                         };
                         self.long_value = $(self.ui.input_long_value).html();
                         try{
                        	 long_value = parseFloat(long_value);
                         }
                         catch(err){
                         	alert("Longtitude phải ở dạng số!");
                             e.preventDefault(); return;
                         };
//                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("validate");
//                        self.approve_reject = true;
                        $(self.ui.btn_confirm).prop('disabled', true);
                    });

                },
                
                onClickButtonConfirm: function(){
                	var self = this;
                	var input = $("<input>").attr({type: "hidden", name: "action"}).val("approve");
                	$('form').append($(input)).submit();
                }

                });

            };
        

		return MyCoordinateView;
	}
);
