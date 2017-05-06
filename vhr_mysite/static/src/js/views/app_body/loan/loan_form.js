'use strict';

define(
    ["marionette"],
    function(Marionette){
        var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;

        var LoanFormView = ItemView.extend({

            initialize: function(options) {

				_super.initialize.apply(this, arguments);

                if ($(this.ui.inputMode).val() == 'create'){
                    this.initLoanTime();
                }

                var eleLoanCategWarning = $(this.ui.divLoanCategWarning);
                var eleLoanCategNote = $(this.ui.divLoanCategNote);
                var eleLoanTypeNote = $(this.ui.textareaLoanTypeNote);

                if (eleLoanCategWarning.attr('show') === 'show'){
                    eleLoanCategWarning.show();
                }
                else{
                    eleLoanCategWarning.hide();
                }

                if (eleLoanCategNote.attr('show') === 'show'){
                    eleLoanCategNote.show();
                    eleLoanTypeNote.attr("required", "required");
                    eleLoanCategNote.addClass("has-success");
                }
                else{
                    eleLoanCategNote.hide();
                    eleLoanTypeNote.prop("required", null);
                    eleLoanCategNote.removeClass("has-success");
                }

			},

			el: '.loan_form',

			template: false,

            ui: {
                //INPUT
                inputState: 'input#state',
                inputEmployeeId: 'input#employee_id',
                inputJoinedDate: 'input#joined_date',
                inputLoanId: 'input#loan_id',
                inputCurrentSalary: 'input#current_salary',
                inputLoanAmount: 'input#loan_amount',
                inputInterestRate: 'input#interest_rate',
                inputSupportRate: 'input#support_rate',
                inputAmount: 'input#amount',
                inputCurrentContractType: 'input#current_contract_type',
                inputCurrentContractTypeName: 'input#current_contract_type_name',
                inputCheckBoxIsPayPayroll: 'input#checkbox_is_pay_payroll',
                inputIsPayPayroll: 'input#is_pay_payroll',
                inputCheckBoxIsDocumentSubmitted: 'input#checkbox_is_document_submitted',
                inputIsDocumentSubmitted: 'input#is_document_submitted',
                inputYearLoan: 'input#year_loan',
                inputMonthPaid: 'input#month_paid',
                inputYearPaid: 'input#year_paid',
                inputMode: 'input#mode',
                inputActionCall: 'input#action_call',
                inputIsVisibleWarning: 'input#is_visible_warning',
                inputIsVisibleNote: 'input#is_visible_note',
                //SELECT
                selectLoanCateId: 'select#loan_cate_id',
                selectCompanyId: 'select#company_id',
                selectMonthLoan: 'select#month_loan',
                //TEXTAREA
                textareaRequiredDocument: 'textarea#required_document',
                textareaLoanTypeWarning: 'textarea#loan_type_warning',
                textareaLoanTypeNote: 'textarea#loan_type_note',
                //BUTTON
                buttonConfirm: 'button#btn_confirm',
                buttonSubmit: 'button#btn_submit',
                buttonApprove: 'button#btn_approve',
                buttonCancel: 'button#btn_cancel',
                //DIV
                divLoanCategWarning: 'div#loan_categ_warning',
                divLoanCategNote: 'div#loan_categ_note',
            },

            events: {
                //CHANGE
                'change @ui.selectLoanCateId': 'onchangeLoanCateg',
                'change @ui.selectCompanyId': 'onchangeCompany',
                'change @ui.inputCheckBoxIsPayPayroll': 'onchangeIsPayPayroll',
                'change @ui.inputCheckBoxIsDocumentSubmitted': 'onchangeIsDocumentSubmitted',
                'change @ui.inputLoanAmount': 'onchangeAmountRate',
                'change @ui.inputInterestRate': 'onchangeAmountRate',
                'change @ui.inputSupportRate': 'onchangeAmountRate',
                'change @ui.selectMonthLoan': 'onchangeLoanTime',
                'change @ui.inputYearLoan': 'onchangeLoanTime',
                //CLICK
                'click @ui.buttonConfirm': 'validateBeforeSubmit',
                'click @ui.buttonSubmit': 'clickSubmit',
                'click @ui.buttonApprove': 'clickApprove',
                'click @ui.buttonCancel': 'clickCancel',
            },

            validateBeforeSubmit: function(event){
                var self = this;
                if ($(self.ui.selectLoanCateId).val() === 'none'){
                    alert("Vui lòng lựa chọn Mục Đích !!!");
                    event.preventDefault();
                }
            },

            onchangeCompany: function(event){
                var self = this;
                var eleCompanyID = $(self.ui.selectCompanyId);
                var eleEmployeeId = $(self.ui.inputEmployeeId);
                var companyId = (eleCompanyID.val() && !isNaN(eleCompanyID.val())) ? parseInt(eleCompanyID.val()) : false;
                var employeeId = (eleEmployeeId.val() && !isNaN(eleEmployeeId.val())) ? parseInt(eleEmployeeId.val()) : false;
                if (companyId && employeeId){
                    // Get current contract and current salary
                    // set value of Số Tiền Tạm Ứng, Lãi Suất, Công Ty Hỗ Trợ, Tổng Tiền Phải Trả to null
                    openerp.jsonRpc('/loan/form/contracts', 'call',
                    {employee_id: employeeId, company_id: companyId}
                    ).then(function(result_data){
                        var contractTypeData = result_data['contract_type_data'];
                        $(self.ui.inputCurrentContractType).val(contractTypeData['id']);
                        $(self.ui.inputCurrentContractTypeName).val(contractTypeData['name']);
                        $(self.ui.inputLoanAmount).val(null);
                        $(self.ui.inputInterestRate).val(null);
                        $(self.ui.inputSupportRate).val(null);
                        $(self.ui.inputAmount).val(null);
                    });
                }
            },

            onchangeIsPayPayroll: function(event){
                var self = this;
                $(self.ui.inputIsPayPayroll).val($(self.ui.inputCheckBoxIsPayPayroll).prop("checked"));
            },

            onchangeIsDocumentSubmitted: function(event){
                var self = this;
                $(self.ui.inputIsDocumentSubmitted).val($(self.ui.inputCheckBoxIsDocumentSubmitted).prop("checked"));
            },

            _getDayBetweenDates: function(dateFrom, dateTo){
                if (!dateFrom || !dateTo){
                    return 0;
                }
                var milisecondOneDay = 24 * 60 * 60 * 1000;
                var milisecondDateFrom = dateFrom.getTime();
                var milisecondDateTo = dateTo.getTime();
                var diff = Math.abs(milisecondDateTo - milisecondDateFrom);
                return Math.round(diff/milisecondOneDay);
            },

            _getYearBetweenDates: function(dateFrom, dateTo){
                var self = this;
                if (!dateFrom || !dateTo){
                    return 0.0;
                }
                var daysOneYear = 365.0;
                var days = parseFloat(self._getDayBetweenDates(dateFrom, dateTo));
                return days / daysOneYear;
            },

            _get_seniority: function(joinedDate){
                var self = this;
                if (!joinedDate){
                    return 0.0;
                }
                var today = new Date();
                return self._getYearBetweenDates(joinedDate, today);
            },

            initLoanTime: function(){
                var self = this;
                var currentDate = new Date();
                $(self.ui.selectMonthLoan).val(currentDate.getMonth() + 1);
                $(self.ui.inputYearLoan).val(currentDate.getFullYear());
                var datePaid = new Date(new Date(currentDate).setMonth(currentDate.getMonth() + 2));
                $(self.ui.inputMonthPaid).val((datePaid.getMonth() == 0) ? 12 : datePaid.getMonth());
                $(self.ui.inputYearPaid).val(datePaid.getFullYear());
            },

            clickSubmit: function(event){
                var self = this;
                $(self.ui.inputActionCall).val('submit');
                return confirm("Bạn chắc chắn muốn nộp đăng ký vay nợ này ?");
            },

            clickApprove: function(event){
                var self = this;
                $(self.ui.inputActionCall).val('approve');
                return confirm("Bạn có chắc chắn duyệt đăng ký vay nợ này ?");
            },

            clickCancel: function(event){
                var self = this;
                $(self.ui.inputActionCall).val('cancel');
                return confirm("Bạn có chắc chắn hủy đăng ký vay nợ này ?");
            },

            onchangeLoanTime: function(event){
                var self = this;
                var monthLoan = $(self.ui.selectMonthLoan).val();
                var yearLoan = $(self.ui.inputYearLoan).val();
                var dateLoan = new Date(yearLoan, monthLoan - 1);
                // get first day of current month
                var currentDate = new Date(new Date().getFullYear(), new Date().getMonth());
                if (dateLoan < currentDate){
                    alert("Thời điểm vay phải lớn hơn hoặc bằng thời điểm hiện tại");
                    self.initLoanTime();
                }
                else{
                    var datePaid = new Date(new Date(dateLoan).setMonth(dateLoan.getMonth() + 2));
                    $(self.ui.inputMonthPaid).val((datePaid.getMonth() == 0) ? 12 : datePaid.getMonth());
                    $(self.ui.inputYearPaid).val(datePaid.getFullYear());
                }
            },

            onchangeAmountRate: function(event){
                var self = this;
                var joinedDate = $(self.ui.inputJoinedDate).val();
                var eleCurrentSalary = $(self.ui.inputCurrentSalary);
                var currentSalary = (eleCurrentSalary.val()) ? parseFloat(eleCurrentSalary.val()) : 0.0;
                var eleLoanAmount = $(self.ui.inputLoanAmount);
                var loanAmount = (eleLoanAmount.val()) ? parseFloat(eleLoanAmount.val()) : 0.0;
                var eleInterestRate = $(self.ui.inputInterestRate);
                var interestRate = (eleInterestRate.val()) ? parseFloat(eleInterestRate.val()) : 0.0;
                var eleSupportRate = $(self.ui.inputSupportRate);
                var SupportRate = (eleSupportRate.val()) ? parseFloat(eleSupportRate.val()) : 0.0;
                var eleAmount = $(self.ui.inputAmount);
                if (joinedDate && currentSalary){
                    // convert joinedDate to Date with format dd/mm/YYYY
                    var joinedDateItems = joinedDate.split("/");
                    joinedDate = new Date(joinedDateItems[2], joinedDateItems[1] - 1, joinedDateItems[0]);
                    // get seniority
                    var seniority = self._get_seniority(joinedDate);
                    if (seniority >= 1.0){
                        if ((loanAmount / currentSalary) > 3.0){
                            alert("Bạn chỉ được vay tối đa 3 tháng lương !!!");
                            loanAmount = currentSalary * 3.0;
                        }
                    }
                    else {
                        if (loanAmount > currentSalary){
                            alert("Bạn chỉ được vay tối đa 1 tháng lương !!!");
                            loanAmount = currentSalary;
                        }
                    }
                }
                var amount = loanAmount + loanAmount * (interestRate - SupportRate) / 100.0;
                eleAmount.val(amount);
                eleLoanAmount.val(loanAmount);
            },

            onchangeLoanCateg: function(){
                var self = this;
                var eleLoanCateID = $(self.ui.selectLoanCateId);
                var eleRequiredDocument = $(self.ui.textareaRequiredDocument);
                var eleEmployeeId = $(self.ui.inputEmployeeId);
                var eleLoanId = $(self.ui.inputLoanId);
                var eleLoanCategWarning = $(self.ui.divLoanCategWarning);
                var eleLoanCategNote = $(self.ui.divLoanCategNote);
                var eleLoanTypeWarning = $(self.ui.textareaLoanTypeWarning);
                var eleLoanTypeNote = $(self.ui.textareaLoanTypeNote);
                var eleIsVisibleWarning = $(self.ui.inputIsVisibleWarning);
                var eleIsVisibleNote = $(self.ui.inputIsVisibleNote);
                var categId = (eleLoanCateID.val() && !isNaN(eleLoanCateID.val())) ? parseInt(eleLoanCateID.val()) : false;
                var empId = (eleEmployeeId.val() && !isNaN(eleEmployeeId.val())) ? parseInt(eleEmployeeId.val()) : false;
                var loanId = (eleLoanId.val() && !isNaN(eleLoanId.val())) ? parseInt(eleLoanId.val()) : false;
                var joinedDate = $(self.ui.inputJoinedDate).val();
                eleLoanCategWarning.hide();
                eleLoanCategNote.hide();
                eleLoanTypeWarning.val('');
                eleLoanTypeNote.val('');
                eleIsVisibleWarning.val('false');
                eleIsVisibleNote.val('false');
                eleLoanTypeNote.attr("readonly", "readonly");
                eleLoanTypeNote.prop("required", null);
                eleLoanCategNote.removeClass("has-success");
                if (categId && empId && joinedDate){
                    //Get required document
                    openerp.jsonRpc('/loan/form/required_document', 'call',
                    {loan_cate_id: categId, employee_id: empId, joined_date: joinedDate, loan_id: loanId}
                    ).then(function(result_data){
                            var required_document = (result_data['required_document']) ? result_data['required_document'] : "";
                            var error = result_data['error'];
                            var loan_type_warning = result_data['loan_type_warning'];
                            var is_visible_note = result_data['is_visible_note'];
                            if (error){
                                alert(error);
                                eleRequiredDocument.val("");
                                eleLoanCateID.val("none");
                            }
                            else{
                                if (loan_type_warning){
                                    eleLoanCategWarning.show();
                                    eleLoanTypeWarning.val(loan_type_warning);
                                    eleIsVisibleWarning.val('true');
                                }
                                if (is_visible_note){
                                    eleLoanCategNote.show();
                                    eleIsVisibleNote.val('true');
                                    eleLoanTypeNote.prop("readonly", null);
                                    eleLoanTypeNote.attr("required", "required");
                                    eleLoanCategNote.addClass("has-success");
                                }
                                eleRequiredDocument.val(required_document);
                                if (required_document){
                                    eleRequiredDocument.attr("readonly", "readonly");
                                }
                                else if (!required_document && $(self.ui.inputState).val() === 'clicker_request'){
                                    eleRequiredDocument.prop("readonly", null);
                                }
                            }
                        });
                }
            },

        });

        return LoanFormView;
    }
);
