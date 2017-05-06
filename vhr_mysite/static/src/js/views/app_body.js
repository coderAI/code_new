'use strict';

define(
	["marionette", "BasicInfoView", "SideBarView", "MyProfileView",
	 "MySearchResultView", "MyProfileTempView", "MyTotalIncomeView",
	 "LeaveFormView", "OvertimeFormView", "MyPayslipView",
	 "MyYearEndBonusView", "MyTaxSettlementView", "TerminationFormView",
	 "MyRecruitmentRequestView", "MyInsuranceRegistrationView", "MyCoordinateView","CoordinateSumView",
	 "LoanFormView","LiabilityListView","MyBenefitView", "CollaboratorAssessmentFormView"],

	function(Marionette, BasicInfoView, SideBarView, MyProfileView,
             MySearchResultView, MyProfileTempView, MyTotalIncomeView,
             LeaveFormView, OvertimeFormView, MyPayslipView,
             MyYearEndBonusView, MyTaxSettlementView, TerminationFormView,
             MyRecruitmentRequestView, MyInsuranceRegistrationView,MyCoordinateView,CoordinateSumView,
		 	 LoanFormView, LiabilityListView,MyBenefitView, CollaboratorAssessmentFormView) {

		var vhr_mysite = openerp.vhr_mysite,
			LayoutView = Marionette.LayoutView,
			_super = LayoutView.prototype;

		var BodyLayout = LayoutView.extend({

			initialize: function(options) {

				var self = this;

				_super.initialize.apply(this, arguments);
				this.views();
				this.global_data_decode64 = '';

				$(window).on('scroll', function(e) {

					if ($(this).scrollTop() > 150) {

						$(self.ui.scroll_top).stop(true, true).fadeIn('slow');
				    } else {

				    	$(self.ui.scroll_top).stop(true, true).fadeOut();
				    }
				})
			},

			views: function(e) {

				basic_info: new BasicInfoView({

					parent: this,
					my_employee_id: parseInt($(this.ui.employee_id).html() || false)
				});

				side_bar: new SideBarView({

					parent: this
				});

				if ($('.my_profile').length > 0) {
					my_profile: new MyProfileView({

						parent: this,

						my_employee_id: parseInt($(this.ui.employee_id).html() || false),

						my_employee_name: $(this.ui.employee_name).html() || ''

					});
				}
				if ($('.my_profile_temp').length > 0) {
					my_profile_temp: new MyProfileTempView({

						parent: this,
						my_employee_id: parseInt($(this.ui.employee_id).html() || false)
					});
				}
				if ($('.my_search_result').length > 0) {
					my_search_result: new MySearchResultView({

						parent: this
					});
				}
				if ($('.my_total_income').length > 0) {
					my_total_income: new MyTotalIncomeView({

						parent: this
					});
				}
				if ($('.my_payslip').length > 0) {
					my_payslip: new MyPayslipView({
						parent: this
					});
				}
				if ($('.my_benefit').length > 0) {
					my_benefit: new MyBenefitView({
						parent: this
					});
				}
				if ($('.my_year_end_bonus').length > 0) {
					my_year_end_bonus: new MyYearEndBonusView({
						parent: this
					});
				}
				if ($('.my_tax_settlement').length > 0) {
					my_tax_settlement: new MyTaxSettlementView({
						parent: this
					});
				}
				if ($('.my_recruitment_request').length > 0) {
					my_recruitment_request: new MyRecruitmentRequestView({
						parent: this
					});
				}
				if ($('.my_insurance_registration').length > 0) {
					my_insurance_registration: new MyInsuranceRegistrationView({
						parent: this
					});
				}

                if ($('.leave_registration').length > 0) {
                    leave_request: new LeaveFormView({
                        parent: this,
                        leave_id: parseInt($(this.ui.leave_id).html() || false)
                    });
                }
                if ($('.overtime_registration').length > 0) {
                    ot_request: new OvertimeFormView({
                        parent: this,
                        ot_id: parseInt($(this.ui.ot_id).html() || false)
                    });
                }
                 if ($('.termination_request').length > 0) {
                     termination_request: new TerminationFormView({
                        parent: this,
                        ter_id: parseInt($(this.ui.ter_id).html() || false)
                    });
                 }

                 if ($('.employee_coordinate').length > 0) {
                	 employee_coordinate: new MyCoordinateView({
                        parent: this
                    });
                 }
                 if ($('.coordinate_summary').length > 0) {
                	 coordinate_summary: new CoordinateSumView({
                        parent: this
                    });
                 }
				if ($('.loan_form').length > 0) {
                    loan_form: new LoanFormView({
                        parent: this,
                    });
                }
				if ($('.liability_list_view').length > 0) {
                    liability_list_view: new LiabilityListView({
                        parent: this,
                    });
                }
                if ($('.collaborator_assessment').length > 0) {
                    ca_form_view: new CollaboratorAssessmentFormView({
                        parent: this
                    });
                }
			},

			ui: {

				employee_id: 'div#my_employee_id',

				employee_name: 'div#my_employee_name',

				scroll_top: 'div#my_scroll_top',

				btn_toggle_sidebar: 'div#button-toggle-sidebar',
			},

			events: {

				'click @ui.scroll_top': 'onClickScrollTop',

				'click @ui.btn_toggle_sidebar': 'onClickToggleSidebar',
			},

			onClickScrollTop: function(e) {

				$('html, body').animate({

					scrollTop: $('body').offset().top
				}, 1000);
			},

			onClickToggleSidebar: function(e) {

				this.$el.find('.side-bar').toggleClass('hidden');
				this.$el.find('.main-content').toggleClass('full_width');
				this.$el.find('#button-toggle-sidebar .fa-minus-square-o').toggleClass('hidden');
				this.$el.find('#button-toggle-sidebar .fa-plus-square-o').toggleClass('hidden');
				this.$el.find('#button-toggle-sidebar .oe_breathing').toggleClass('hidden');
			},
		});

		return BodyLayout;
	}
);
