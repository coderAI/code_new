'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyRecruitmentRequestView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				
				$(this.ui.input_date).datepicker({
					format: 'dd/mm/yyyy',
					altFormat : 'yy-mm-dd',
					altField  : '.date input',
					startDate: new Date(),
				});
				
				$(this.ui.input_date).datepicker('setDate', new Date());
				$(this.ui.input_date).datepicker('update');
				$(this.ui.input_date).val('');
				 
				 _.each($(this.ui.summer_note), function(item) {
					 $(item).summernote({
						 height: 180,
						 codemirror: { // codemirror options
						    theme: 'monokai'
						  },
						 toolbar: [
						           // [groupName, [list of button]]
						           ['style', ['bold', 'italic', 'underline', 'clear']],
						           ['fontsize', ['fontsize']],
						           ['para', ['ul', 'ol', 'paragraph']],
						           ['height', ['height']]
						         ],
			        	 callbacks: {
			        		 onChange: function(contents, $editable) {
			        			 console.log($(item).summernote('isEmpty'), contents);
			        			 if (!$(item).summernote('isEmpty')) {
			        				 $(item).val(contents);
			        			 } else {
			        				 $(item).html('');
			        			 }
			        		 }
			        	 }
					 });
					 
					 $(item).summernote('fontSize', 14);
				 })
				 
				 $(this.ui.dropdown).dropdown();
				 
				 $('.main-display').focus();
				 
				 this.request_for_dept = $(this.ui.select_request_for_dept).fastselect(options).data('fastselect');
				 this.request_role = $(this.ui.select_request_role).fastselect(options).data('fastselect');
				 this.report_to = $(this.ui.select_report_to).fastselect(options).data('fastselect');
				 this.education_level = $(this.ui.select_education_level).fastselect(options).data('fastselect');
				 this.request_for_comp = $(this.ui.select_request_for_comp).fastselect(options).data('fastselect');
				 this.working_place = $(this.ui.select_working_place).fastselect(options).data('fastselect');
				 this.requester = $(this.ui.select_requester).fastselect(options).data('fastselect');
				 this.for_employee = $(this.ui.select_for_employee).fastselect(options).data('fastselect');
				 
				 if ($('.my_recruitment_request').length > 0) {
					 $('html, body').animate({
						scrollTop: $('.main-display').offset().top
					 }, 1000);
				 }
			},
			
			el: '.my_recruitment_request',
			
			template: false,
			
			ui: {
				request_form: '#request_form',
				
				input_date: '.form_line .date input',
				summer_note: '.form_line .summer_note',
				summer_note_required: '.form_line .summer_note.required',
				dropdown: '#request_form .dropdown-toggle',
				
				input_reason: '.form-control.reason',
				input_for_employee: '.form-control.for_employee',
				div_for_employee: 'div.for_employee',
				
				// Selection
				select_requester: '#request_form .form_line .form-control.requester',
				select_request_for_dept: '#request_form .form_line .form-control.request_for_dept',
				select_request_role: '#request_form .form_line .form-control.request_role',
				select_report_to: '#request_form .form_line .form-control.report_to',
				select_education_level: '#request_form .form_line .form-control.education_level',
				select_request_for_comp: '#request_form .form_line .form-control.request_for_comp',
				select_working_place: '#request_form .form_line .form-control.working_place',
				select_for_employee: '#request_form .form_line .form-control.for_employee',
			},
			
			events: {
				'submit @ui.request_form': 'onFormSubmit',
				'change @ui.input_reason': 'onChangeReason',
				'keyup @ui.input_date': 'onKeyPress',
				'keydown @ui.input_date': 'onKeyPress',
				'keypress @ui.input_date': 'onKeyPress',
			},
			
			onFormSubmit: function(e) {
				
				// For employee
				var for_emps = [];
				_.each(this.for_employee.optionsCollection.selectedValues, function(val, key) {
					for_emps.push(key);
				})
				
				$('<input />').attr('type', 'hidden')
		          .attr('name', "for_employees")
		          .attr('value', for_emps)
		          .appendTo(this.ui.request_form);
				
//				select_requester
				this.insert_select_data(this.requester, 'requester');
//				select_request_for_dept
				this.insert_select_data(this.request_for_dept, 'request_for_dept');
//				select_request_role
				this.insert_select_data(this.request_role, 'request_role');
//				select_report_to
				this.insert_select_data(this.report_to, 'report_to');
//				select_education_level
				this.insert_select_data(this.education_level, 'education_level');
//				select_request_for_comp
				this.insert_select_data(this.request_for_comp, 'request_for_comp');
//				select_working_place
				this.insert_select_data(this.working_place, 'working_place');
			},
			
			insert_select_data: function(select, name) {
				var value;
				_.each(select.optionsCollection.selectedValues, function(val, key) {
					value = key;
				});
				$('<input />').attr('type', 'hidden')
		          .attr('name', name)
		          .attr('value', value)
		          .appendTo(this.ui.request_form);
			},
			
			onChangeReason: function(e) {
				var reason = $(e.currentTarget).val();
				if (parseInt(reason) != 19) {
					$(this.ui.input_for_employee).prop('required',true);
					$(this.ui.div_for_employee).show();
				} else {
					$(this.ui.input_for_employee).prop('required', false);
					$(this.ui.div_for_employee).hide();
				}
			},
			
			onKeyPress: function(e) {
				e.preventDefault();
			}

		});
		
		return MyRecruitmentRequestView;
	}
);