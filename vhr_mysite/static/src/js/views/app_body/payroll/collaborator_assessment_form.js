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

        var CollaboratorAssessmentFormView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.collaborator_assessment').length > 0) {
            CollaboratorAssessmentFormView = ItemView.extend({
                initialize: function(options) {
                    _super.initialize.apply(this, arguments);
                    var self = this;
                    this.ca_id = options.ca_id;
                    this.ca_product_lines = {};
                    this.ca_month_lines = {};
                    this.approve_reject = false;
                    this.approve_reject = false;
                    this.departments = false;
                    var states = new Bloodhound({
                        datumTokenizer: function(d) {return Bloodhound.tokenizers.whitespace(d.word);
                        },
                        queryTokenizer: Bloodhound.tokenizers.whitespace,
                        remote: {
                            url: '/mysite/get_all_departments?code=%QUERY',
                            filter: function (data) {
                                var maps = {};
                                $.each(data, function(i, item){
                                   maps[item.complete_code] = item.id;
                                });
                                self.departments = maps;
                                return $.map(data, function (item) {
                                    return {
                                        word: item.complete_code
                                    };
                                });
                            }
                        }
                    });
                    states.initialize();
                    $(self.ui.input_dept_name).typeahead(null, {
                      displayKey: 'word',
                      source: states.ttAdapter()
                    });

                    $(self.ui.modal_dept_th).typeahead(null, {
                      displayKey: 'word',
                      source: states.ttAdapter()
                    });

                    this.onShow();
                },

                el: '.collaborator_assessment',

                template: false,

                ui: {
                    //input
                    ca_id: 'input#ca_id',
                    input_dept_name: 'input#department_name',
                    input_dept_id: 'input#department_id',


                    //select
                    sl_month: 'select#month',
                    sl_year: 'select#year',
                    sl_ca_type_id: 'select#collaborator_assessment_type_id',
                    sl_comp_id: 'select#company_id',

                    //div

                    //button
                    btn_confirm: 'button#btn_confirm',
                    btn_approve: 'button#btn_approve',
                    btn_reject: 'button#btn_reject',
                    btn_remove: 'i.fa-trash-o',
                    btn_add: 'a#btn_add',

                    //modal
                    modal_product: '#add_product_line',
                    modal_month: '#add_month_line',
                    modal_dept_th: '.modal input[name="department_name"]',
                    modal_emp_th: '.modal input[name="employee_th"]',

                    //tbody
                    ca_products_container: 'tbody#tb_ca_products_container',
                    ca_months_container: 'tbody#tb_ca_months_container',

                    //table
                    tb_ca_products: 'table#tb_ca_products',
                    tb_ca_months: 'table#tb_ca_months',

                    form: 'form#collaborator_assessment'
                },

                events: {

                    'change @ui.sl_ca_type_id': 'onChangeCaType',

                    'change @ui.input_date_to': 'onChangeDate',

                    'change @ui.input_ca_type_id': 'onChangeType',

                    'click @ui.btn_add': 'add_line',

                    'blur @ui.input_dept_name': 'onChangeDept',

                    'blur @ui.modal_dept_th': 'onChangeDeptCharge'

                },

                onShow: function (){
                    var self = this;
                },

                onChangeDept: function(e) {
                    var self = this;
                    if(!self.departments || !($(self.ui.input_dept_name).val() in self.departments)){
                        $(self.ui.input_dept_name).val("");
                        $(self.ui.input_dept_id).val("");
                    }else{
                        $(self.ui.input_dept_id).val(self.departments[$(self.ui.input_dept_name).val()]);
                    }

                },

                onChangeDeptCharge: function(e) {
                    var self = this;
                    if(!self.departments || !($(e.currentTarget).val() in self.departments)){
                        $(e.currentTarget).val("");
                        $(e.currentTarget).parents("div.controls").find('input[name="charged_dept_id"]').val("");
                    }else{
                       $(e.currentTarget).parents("div.controls").find('input[name="charged_dept_id"]').val(self.departments[$(e.currentTarget).val()]);
                    }

                },

                onChangeCaType: function(e) {
                    var self = this;
                    var type_code = $(self.ui.sl_ca_type_id).find(":selected").attr('code');
                    if (type_code == 'PR_COLLA_1'){
                        $(self.ui.tb_ca_products).show();
                        $(self.ui.tb_ca_months).hide();
                    }else{
                        $(self.ui.tb_ca_products).hide();
                        $(self.ui.tb_ca_months).show();
                    }
                },

                add_line: function () {
                    var self = this;
                    var type_code = $(self.ui.sl_ca_type_id).find(":selected").attr('code');
                    if (type_code == 'PR_COLLA_1'){
                        self.add_line_product();
                    }else{
                        self.add_line_month();
                    }
                },

                add_line_product: function () {
                    var self = this;
//                    var index = 1;
//                    for (var key in self.ca_product_lines) {
//                        key = parseInt(key);
//                        if (key >= index) {
//                            index = key + 1;
//                        }
//                    }
                    $(self.ui.modal_product).modal("show");
//                    self.ca_product_lines[index] = {
//                        charged_dept_id: '',
//                        employee_id: '',
//                        product: '',
//                        number: '',
//                        price: '',
//                        amount: '',
//                        amount_manager: '',
//                        other_addition: '',
//                        description: ''
//                    }
                },

                add_line_month: function () {
                    var self = this;
//                    var index = 1;
//                    for (var key in self.ca_month_lines) {
//                        key = parseInt(key);
//                        if (key >= index) {
//                            index = key + 1;
//                        }
//                    }
                    $(self.ui.modal_month).modal("show");
//                    self.ca_month_lines[index] = {
//                        charged_dept_id: '',
//                        employee_id: '',
//                        from_date: '',
//                        to_date: '',
//                        total_date: '',
//                        total_ot_normal_days_day: '',
//                        total_ot_normal_days_night: '',
//                        total_ot_days_off_day: '',
//                        total_ot_days_off_night: '',
//                        total_ot_holidays_day: '',
//                        total_ot_holidays_night: '',
//                        total_ot_task: '',
//                        amount: '',
//                        other_addition: '',
//                        description: ''
//                    }
                }
            });
        }

		return CollaboratorAssessmentFormView;
	}
);
