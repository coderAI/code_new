'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;


		$('.input-append.date').datepicker({
            startDate: new Date(), autoclose: true, todayHighlight: true
        });
        var TerminationFormView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.termination_request').length > 0) {
            TerminationFormView = ItemView.extend({
                initialize: function(options) {
                    _super.initialize.apply(this, arguments);
                    this.onShow();
                },

                el: '.termination',

                template: false,

                ui: {
                    //input
                    input_ter_id: 'input#ter_id',
                    input_expect_date: 'input#date_end_working_expect',
                    input_approve_date: 'input#date_end_working_approve',

                    //textarea
                    txt_reason: 'textarea[name=employee_reason]',

                    //button
                    btn_confirm: 'button#btn_confirm',
                    btn_approve: 'button#btn_approve',
                    btn_reject: 'button#btn_reject',

                    //tbody
                    form: 'form#termination'
                },

                events: {

                    'change @ui.input_expect_date': 'onChangeExpectDate'

                },

                onShow: function (){
                    var self = this;
                    $(self.ui.input_expect_date).change(function (e){
                         self.onChangeExpectDate(e);
                    });
                    $(self.ui.btn_approve).click(function (e){
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("approve");
                        $('form').append($(input)).submit();
                        $(self.ui.btn_approve).prop('disabled', true);

                    });

                    $(self.ui.btn_reject).click(function (e){
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("reject");
                        $('form').append($(input)).submit();
                        $(self.ui.btn_reject).prop('disabled', true);
                        $(self.ui.btn_approve).prop('disabled', true);
                    });

                    $(self.ui.form).submit(function(e) {
                        $(self.ui.btn_confirm).prop('disabled', true);
                        $(self.ui.btn_reject).prop('disabled', true);
                    });

                },

                onChangeExpectDate: function(e) {
                    var self = this;
                    $(self.ui.input_approve_date).val($(self.ui.input_expect_date).val());
                }

            });
        }

		return TerminationFormView;
	}
);
