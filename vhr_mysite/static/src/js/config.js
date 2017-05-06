'use strict';

requirejs.config({

	baseUrl: '../../../vhr_mysite/static',

	paths: {

		// CORE JS LIB
		require: 	'lib/requirejs/require',
		jquery: 	'lib/noConflict/jquery',
		underscore: 'lib/noConflict/underscore',
		backbone: 	'lib/noConflict/backbone',
		marionette: 'lib/noConflict/marionette',
		'backbone.babysitter': 	'lib/marionettejs/backbone.babysitter.min',
		'backbone.wreqr': 		'lib/marionettejs/backbone.wreqr.min',

		// External plugin
		bootstrap_editable: 'lib/bootstrap_editable/js/bootstrap-editable.min',

		// Template
		TemplateLoader: 'src/js/core/template_loader',

		// Application
		Application: 'src/js/app',

		// Layouts
		HeaderLayout: 	'src/js/views/app_header',

		BodyLayout: 	'src/js/views/app_body',
			BasicInfoView:		'src/js/views/app_body/my_basic_info',
			SideBarView: 		'src/js/views/app_body/side_bar',
				SearchItemView:		'src/js/views/app_body/side_bar/search',
				PanelMenuItemView:	'src/js/views/app_body/side_bar/panel_menu',
			MyProfileView: 		'src/js/views/app_body/my_profile',
			MyProfileTempView: 	'src/js/views/app_body/my_profile_temp',
				DocumentAddView: 	'src/js/views/app_body/my_profile/document_add',
			MySearchResultView: 'src/js/views/app_body/my_search_result',
			MyTotalIncomeView: 'src/js/views/app_body/my_total_income',
			LeaveFormView: 'src/js/views/app_body/leave_request/leave_form',
			OvertimeFormView: 'src/js/views/app_body/ot_request/overtime_form',
			MyPayslipView: 'src/js/views/app_body/my_payslip',
			MyYearEndBonusView: 'src/js/views/app_body/my_year_end_bonus',
			MyTaxSettlementView: 'src/js/views/app_body/my_tax_settlement',
			TerminationFormView: 'src/js/views/app_body/hr/termination_form',
			MyRecruitmentRequestView: 'src/js/views/app_body/my_recruitment_request',
			MyInsuranceRegistrationView: 'src/js/views/app_body/my_insurance_registration',
			MyCoordinateView:  'src/js/views/app_body/my_employee_coordinate',
			CoordinateSumView: 'src/js/views/app_body/employee_coordinate_summary',
			LoanFormView: 'src/js/views/app_body/loan/loan_form',
			LiabilityListView: 'src/js/views/app_body/account/liability_list_view',
			
			MyBenefitView: 'src/js/views/app_body/my_benefit',
			CollaboratorAssessmentFormView: 'src/js/views/app_body/payroll/collaborator_assessment_form',

		FooterLayout: 	'src/js/views/app_footer',
	},

	shim: {

		jquery: {
			exports: '$'
		},

		underscore: {
			exports: '_'
		},

		backbone: {
			exports: 'Backbone',
			deps: ['jquery', 'underscore']
		},

		marionette: {
			exports: 'Backbone.Marionette',
			deps: ['backbone']
		}
	}

});
/*
$(document).ready(function() {

	openerp.vhr_mysite = {
			session: new openerp.Session()
	}

	openerp.vhr_mysite.session.session_reload().then(

		function() {

			requirejs(['TemplateLoader'], function() {

				// Start the application
				requirejs(['Application'], function() {

					console.log('DOM Ready');
				});

				return $.when();
			})
		}
	);
});*/

openerp.vhr_mysite = {
		session: new openerp.Session()
}

openerp.vhr_mysite.session.session_reload().then(

	function() {

		// Start the application
		requirejs(['Application'], function() {

			console.log('DOM Ready');
		});

		return $.when();
	}
);
