'use strict';

define(
    ["marionette"],
    function(Marionette){

        var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;

        var LoanFormView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if($(".loan_form").length > 0)  {
            LoanFormView = ItemView.extend({
                initialize: function(option){
                    _super.initialize.apply(this, arguments);

                    this.parent = option.parent;
                    this.loan_id = option.loan_id;

                    this.onShow();
                },

                el: '.loan-form',

                template: false,

                ui: {
                    //INPUT
                    input_current_contract_type: 'input#current_contract_type',
                    input_current_contract_type_name: 'input#current_contract_type_name',
                    input_current_salary: 'input#current_salary',
                    input_loan_amount: 'input#loan_amount',
                    input_interest_rate: 'input#interest_rate',
                    input_support_rate: 'input#support_rate',
                    input_amount: 'input#amount',
                    input_employee_id: 'input#employee_id',
                    //SELECT
                    select_company_id: 'select#company_id',
                    select_loan_cate_id: 'select#loan_cate_id',
                    //TEXTAREA
                    textarea_required_document: 'textarea#required_document',
                },

                events: {
                    'change @ui.select_company_id': 'onchangeCompany',
                    'change @ui.select_loan_cate_id': 'onchangeLoanCategory',
                    'hover @ui.select_loan_cate_id': 'test',
                },

                onShow: function(){
                    alert("aasfadfa");
                },

                test: function(){
                    alert("abc");
                },

                onchangeCompany: function(){
                    var self = this;
                    var com_id = parseInt($(self.ui.select_company_id).val());
                    alert(emp_id);
                    var emp_id = parseInt($(self.ui.select_company_id).val());
                    //Get the new contract of employee and the salary
                    $.post('/loan/form/contracts', {employee_id: emp_id, company_id: com_id}, function(result_data){
                        $(self.ui.input_current_contract_type).val(result_data.contract_type_data.id);
                        $(self.ui.input_current_contract_type_name).val(result_data.contract_type_data.name);
                        $(self.ui.input_current_salary).val(result_data.current_salary);
                    }, 'json');
                    //Set 0.0 for interest_rate, support_rate, loan_amount, amount
                    $(self.ui.input_loan_amount).val("0.0");
                    $(self.ui.input_interest_rate).val("0.0");
                    $(self.ui.input_support_rate).val("0.0");
                    $(self.ui.input_amount).val("0.0");
                },

                onchangeLoanCategory: function(){
                    var self = this;
                    var categ_id = parseInt($(self.ui.select_loan_cate_id).val());
                    alert(categ_id);
                    $.ajax({
                        url: "/loan/form/required_document",
                        type: "post",
                        dataType: "json",
                        data: {
                            loan_cate_id: categ_id
                        },
                        success: function(result_data){
                            $(self.ui.textarea_required_document).val(result_data.required_document);
                            if(result_data.required_document){
                                $(self.ui.textarea_required_document).attr("readonly", "readonly");
                            }
                            else{
                                $(self.ui.textarea_required_document).attr("readonly", "''");
                            }
                        }
                    });
                },
            });
        }

        return LoanFormView;
    }
);
