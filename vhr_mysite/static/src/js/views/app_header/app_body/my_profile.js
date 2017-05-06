'use strict';

define(
	["marionette", "DocumentAddView"],
	function(Marionette, DocumentAddView) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyProfileView = ItemView.extend({
			
			initialize: function(options) {

				var self = this;
				_super.initialize.apply(this, arguments);
				this.parent = options.parent;
				this.my_employee_id = options.my_employee_id;
				this.my_employee_name = options.my_employee_name;
				
				openerp.jsonRpc(

				    '/mysite/check_editable', 'call', {'employee_id': self.my_employee_id}

				).then(function (result) {
					
					if (result) {
						
						self.startBootrapEdit();
					}
				});		
			},
			
			el: '.my_profile',
			
			template: false,
			
			ui: {
				
				// BUTTON
				btn_send: 'a#btn_profile_send',
				btn_education_add: 'a#btn_education_add',
				btn_document_add: 'a#btn_document_add',
				btn_partner_add: 'a#btn_partner_add',
				btn_bank_add: 'a#btn_bank_add',
				btn_row_remove: 'i.btn_my_remove',
				btn_next_tab: "a.btnNext",
				btn_prev_tab: "a.btnPrevious",
				
				// INPUT
				input_editable: '.my_input_editable',
				input_date_editable: '.my_date_editable',
				input_number_editable: '.my_number_editable',

				input_gender: '#my_gender',
				input_marital: '#my_marital',
				input_nation: '#my_nation',
				input_city: '#my_city',
				input_temp_city: '#my_temp_city',
				input_district: '#my_district',
				input_temp_district: '#my_temp_district',
				input_ethenic: '#my_ethnic',
				input_country: '#my_country',
				input_children: '#my_children',
				input_religion: '#my_religion',
				input_office: '#my_office',
				input_phone: '#my_phone',
				
				input_document_type: 'table#my_document_info .my_document_type',
				input_document_state: 'table#my_document_info .my_document_state',
				input_document_country: 'table#my_document_info .my_document_country',
				input_document_city: 'table#my_document_info .my_document_city',
				input_document_date: 'table#my_document_info .my_date_editable',
				input_document_number: 'table#my_document_info .my_number_editable',
				
				input_education_school: 'table#my_education_table .my_education_school',
				input_education_faculty: 'table#my_education_table .my_education_faculty',
				input_education_speciality: 'table#my_education_table .my_education_speciality',
				input_education_degree: 'table#my_education_table .my_education_degree',
				input_education_issue_date: 'table#my_education_table .my_education_issue_date',
				
				input_partner_text: 'table#my_partner_info .my_input_editable',
				input_partner_numer: 'table#my_partner_info .my_number_editable',
				input_partner_district: 'table#my_partner_info .my_partner_district',
				input_partner_city: 'table#my_partner_info .my_partner_city',
				input_partner_relation: 'table#my_partner_info .my_partner_relationship',
				input_partner_is_emergency: 'table#my_partner_info .my_partner_is_emergency',
				
				input_bank_account_name: 'table#my_bank_info .my_input_editable',
				input_bank_account_number: 'table#my_bank_info .my_number_editable',
				input_bank: 'table#my_bank_info .my_bank',
				input_bank_branch: 'table#my_bank_info .my_bank_branch',
				input_bank_is_main: 'table#my_bank_info .my_bank_is_main',
				
				input_non_edit: '.non_edit_field',
				
				// TABS
				tab_info: 'ul#my_info_tabs',
				tab_element: 'ul#my_info_tabs a',

				// TABLE
				table_personal_info: 'table#my_personal_info',
				table_contact_info: 'table#my_contact_info',
				table_education_info: 'table#my_education_table',
				table_document_info: 'table#my_document_info',
				table_partner_info: 'table#my_partner_info',
				table_bank_info: 'table#my_bank_info',
			},
			
			events: {
				
				'click @ui.btn_send': 'onClickButtonSend',
				
				'click @ui.btn_education_add': 'onClickButtonEducationAdd',
				
				'click @ui.btn_document_add': 'onClickButtonDocumentAdd',
				
				'click @ui.btn_partner_add': 'onClickButtonPartnerAdd',
				
				'click @ui.btn_bank_add': 'onClickButtonBankAdd',
				
				'click @ui.tab_element': 'onClickTabElement',
				
				'click @ui.btn_row_remove': 'onClickRemoveRow',
				
				'click @ui.input_partner_is_emergency': 'onClickCheckBoxRequired',
				
				'click @ui.input_bank_is_main': 'onClickCheckBox',
				
				'click @ui.input_bank_branch': 'onClickBankBranch',
				
				'click @ui.input_district': 'onClickDistrict',
				
				'click @ui.input_temp_district': 'onClickTempDistrict',
				
				'click @ui.input_partner_district': 'onClickPartnerDistrict',
				
				'click @ui.input_non_edit': 'onClickNonEditField',
				
				'click @ui.btn_next_tab': 'onClickButtonNext',
				'click @ui.btn_prev_tab': 'onClickButtonPrev',
			},
			
			_checkNumber: function(n) {
				
				return !isNaN(parseFloat(n)) && isFinite(n);
			},
			
			_checkLength: function(val, length, type) {
				
				if (!length || typeof(length) == 'undefined') {
					return true;
				}
				
				if (type == 'max') {
					
					if (val.toString().length > length) {
						return false;
					}
				}
				
				if (type == 'min') {
					
					if (val.toString().length < length) {
						return false;
					}
				}
				
				return true;
			},
			
			startBootrapEdit: function() {
				
				var self = this;

				$.fn.editable.defaults.mode = 'popup';

				self._textEditable(self.ui.input_editable);
				self._numberEditable(self.ui.input_number_editable);
				self._dateEditable(self.ui.input_date_editable);
				self._dateEditable(self.ui.input_education_issue_date, 'left');

				var gender_type = [{value: 'male', text: 'Nam'},
				                   {value: 'female', text: 'Nữ'}];
				self._selectEditable(self.ui.input_gender, gender_type, true);

				var marital_type = [{value: 'single', text: 'Độc thân'},
				                    {value: 'married', text: 'Đã lập gia đình'},
				                    {value: 'divorced', text: 'Đã ly hôn'},
				                    {value: 'widowed', text: 'Góa Vợ/Chồng'}];
				self._selectEditable(self.ui.input_marital, marital_type, true);
				
				self.global_document_state = [{value: 'new', text: 'Cấp Mới'},
				                      {value: 'update', text: 'Cập Nhật'},
				                      {value: 'move', text: 'Chuyển từ công ty cũ sang'}];
				self._selectEditable(self.ui.input_document_state, self.global_document_state, true);
				
				// Init extra tables
				self._initExtraTable();
				
				openerp.jsonRpc(

				    '/mysite/get_personal_info', 'call', {'employee_id': self.my_employee_id}

				).then(function (result) {

					if (result) {

						var ethnices = result.ethnices,
							religions = result.religions,
							offices = result.offices;
						self.global_relationship = result.relationship,
						self.global_cities = result.cities,
						self.global_districts = result.districts,
						self.global_doc_types = result.doc_types,
						self.global_schools = result.schools,
						self.global_faculties = result.faculties,
						self.global_specialities = result.specialities,
						self.global_degrees = result.degrees,
						self.global_countries = result.countries;
						self.global_banks = result.banks;
						self.global_bank_branchs = result.bank_branchs;

						self._selectEditable(self.ui.input_ethenic, ethnices);
						self._selectEditable(self.ui.input_country, self.global_countries);
						self._selectEditable(self.ui.input_religion, religions);
						self._selectEditable(self.ui.input_office, offices);
						self._selectEditable(self.ui.input_temp_city, self.global_cities);
						self._selectEditable(self.ui.input_city, self.global_cities);
						self._selectEditable(self.ui.input_district, self.global_districts);
						self._selectEditable(self.ui.input_temp_district, self.global_districts);
						
						self._selectEditable(self.ui.input_document_country, self.global_countries);
						self._selectEditable(self.ui.input_document_city, self.global_cities);
						self._selectEditable(self.ui.input_document_type, self.global_doc_types);
						
						self._selectEditable(self.ui.input_education_school, self.global_schools);
						self._selectEditable(self.ui.input_education_faculty, self.global_faculties);
						self._selectEditable(self.ui.input_education_speciality, self.global_specialities);
						self._selectEditable(self.ui.input_education_degree, self.global_degrees);
						
						self._selectEditable(self.ui.input_partner_district, self.global_districts);
						self._selectEditable(self.ui.input_partner_city, self.global_cities);
						self._selectEditable(self.ui.input_partner_relation, self.global_relationship);
						
						self._selectEditable(self.ui.input_bank, self.global_banks);
						self._selectEditable(self.ui.input_bank_branch, self.global_bank_branchs);
					}
					
	            }).fail(function () {

	                // TODO: bootstrap alert with error message
	                alert("Could not load data");
	            });
			},
			
			_requireValidate: function(value) {
				
				if (value.trim() === '') {
					return 'Ô này không được để trống';
				}
				
				return true;
			},
			
			_textEditable: function(selector, required) {

				var self = this;
				$(selector).editable({

					success: function(val, res) {
						
						$(this).data('value', res);
					},
					
					validate: function(value) {
						
						if (required) {
							var check_required = self._requireValidate(value);
							if (check_required !== true) {
								return check_required;
							}
						}
					},
				});
			},

			_dateEditable: function(selector, placement, required) {

				var self = this;
				$(selector).editable({
					placement: placement ? placement : 'top',
					success: function(val, res) {
						
						$(this).data('value', res.format("YYYY-MM-DD"));
					},
					
					validate: function(value) {
						
						if (required) {
							var check_required = self._requireValidate(value);
							if (check_required !== true) {
								return check_required;
							}
						}
					},
					
					combodate: {
						minYear: 1900,
						maxYear: 2070
					}
				});
			},

			_numberEditable: function(selector, required) {

				var self = this;
				$(selector).editable({
					
					success: function(val, res) {
						
						$(this).data('value', res);
					},
					
					validate: function(value) {
						
						// Default check required true
						var check_required = true;

						if (required) { // check required if has a request
							check_required = self._requireValidate(value);
						}
						
						// If required not true, raise error
						if (check_required !== true) {
							return check_required;
						}

						var check = self._checkNumber(value ? value : 0);
						
						if (!check) return 'Vui lòng nhập số, không có khoảng trắng và chữ.';
						
						var maxlength = $(this).data('maxlength');
						check = self._checkLength(value, maxlength, 'max');
						
						if (!check) return 'Độ dài không được vượt quá ' + maxlength.toString() + ' chữ số';
						
						var minlength = $(this).data('minlength');
						check = self._checkLength(value, minlength, 'min');
						
						if (!check) return 'Độ dài không được ít hơn ' + minlength.toString() + ' chữ số';
					}
				});
			},
			
			_selectEditable: function(selector, source_list, not_convert, required) {

				var self = this;
				if (!source_list || source_list.constructor !== Array) {
					var source_list = [];
				}
				
				if (!not_convert || not_convert !== true) {
					
					var source = [];
					_.each(source_list, function(item) {

						source.push({

							value: item.id,

							text: item.name
						})
					});
					
					self._baseSelectEditable(selector, source, required);
				} else {
					
					self._baseSelectEditable(selector, source_list, required);
				}
			},
			
			_baseSelectEditable: function(selector, source, required) {
				$(selector).editable({

					source: source,
					
					success: function(val, res) {
						
						$(this).data('value', res);
						$(this).attr('data-value', res);
					},
					
					validate: function(value) {
						
						if (required) {
							var check_required = self._requireValidate(value);
							if (check_required !== true) {
								return check_required;
							}
						}
					},
				});
			},
			
			_initExtraTable: function() {

				var self = this;
				
				self.my_education_table = self._dataExtraTable(self.ui.table_education_info);
				self.my_document_table = self._dataExtraTable(self.ui.table_document_info);
				self.my_partner_table = self._dataExtraTable(self.ui.table_partner_info);
				self.my_bank_table = self._dataExtraTable(self.ui.table_bank_info);
			},
			
			_dataExtraTable: function(table) {

				return $(table).DataTable({
					'paging': false,
					'info': false,
					'bFilter': false, 
				});
			},
			
			onClickButtonSend: function(e) {
				
				e.preventDefault();
				var self = this;
				
				bootbox.confirm({ 
				    size: 'medium', // small, medium, large
				    message: "Bạn sẽ không được chỉnh sửa thêm bất kỳ thông tin nào cho đến khi yêu cầu của bạn được phê duyệt. <br/>" +
				    "Hãy chắc chắn những thông tin bên dưới là chính xác.", 
				    callback: function(result){
				    	if (result) {
				    		
				    		$('.miss_required').removeClass('miss_required');
							
							var employee_data = self.collectEmployee(),
								contact_data = self.collectContact(),
							    document_data = self.collectPersonalDocument(),
							    partner_data = self.collectPartner(),
							    certificate_data = self.collectCetificate(),
								bank_data = self.collectBank();

							var check_extra = self._validate_extra_info([employee_data,
							                                             contact_data,
							                                             document_data,
							                                             partner_data,
							                                             certificate_data,
							                                             bank_data]);
							var check_partner_emergency = self._check_partner_emergency();
							var check_account_is_main = self._check_account_is_main();
							/*if (partner_data && partner_data[0].length > 0){
								check_partner_emergency = self._check_partner_emergency();
							}*/
							if (check_extra !== true) {
								
								bootbox.alert({ 
								    size: 'small',
								    message: 'Bạn nhập thiếu dữ liệu tại: ' + check_extra,
								});
							}
							else if (!check_partner_emergency) {

								bootbox.alert({ 
								    size: 'small',
								    message: 'Chọn một người liên lạc khẩn cấp!',
								});
							}
							else if (!check_account_is_main) {

								bootbox.alert({ 
								    size: 'small',
								    message: 'Chọn một tài khoản ngân hàng chính',
								});
							}
							else {
								
								openerp.jsonRpc(

								    '/mysite/set_personal_info', 'call', {
								    	'employee_id': self.my_employee_id,
								    	'employee_data': employee_data[1],
								    	'contact_data': contact_data[1],
								    	'document_data': document_data,
								    	'partner_data': partner_data,
								    	'certificate_data': certificate_data,
								    	'bank_data': bank_data,
								    }
								).then(function(result) {
									
									if (result) {
										
										bootbox.dialog({
											message: "Yêu cầu thay đổi thông tin của bạn đã được gửi cho C&B phê duyệt<br/>" +
													"Kiểm tra thông tin thay đổi của bạn trong menu Cá nhân > Thông tin thay đổi <br />" +
													"Vui lòng gửi bản copy/ sao y hồ sơ liên quan cho C&B để xác nhận",
											title: "Thông báo",
											buttons: {
												success: {
													label: "OK",
													className: "btn-primary",
													callback: function() {
														document.location.href = "/";
													}
											    },
											}
										});
									}
									else {
										
										bootbox.alert({ 
										    size: 'small',
										    message: 'Bạn chưa chỉnh sửa thông tin!',
										});
									}
								});
							}
				    	}
				    }
				});
			},

			_validate_extra_info: function(list_data) {
				
				var message = '';
				_.each(list_data, function(_data) {
					
					if (_data[0].length == 0) {
						return;
					}
					
					_.each(_data[0], function(data) {
						
						message += ('<br/> - ' +data);
					});
				});
				
				if (message.trim() != '') {
					return message;
				}
				
				return true;
			},
			
			_check_partner_emergency: function() {
				var checks = $('#my_partner_info .my_partner_is_emergency'),
					res = false;
				_.each(checks, function(item) {
					
					if ($(item).data('value') == 1) {
						res = true;
					}
				});
				
				return res;
			},
			
			_check_account_is_main: function() {
				
				var checks = $('#my_bank_info .my_bank_is_main'),
				count = 0;
				_.each(checks, function(item) {
					
					if ($(item).data('value') == 1) {
						count++;
					}
				});
				
				if (count > 1 || count == 0) {
					return false;
				}
				
				return true;
			},
			
			/*
			 * This function collects the basic info:
			 *  - my_profile_info
			 *  - my_contact_info
			 */
			_collectDataInfo: function(selector) {
				
				var res = {},
					result = [];
				
				/* result containt 2 part
				 * - Part 1 store field required
				 * - Part 2 store value to send to system
				 */
				result.push([]);
				var list_unsave = $(selector).find('.editable-unsaved');
				// Looping on all the fields which were modified
				_.each(list_unsave, function(item) {
					item = $(item);
					res[item.data('field')] = item.data('value');
				});
				
				// Looping on all fields to check required
				var list_field = $(selector).find('.editable');
				_.each(list_field, function(item) {
					item = $(item);
					if (parseInt(item.data('required')) == 1 && (!item.data('value') || parseInt(item.data('value')) == -1)) {
						item.parent().addClass('miss_required');
						result[0].push(item.data('title'));
					}
				});
				result.push(res)
				return result;
			},
			
			/*
			 * This function loops on all the row in the extra table and collect data. List of table:
			 *  - my_document_info
			 *  - my_partner_info
			 *  - my_certificate_info
			 *  - my_bank_info
			 */
			_collectDataExtraInfo: function(table) {
				
				var self = this,
					res = [];
				
				/* res containt 2 part
				 * - Part 1 store field required
				 * - Part 2 store value to send to system
				 */
				res.push([]);
			
				// Loop on all tbody row
				_.each($(table).find('tbody tr'), function(row) {
					
					// But first, checking user modified this row or not
					if ($(row).find('td .editable-unsaved').length == 0) return; // the return in _.each = continue
					
					// Declare the JSON object for each row.
					var object = {};
					object['origin_id'] = $(row).data('id') || false;
					
					// Check line in quick edit mode
					if ($(row).data('update-id')) {
						object['update_id'] = $(row).data('update-id');
					}
					
					// Get the value from each cell
					_.each($(row).find('td > a'), function(cell) {
						object[$(cell).data('field')] = $(cell).data('value') || false;
					});

					_.each($(row).find('td > input'), function(cell) {
						
						object[$(cell).data('field')] = $(cell).data('value') || false;
					});

					res.push(object);
				});
				
				// Loop on all tbody rows for check required fields 
				_.each($(table).find('tbody tr'), function(row) {
					
					// Get the value from each cell
					_.each($(row).find('td > a'), function(cell) {
						if (parseInt($(cell).data('required')) == 1 && (!$(cell).data('value') || parseInt($(cell).data('value')) == -1)) {
							$(cell).parent().addClass('miss_required');
							var message = $(cell).data('error-message') ? $(cell).data('error-message') : $(cell).data('title');
							res[0].push(message);
						}
					});
				});
				return res;
			},
			
			collectEmployee: function() {

				return this._collectDataInfo(this.ui.table_personal_info);
			},
			
			collectContact: function() {

				return this._collectDataInfo(this.ui.table_contact_info);
			},
			
			collectPersonalDocument: function() {
				
				return this._collectDataExtraInfo(this.ui.table_document_info);
			},
			
			collectPartner: function() {

				return this._collectDataExtraInfo(this.ui.table_partner_info);
			},
			
			collectCetificate: function() {
				
				return this._collectDataExtraInfo(this.ui.table_education_info);
			},
			
			collectBank: function() {
				
				return this._collectDataExtraInfo(this.ui.table_bank_info);
			},
			
			_checkListDuplicate: function(res, check) {
				
			},
			
			_addRowEmpty: function() {
				
				return '<span></span>';
			},
			
			_addRowText: function(field, title, required, default_value, err_message) {
				var error_message = err_message;
				if(typeof error_message === 'undefined') {
					error_message = '';
				}
				
				if(typeof default_value === 'undefined') {
					return '<a class="my_input_editable" \
					data-type="text" \
					data-required="'+ required +'" \
					data-title="' + title + '" \
					data-error-message="' + error_message + '" \
					data-field="' + field + '"></a>';
				}
				
				return '<a class="my_input_editable" \
							data-type="text" \
							data-value="' + default_value +'" \
							data-required="'+ required +'" \
							data-title="' + title + '" \
							data-error-message="' + error_message + '" \
							data-field="' + field + '">' + default_value +'</a>';
			},
			
			_addRowNumber: function(field, title, required, err_message, max, min) {

				var error_message = err_message;
				if(typeof error_message === 'undefined') {
					error_message = '';
				}
				
				var html = '<a class="my_number_editable" data-type="text" \
							data-field="' + field + '" \
							data-required="'+ required +'" \
							data-error-message="' + error_message + '" \
							data-title="' + title + '"';
				if (max != undefined) {
					html += ' data-maxlength="'+ max +'"';
				}
				if (min != undefined) {
					html += ' data-minlength="'+ min +'"';
				}
				
				html += '></a>';
				return html;
			},
			
			_addRowSelect: function(class_name, field, title, required, value, err_message) {
				var error_message = err_message;
				if(typeof error_message === 'undefined') {
					error_message = '';
				}
				
				if (value !== undefined) {
					return '<a class="'+ class_name +'" \
							data-field="'+ field +'" \
							data-type="select" \
							data-required="'+ required +'" \
							data-value="'+ value +'" \
							data-error-message="'+ error_message +'" \
							data-title="'+ title +'"></a>';
				} else {
					return '<a class="'+ class_name +'" \
							data-field="'+ field +'" \
							data-type="select" \
							data-required="'+ required +'" \
							data-error-message="'+ error_message +'" \
							data-title="'+ title +'"></a>';
				}
			},
			
			_addRowDate: function(class_name, field, title, required) {
				
				return '<a class="' + class_name + '" \
					data-type="combodate" data-title="' + title + '" \
					data-format="YYYY-MM-DD" data-viewformat="DD/MM/YYYY" \
					data-template="DD / MMM / YYYY" \
					data-required="'+ required +'" \
					data-field="'+ field +'"></a>';
			},
			
			_addRowCheckBox: function(field, class_name , required, fields) {
				
				var data_field = '';
				_.each(fields, function(item) {
					data_field = data_field + '-' + item;
				})
				return '<input type="checkbox" data-value="1" \
								checked="checked" \
								data-field="' + field +'" \
								data-required="'+ required +'" \
								data-fields-required="'+ data_field +'" \
								class="' + class_name +'" />';
			},
			
			_addRowMulti: function(list_class, list_field, list_title, list_type, list_required) {
				
				// I just declare two options, actually
				// If you want to improve, you can insert more options (date, number, ...)
				var self = this,
					length = list_field.length,
					res = '';
				for (var i = 0; i < length; i++) {
					switch(list_type[i]){
						case 'select':
							res += self._addRowSelect(list_class[i], list_field[i], list_title[i], list_required[i]);
							if (length -  i > 1) {
								res += ',&#160;';
							}
							break;
						default: // case 'text':
							res += self._addRowText(list_field[i], list_title[i], list_required[i]);
							if (length -  i > 1) {
								res += ',&#160;';
							}
							break;
					}
				}
				
				return res;
			},
			
			_checkRowEmpty: function(table) {
				var rows = 0;

				if (table == 'table#my_document_info') {

					rows = this.my_document_table.rows()[0].length;

				}else if (table == 'table#my_partner_info') {
					
					rows = this.my_partner_table.rows()[0].length;

				}else if (table == 'table#my_education_table') {

					rows = this.my_education_table.rows()[0].length;

				}else if (table == 'table#my_bank_info') {

					rows = this.my_bank_table.rows()[0].length;
				}
				
				// If table is empty
				if (rows == 0) {
					return true;
				}
				
				var cell_num = [];

				_.each($(table).find('tbody tr'), function(row) {
					
					var sum = $(row).find('td > a').length;
					var count = 0;
					_.each($(row).find('td > a'), function(cell) {
						
						// the _.each does not provide the return inside the loop :(
						// So I have to save the value within a array and check the value after loop :(
						if ($(cell).html() == '.........') {
							count++;
						} 
					});
					
					if (count == sum) {
						cell_num.push(true);
					}
				});
				
				if (cell_num.length) {
					return false;
				}
				
				return true;
			},
			
			onClickButtonEducationAdd: function(e) {
				
				e.preventDefault();
				
				var self = this;
				var check = self._checkRowEmpty(self.ui.table_education_info);
				// If row empty all the fields, preventing user add new row
				if (!check) {
					return;
				}
				self.my_education_table.row.add([
				    self._addRowSelect('new_my_education_shool', 'school_id', 'Chọn trường bạn đã học', 0),
				    self._addRowSelect('new_my_education_degree', 'recruitment_degree_id', 'Chọn loại bằng cấp', 0),
				    self._addRowSelect('new_my_education_speciality', 'speciality_id', 'Chọn Khoa', 0),
				    self._addRowSelect('new_my_education_faculty', 'faculty_id', 'Chọn chuyên ngành', 0),
				    '<i class="fa fa-times-circle fa-lg text-danger btn_my_remove"></i>',
				]).draw();

				$('.new_my_issue_date').editable({
					placement: 'left',
					success: function(val, res) {
						
						$(this).data('value', res._d.toISOString().slice(0,10));
					}
				});
				
				self._selectEditable('.new_my_education_shool', self.global_schools);
				self._selectEditable('.new_my_education_faculty', self.global_faculties);
				self._selectEditable('.new_my_education_speciality', self.global_specialities);
				self._selectEditable('.new_my_education_degree', self.global_degrees);
			},
			
			onClickButtonDocumentAdd: function(e) {
				
				e.preventDefault();
				
				var self = this;
				var check = self._checkRowEmpty(self.ui.table_document_info);
				// If row empty all the fields, preventing user add new row
				if (!check) {
					return;
				}
				
				self.my_document_table.row.add([
 				    self._addRowSelect('new_my_document_type', 'document_type_id', 'Loại giấy tờ', 1, undefined, 'Tab Giấy tờ cá nhân: Loại giấy tờ'),
 				    self._addRowNumber('number', 'Số giấy tờ', 1, 'Tab Giấy tờ cá nhân: Số giấy tờ', 12, 8),
 				    self._addRowDate('my_date_editable', 'issue_date', 'Ngày cấp', 0),
 				    self._addRowDate('my_date_editable', 'expiry_date', 'Ngày hết hạn', 0),
 				    self._addRowSelect('new_my_document_city', 'city_id', 'Tỉnh, thành phố', 0),
 				    self._addRowSelect('new_my_document_country', 'country_id', 'Quốc gia', 0, 243),
 				    self._addRowSelect('new_my_document_state', 'state', 'Trạng thái', 1, undefined, 'Tab Giấy tờ cá nhân: Trạng thái'),
 				    '<i class="fa fa-times-circle fa-lg text-danger btn_my_remove"></i>',
 				]).draw();
				
				self._selectEditable('.new_my_document_type', self.global_doc_types);
				self._selectEditable('.new_my_document_country', self.global_countries);
				self._selectEditable('.new_my_document_city', self.global_cities);
				self._selectEditable('.new_my_document_state', self.global_document_state, true);
				self._dateEditable(self.ui.input_document_date);
				self._numberEditable(self.ui.input_document_number);
			},
			
			onClickButtonPartnerAdd: function(e) {
				
				e.preventDefault();
				
				var self = this;
				var check = self._checkRowEmpty(self.ui.table_partner_info);
				// If row empty all the fields, preventing user add new row
				if (!check) {
					return;
				}
				
				self.my_partner_table.row.add([
 				    self._addRowText('name', 'Họ tên', 1, undefined, 'Tab Người thân: Họ tên người thân'),
 				    self._addRowSelect('new_my_partner_relationship', 'relationship_id', 'Mối quan hệ', 1, undefined, 'Tab Người thân: Mối quan hệ'),
 				    self._addRowNumber('mobile', 'Di động người thân', 1, 'Di động người thân', 11, 9),
 				    self._addRowNumber('phone', 'Điện thoại bàn', 0, 'Điện thoại bàn', 10, 7),
 				    self._addRowMulti(['', 'new_my_partner_district', 'new_my_partner_city'],
 				    				  ['street', 'district_id', 'city_id'],
 				    				  ['Số nhà, tên đường, phường / xã', 'Quận / Huyện', 'Tỉnh / Thành Phố'],
 				    				  ['text', 'select', 'select'],
 				    				  [0, 0, 0]),
 				    self._addRowCheckBox('is_emergency', 'my_partner_is_emergency', 0, ['mobile']),
 				    '<i class="fa fa-times-circle fa-lg text-danger btn_my_remove"></i>',
 				]).draw();
				
				self._selectEditable('.new_my_partner_district', self.global_districts);
				self._selectEditable('.new_my_partner_relationship', self.global_relationship);
				self._selectEditable('.new_my_partner_city', self.global_cities);
				self._numberEditable(self.ui.input_partner_numer, true);
				self._textEditable(self.ui.input_partner_text, true);				
			},
			
			onClickButtonBankAdd: function(e) {
				
				e.preventDefault();
				
				var self = this;
				var check = self._checkRowEmpty(self.ui.table_bank_info);
				// If row empty all the fields, preventing user add new row
				if (!check) {
					return;
				}
				
				self.my_bank_table.row.add([
 				    self._addRowText('owner_name', 'Chủ tài khoản', 1, self.my_employee_name, 'Tab Tài khoản ngân hàng: Chủ tài khoản'),
 				    self._addRowNumber('acc_number', 'Số tài khoản', 1, 'Tab Tài khoản ngân hàng: Số tài khoản'),
 				    self._addRowSelect('my_bank', 'bank', 'Ngân hàng', 1, undefined, 'Tab Tài khoản ngân hàng: Tên ngân hàng'),
 				    self._addRowSelect('my_bank_branch', 'bank_branch', 'Chi nhánh', 1, undefined, 'Tab Tài khoản ngân hàng: Chi nhánh'),
 				    self._addRowCheckBox('is_main', 'my_bank_is_main', 0, []),
 				    self._addRowEmpty(),
 				    '<i class="fa fa-times-circle fa-lg text-danger btn_my_remove"></i>',
 				]).draw();
				
				self._selectEditable('.my_bank', self.global_banks);
				self._selectEditable('.my_bank_branch', self.global_bank_branchs);
				self._numberEditable(self.ui.input_bank_account_number, true);
				self._textEditable(self.ui.input_bank_account_name, true);
			},
			
			onClickTabElement: function(e) {
				
				e.preventDefault();
				$(this).tab('show')
			},
			
			onClickRemoveRow: function(e) {
				
				var self = this;

				var table = $(e.target).parents('table');
				switch (table.attr('id')) {
					case 'my_document_info':
						self.my_document_table.row(
							    $(e.target).parents('tr'))
							.remove()
							.draw();
						break;
					case 'my_partner_info':
						self.my_partner_table.row(
							    $(e.target).parents('tr'))
							.remove()
							.draw();
						break;
					case 'my_bank_info':
						self.my_bank_table.row(
							    $(e.target).parents('tr'))
							.remove()
							.draw();
						break;
					default:
						self.my_education_table.row(
							    $(e.target).parents('tr'))
							.remove()
							.draw();
						break;
				}
			},

			onClickCheckBox: function(e) {
				
				if ($(e.target).prop('checked')) {

					$(e.target).data('value', 1);
				} else {
					
					$(e.target).data('value', 0);
				}
				// Add class unsaved for scan data to send to server
				$(e.target).addClass('editable-unsaved');
			},
			
			onClickCheckBoxRequired: function(e) {
				this.onClickCheckBox(e);
				
				var row = $(e.target).parent().parent(),
				fields = $(e.target).data('fields-required');
				fields = fields.split('-');
				
				if ($(e.target).prop('checked')) {
					_.each(fields, function(field) {
						
						var cell = row.find('a[data-field="'+ field +'"]');
						
						cell.attr('data-required', 1);
						cell.data('required', 1);
					});
					
					
				} else {
					
						_.each(fields, function(field) {
						
						var cell = row.find('a[data-field="'+ field +'"]');
						
						cell.attr('data-required', 0);
						cell.data('required', 0);
					});
				}
			},
			
			_onClickFilter: function(e, domain, pool, input) {
				var self = this;

				openerp.jsonRpc(

				    '/mysite/get_info_frontend', 'call',
				    {
				    	'pool': pool,
				    	'domain': domain
				    }

				).then(function (result) {

					if (result) {
						
						$(input).editable('destroy');
						
						self._selectEditable(e.target, result);
						$(e.target).editable('show');
					}
				});
			},
			
			onClickBankBranch: function(e) {
				
				e.preventDefault();

				var self = this,
					bank_id = $(e.target).parent('td').parent('tr').find('.my_bank').data('value'),
					domain = [['bank_id', '=', parseInt(bank_id)]];
				self._onClickFilter(e, domain, 'res.branch.bank', e.target);
			},
				
			onClickDistrict: function(e) {
				
				e.preventDefault();
				
				var self = this,
					city_id = $('#my_city').data('value'),
					domain = [['city_id', '=', parseInt(city_id)]];
				self._onClickFilter(e, domain, 'res.district', e.target);
			},
			
			onClickPartnerDistrict: function(e) {
				
				e.preventDefault();
				
				var self = this,
					line_city = $(e.target).siblings('.my_partner_city'),
					city_id = line_city.data('value'),
					domain = [['city_id', '=', parseInt(city_id)]];
				self._onClickFilter(e, domain, 'res.district', e.target);
			},
			
			onClickTempDistrict: function(e) {
				
				e.preventDefault();
				
				var self = this,
					city_id = $('#my_temp_city').data('value'),
					domain = [['city_id', '=', parseInt(city_id)]];
				self._onClickFilter(e, domain, 'res.district', self.ui.input_temp_district);
			},
			
			onClickNonEditField: function(e) {
				
				e.preventDefault();
				
				bootbox.alert({ 
				    size: 'normal',
				    message: 'Bạn không được phép sửa thông tin này. <br /> Vui lòng liên hệ baitq hoặc baitq nếu có ý kiến thắc mắc.',
				});
			},
			
			onClickButtonNext: function(e) {
				
				if ($(e.target).hasClass('disable')) {
					e.preventDefault();
				} else {
					$('#my_info_tabs > .active').next('li').find('a').trigger('click');
				}
				
			},
			
			onClickButtonPrev: function(e) {
				
				if ($(e.target).hasClass('disable')) {
					e.preventDefault();
				} else {
					$('#my_info_tabs > .active').prev('li').find('a').trigger('click');
				}
				
			},
					
		});

		return MyProfileView;
	}
);
