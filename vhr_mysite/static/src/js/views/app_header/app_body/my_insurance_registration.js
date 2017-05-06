'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MyInsuranceRegistrationView = ItemView.extend({
			
			initialize: function(options) {

				var self = this;
				_super.initialize.apply(this, arguments);
				
				openerp.jsonRpc(

				    '/mysite/check_insurance_edit', 'call', {}

				).then(function (result) {
					
					if (result) {
						
						self.startBootrapEdit();
					}
				});
			},
			
			el: '.my_insurance_registration',
			
			template: false,
			
			ui: {
				
				// INPUT
				radio_registration: 'input.radio_registration',
				input_editable: '.my_input_editable',
				input_date_editable: '.my_date_editable',
				input_number_editable: '.my_number_editable',
				
				// BUTTON
				btn_insurance_add: 'a#btn_insurance_add',
				btn_row_remove: 'i.btn_my_remove',
				btn_send: 'a#btn_profile_send',
				
				// TABLE
				table_ins_reg: 'table#my_insurance_registration_detail',
			},
			
			events: {
				
				'change @ui.radio_registration': 'onChangeRadioRegistration',
				
				'click @ui.btn_insurance_add': 'onClickButtonInsuranceAdd',
				
				'click @ui.btn_send': 'onClickButtonSend',
				
				'click @ui.btn_row_remove': 'onClickRemoveRow',
			},
			
			_checkNumber: function(n) {
				
				return !isNaN(parseFloat(n)) && isFinite(n);
			},
			
			_checkLetterNumber: function(n) {
				
				if (!n) {
					return false;
				}
				
				var letterNumber = /^[0-9a-zA-Z-/]+$/;
				if (n.match(letterNumber)) {
					return true;
				}
				
				return false;
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
				self._numberLetterEditable(self.ui.input_number_editable);
				self._dateEditable(self.ui.input_date_editable);
				
				// Init extra tables
				self._initExtraTable();
				
				openerp.jsonRpc(

				    '/mysite/get_info_frontend', 'call',
				    {
				    	'pool': 'vhr.insurance.package'
				    }

				).then(function (result) {
					self._global_package = result;

					if (result) {
						
						$('.my_package_id').editable('destroy');
						self._selectEditable('.my_package_id', result);
					}
				}).fail(function () {

	                // TODO: bootstrap alert with error message
	                alert("Could not load data");
	            });
				
				openerp.jsonRpc(

				    '/mysite/get_info_frontend', 'call',
				    {
				    	'pool': 'vhr.relationship.type',
				    	'domain': [['code', 'not in', ['GF', 'OST', 'AT', 'ET', 'GM', 'YST', 'CH', 'AU', 'BAC', 'SP']]]
				    }

				).then(function (result) {
					self._global_relation = result;

					if (result) {
						
						$('.my_relation_id').editable('destroy');
						self._selectEditable('.my_relation_id', result);
					}
				}).fail(function () {

	                // TODO: bootstrap alert with error message
	                alert("Could not load data");
	            });
				
				openerp.jsonRpc(

				    '/mysite/_check_contract', 'call', {}

				).then(function (result) {
					
					self._is_regis = result;
				}).fail(function () {

	                // TODO: bootstrap alert with error message
	                alert("Could not load data");
	            });
			},
			
			_requireValidate: function(value) {
				
				if(typeof(value) == 'object') {
					return true;
				}
				else if (value.trim() === '') {
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
						minYear: 1951,
						maxYear: new Date().getFullYear()
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

						var check = self._checkNumber(value ? value : false);
						
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
			
			_numberLetterEditable: function(selector, required) {

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

						var check = self._checkLetterNumber(value ? value : false);
						
						if (!check) return 'Vui lòng nhập số, chữ hoặc các ký tự "-", "/". Không khoảng trắng hoặc các kí tự đặc biệt khác';
						
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
							
							var family_data = self.collectInsuranceFamily();

							var check_extra = self._validate_extra_info([family_data]);
							if (check_extra !== true) {
								
								bootbox.alert({ 
								    size: 'medium',
								    message: 'Vui lòng nhập thông tin tại các ô có tô màu vàng bên dưới.',
								});
							}
							else {
								
								openerp.jsonRpc(

								    '/mysite/set_insurance_registration_info', 'call', {
								    	'registration': self._is_regis,
								    	'family_data': family_data,
								    }
								).then(function(result) {
									
									if (result) {
										
										bootbox.dialog({
											message: "Thông tin đăng ký của bạn đã được gửi đến phòng Nhân sự<br/>",
											title: "Thông báo",
											buttons: {
												success: {
													label: "OK",
													className: "btn-primary",
													callback: function() {
														document.location.href = "/mysite/insurance_registration";
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
			 *  - table_ins_reg
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
			
			collectInsuranceFamily: function() {
				
				return this._collectDataExtraInfo(this.ui.table_ins_reg);
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
				if (max) {
					html += ' data-maxlength="'+ max +'"';
				}
				if (min) {
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
			
			_addRowDate: function(class_name, field, title, required, err_message) {
				var error_message = err_message || '';
				
				return '<a class="' + class_name + '" \
					data-type="combodate" data-title="' + title + '" \
					data-format="YYYY-MM-DD" data-viewformat="DD/MM/YYYY" \
					data-template="DD / MMM / YYYY" \
					data-required="'+ required +'" \
					data-error-message="'+ error_message +'" \
					data-field="'+ field +'"></a>';
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
			
			onClickNonEditField: function(e) {
				
				e.preventDefault();
				
				bootbox.alert({ 
				    size: 'normal',
				    message: 'Bạn không được phép sửa thông tin này. <br /> Vui lòng liên hệ baitq hoặc baitq nếu có ý kiến thắc mắc.',
				});
			},
			
			
			
			
			
			_initExtraTable: function() {

				var self = this;
				
				self.my_ins_reg_table = self._dataExtraTable(self.ui.table_ins_reg);
			},
			
			_dataExtraTable: function(table) {

				return $(table).DataTable({
					'paging': false,
					'info': false,
					'bFilter': false, 
				});
			},
			
			onChangeRadioRegistration: function(e) {
				var self = this;
				var $el = $(e.currentTarget);
				if ($el.val() == '1') {
					$('div.family_registration').removeClass('hidden');
					self._is_regis = true;
				} else {
					$('div.family_registration').addClass('hidden');
					self._is_regis = false;
				}
			},
			
			onClickButtonInsuranceAdd: function(e) {
				
				e.preventDefault();
				
				var self = this;
				var check = self._checkRowEmpty(self.ui.table_ins_reg);
				// If row empty all the fields, preventing user add new row
				if (!check) {
					return;
				}
				self.my_ins_reg_table.row.add([
				    self._addRowText('name', 'Họ và tên', 1, undefined, 'Họ tên người thân'),
				    self._addRowNumber('id_number', 'CMND / Passport / Số giấy Khai sinh', 1, 'CMND / Passport / Số giấy Khai sinh', 12, 6),
				    self._addRowDate('my_date_editable', 'birth_date', 'Ngày sinh', 1, 'Ngày sinh'),
				    self._addRowSelect('new_my_relation_id', 'relation_id', 'Mối quan hệ', 1, undefined, 'Mối quan hệ'),
				    self._addRowSelect('new_my_package_id', 'package_id', 'Gói bảo hiểm', 1, undefined, 'Gói bảo hiểm'),
				    '<i class="fa fa-times-circle fa-lg text-danger btn_my_remove"></i>',
				]).draw();
				
				self._dateEditable(self.ui.input_date_editable, undefined, true);
				self._numberLetterEditable(self.ui.input_number_editable, true);
				self._textEditable(self.ui.input_editable, true);
				self._selectEditable('.new_my_relation_id', self._global_relation, undefined, undefined, true);
				self._selectEditable('.new_my_package_id', self._global_package, undefined, undefined, true);
			},
			
			_checkRowEmpty: function(table) {
				var rows = 0;

				if (table == 'table#my_insurance_registration_detail') {

					rows = this.my_ins_reg_table.rows()[0].length;

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
			
			onClickRemoveRow: function(e) {
				
				var self = this;

				var table = $(e.target).parents('table');
				switch (table.attr('id')) {
					case 'my_insurance_registration_detail':
						self.my_ins_reg_table.row(
							    $(e.target).parents('tr'))
							.remove()
							.draw();
						break;
//					default:
//						self.my_education_table.row(
//							    $(e.target).parents('tr'))
//							.remove()
//							.draw();
//						break;
				}
			},
			
			
			
					
		});

		return MyInsuranceRegistrationView;
	}
);
