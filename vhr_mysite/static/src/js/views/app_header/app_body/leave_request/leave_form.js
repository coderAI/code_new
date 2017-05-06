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

        var LeaveFormView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.leave_registration').length > 0) {
            LeaveFormView = ItemView.extend({
                initialize: function(options) {
                    _super.initialize.apply(this, arguments);
                    var self = this;
                    this.parent = options.parent;
                    this.leave_id = options.leave_id;
                    this.lines = {};
                    this.status = false;
                    this.remaining = 0;
                    this.date_from = false;
                    this.date_to = false;
                    this.min_date = false;
                    this.max_date = false;
                    this.approve_reject = false;

                    openerp.jsonRpc(
                        '/mysite/get_holiday_status', 'call', {}).then(function (result) {
                        if (result) {
                            self.status = result;
                        }
                    });

                    this.onShow();
                },

                el: '.leave-request',

                template: false,

                ui: {
                    //input
                    leave_id: 'input#leave_id',
                    input_date_from: 'input#date_from',
                    input_date_to: 'input#date_to',
                    input_leave_lines: 'input[name=leave_detail_lines]',
                    input_shift_d: 'input.shift_d',
                    input_shift_n: 'input.shift_n',
                    input_all_day: 'input.all_day',
                    input_to_date_ins: 'input#to_date_insurance',
                    input_number_of_days_temp: 'input#number_of_days_temp',

                    //select
                    sl_type_id: 'select#holiday_status_id',

                    //textarea
                    txt_reason: 'textarea[name=notes]',

                    //div
                    val_leaves_submitted: 'div#leaves_submitted',
                    val_leaves_taken: 'div#leaves_taken',
                    val_total_leaves: 'div#total_leaves',
                    val_max_allow: 'div#max_allow',
                    val_leave_register: 'div#leave_register',
                    val_remaining_leaves: 'div#remaining_leaves',
                    val_description: 'div#description',
                    val_to_date_ins: 'div#to_date_ins',

                    //button
                    btn_confirm: 'button#btn_confirm',
                    btn_approve: 'button#btn_approve',
                    btn_reject: 'button#btn_reject',
                    btn_remove: 'i.fa-trash-o',

                    //tbody
                    leave_container: 'tbody#tb-leave-container',
                    td_index: 'td.line_index',

                    form: 'form#leave'
                },

                events: {

                    'change @ui.input_date_from': 'onChangeDate',

                    'change @ui.input_date_to': 'onChangeDate',

                        'change @ui.sl_type_id': 'onChangeType'

                },

                onShow: function (){
                    var self = this;
                    var max_allow = $(self.ui.val_max_allow).html();
                    max_allow = (max_allow  && max_allow.toString() != '') ? parseFloat(max_allow) : '';
                    var leave_lines = $(self.ui.input_leave_lines).val();
                    self.remaining = parseFloat($(self.ui.val_remaining_leaves).html());

                    if ($(self.ui.input_date_from) && $(self.ui.input_date_to) && !leave_lines && (max_allow.toString() == '' || max_allow > 0)){
                         self.gen_leave_detail_table($(self.ui.input_date_from).val(), $(self.ui.input_date_from).val(), "date_from");
                    }
                    else if (leave_lines){
                        leave_lines = leave_lines.replace(/'/g, '"');
                        var register_qty = self.gen_table_from_leave_lines(leave_lines);
                        if(self.lines && Object.keys(self.lines).length > 0){
                            var total_register = parseFloat($(self.ui.val_leave_register).html() || 0) ;
                            if ($(self.ui.val_leave_register).html() == "" || isNaN(total_register) || (total_register ==0 && register_qty > 0)){
                                $(self.ui.val_leave_register).html(register_qty);
                                total_register = register_qty;
                            }
                            if (!isNaN(self.remaining - total_register) && !$(self.ui.leave_id).val())
                                $(self.ui.val_remaining_leaves).html(self.remaining - total_register);
                        }
                    }

                    $(self.ui.input_date_from).change(function () {
                        if (self.date_from != $(self.ui.input_date_from).val()){
                            self.date_from = $(self.ui.input_date_from).val();
                            var max_allow = $(self.ui.val_max_allow).html();
                            max_allow = (max_allow  && max_allow.toString() != '') ? parseFloat(max_allow) : '';
                            if (max_allow.toString() == '' || max_allow > 0) {
                                self.gen_leave_detail_table($(self.ui.input_date_from).val(), $(self.ui.input_date_to).val(), "date_from");
                            }
                        }

                    });
                    $(self.ui.input_date_to).change(function () {
                        if (self.date_to != $(self.ui.input_date_to).val()) {
                            self.date_to = $(self.ui.input_date_to).val();
                            var max_allow = $(self.ui.val_max_allow).html();
                            max_allow = (max_allow && max_allow.toString() != '') ? parseFloat(max_allow) : '';
                            if (max_allow.toString() == '' || max_allow > 0) {
                                self.gen_leave_detail_table($(self.ui.input_date_from).val(), $(self.ui.input_date_to).val(), "date_to");
                            }
                        }
                    });

                    $(self.ui.sl_type_id).change(function () {
                        self.onChangeType();
                    });

                    $(self.ui.btn_approve).click(function (e){
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("validate");
                        self.approve_reject = true;
                        $('form').append($(input)).submit();
                        $(self.ui.btn_approve).prop('disabled', true);
                        $(self.ui.btn_reject).prop('disabled', true);
                    });

                    $(self.ui.btn_reject).click(function (e){
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("reject");
                        self.approve_reject = true;
                        $('form').append($(input)).submit();
                        $(self.ui.btn_reject).prop('disabled', true);
                        $(self.ui.btn_approve).prop('disabled', true);
                    });

                    $(self.ui.form).submit(function(e) {
                        if (self.approve_reject == false){
                            if(!(self.lines && Object.keys(self.lines).length > 0)){
                                alert("Vui lòng thêm chi tiết phiếu nghỉ!");
                                e.preventDefault(); return;
                            }
                            var remaining = $(self.ui.val_remaining_leaves).html();
                            if(remaining.toString() != "" && parseFloat(remaining) < 0){
                                alert("Số lượng đăng ký vượt quá số phép còn lại!");
                                e.preventDefault(); return;
                            }
                            var register = $(self.ui.val_leave_register).html();
                            if(register.toString() == "" || parseFloat(register) == 0){
                                alert("Số lượng đăng ký phải lớn hơn 0!");
                                e.preventDefault(); return;
                            }
                            var max_allow = $(self.ui.val_max_allow).html();
                            if(register.toString() != "" && parseFloat(max_allow) < parseFloat(register)){
                                alert("Số lượng đăng ký vượt quá số phép tối đa được đăng ký!");
                                e.preventDefault(); return;
                            }
                            $(self.ui.btn_confirm).prop('disabled', true);
                            $(self.ui.btn_reject).prop('disabled', true);
                        }
                        self.approve_reject = false;
                    });

                },

                gen_table_from_leave_lines: function(leave_lines) {
                    var html = "";
                    var self = this;
                    self.min_date = false;
                    self.max_date = false;
                    self.lines = JSON.parse(leave_lines);
                    var total_register = 0;
                    var i = 1;
                    self.check_min_max_date();
                    for (var key in self.lines){
                        var remove = "";
                        if (self.lines[key].remove == 1 && !$(self.ui.input_number_of_days_temp).val()){
                            remove = "<i class='fa fa-trash-o fa-lg text-error' line_id='"+key+"'>";
                        }
                        html += "<tr>" +
                                    "<td class='line_index' line_id='"+key+"'>" + i + "</td>" +
                                    "<td>" + self.lines[key].date + "</td>" +
                                    "<td>" + "<input type='checkbox' class='shift_d' " + (self.lines[key].shift_d ? "checked='checked' ": "") + (self.lines[key].readonly == 1 ? "disabled='disabled' ": "") + "/>" + "</td>" +
                                    "<td>" + "<input type='checkbox' class='shift_n' " + (self.lines[key].shift_n ? "checked='checked' ": "") + (self.lines[key].readonly == 1 ? "disabled='disabled' ": "") + "/>" + "</td>" +
                                    "<td>" + "<input type='checkbox' class='all_day' " + (self.lines[key].all_day ? "checked='checked' ": "") + (self.lines[key].readonly == 1 ? "disabled='disabled' ": "") + "/>" + "</td>" +
                                    "<td>" + remove + "</td>" +
                                "</tr>";
                        if (self.lines[key].all_day){
                            total_register += 1;
                        }else if(self.lines[key].shift_d || self.lines[key].shift_n){
                            total_register += 0.5;
                        }
                        i++;
                    }
                    if (Object.keys(self.lines).length <= 31){
                         $(self.ui.leave_container).html(html);
                    }
//                    var days_temp = $(self.ui.input_number_of_days_temp).val();
                    if (!$(self.ui.input_number_of_days_temp).val() && Object.keys(self.lines).length <= 31 && self.min_date && self.min_date != $(self.ui.input_date_from).val()){
//                        var date_from = $(self.ui.input_date_from).val();
                        self.date_from = self.min_date;
                        $(self.ui.input_date_from).val(self.min_date);
//                        var split = self.min_date.split("/");
//                        $('.input-append.date#from_date').datepicker("update", new Date(split[2], split[1]-1, split[0])).datepicker("fill");
//                        if (days_temp && !isNaN(days_temp) && date_from){
//                            days_temp -= self.calc_date_delta(date_from, self.min_date) - 1;
//                            $(self.ui.input_number_of_days_temp).val(days_temp);
//                            $(self.ui.val_leave_register).html(days_temp);
//                        }
                    }
                    if (!$(self.ui.input_number_of_days_temp).val() && Object.keys(self.lines).length <= 31 && self.max_date && self.max_date != $(self.ui.input_date_to).val()){
//                        var date_to = $(self.ui.input_date_to).val();
                        $(self.ui.input_date_to).val(self.max_date);
                        self.date_to = self.max_date;
//                        var s_max = self.max_date.split("/");
//                        $('.input-append.date#to_date').datepicker("update", new Date(s_max[2], s_max[1]-1, s_max[0])).datepicker("fill");
//                        if (days_temp && !isNaN(days_temp) && date_to){
//                            days_temp -= self.calc_date_delta(self.date_to, date_to) - 1;
//                            $(self.ui.input_number_of_days_temp).val(days_temp);
//                            $(self.ui.val_leave_register).html(days_temp);
//                        }
                    }
                    $(self.ui.btn_remove).click(function () {
                        var change_qty = 0;
                        var key = parseInt($(this).attr('line_id'));
                        if (self.lines[key].all_day){
                            change_qty = 1;
                        }else if(self.lines[key].shift_d || self.lines[key].shift_n){
                            change_qty = 0.5;
                        }
                        delete self.lines[key];
                        self.gen_leave_lines();
                        var total = self.gen_table_from_leave_lines(JSON.stringify(self.lines));
                        if (!isNaN(total)){
                            var days_temp = $(self.ui.input_number_of_days_temp).val();
                            if (days_temp != ""){
                                total = (parseFloat(days_temp) - change_qty).toFixed(1);
                                $(self.ui.input_number_of_days_temp).val(total);
                                $(self.ui.val_leave_register).html(total);
                                if ($(self.ui.val_remaining_leaves).html() != "" &&  $(self.ui.val_max_allow).html() != ""){
                                    $(self.ui.val_remaining_leaves).html(self.remaining - total);
                                }
                            }else{
                                total = (parseFloat(total)).toFixed(1);
                                $(self.ui.val_leave_register).html(total);
                                if ($(self.ui.val_remaining_leaves).html() != "" &&  $(self.ui.val_max_allow).html() != ""){
                                    $(self.ui.val_remaining_leaves).html(self.remaining - total);
                                }
                            }
                        }

                    });
                    self.gen_leave_lines();
                    self.add_event_click();
                    return total_register;
                },

                onChangeDate: function(e) {
                    var self = this;
                    var max_allow = $(self.ui.val_max_allow).html();
                    max_allow = (max_allow  && max_allow.toString() != '') ? parseFloat(max_allow) : '';
                    if (max_allow.toString() == '' || max_allow > 0){
                        self.gen_leave_detail_table($(self.ui.input_date_from).val(), $(self.ui.input_date_to).val(), "date_from");
                    }
                },

                onChangeType: function(e) {
                    var self = this;
                    var type_id = $(self.ui.sl_type_id).val();
                    if (self.status){
                        var values = self.status[type_id];
                        if (values){
                            if ('leave_register' in values)
                            $(self.ui.val_leave_register).html(0);
                            $(self.ui.val_leaves_submitted).html(values['leaves_submitted']);
                            $(self.ui.val_leaves_taken).html(values['leaves_taken']);
                            $(self.ui.val_max_allow).html(values['max_leaves']);
                            $(self.ui.val_remaining_leaves).html(values['remaining_leaves']);
                            $(self.ui.val_total_leaves).html(values['total_leaves']);
                            $(self.ui.val_description).html(values['description']);
                        }else {
                            $(self.ui.val_leave_register).html(0);
                            $(self.ui.val_leaves_submitted).html(0);
                            $(self.ui.val_leaves_taken).html(0);
                            $(self.ui.val_max_allow).html(0);
                            $(self.ui.val_remaining_leaves).html(0);
                            $(self.ui.val_total_leaves).html(0);
                            $(self.ui.val_description).html("");
                        }
                        self.remaining = parseFloat($(self.ui.val_remaining_leaves).html()) || 0;
                        var max_allow = $(self.ui.val_max_allow).html();
                        max_allow = (max_allow  && max_allow.toString() != '') ? parseFloat(max_allow) : '';
                        if (max_allow.toString() == '' || max_allow > 0){
                            self.gen_leave_detail_table($(self.ui.input_date_from).val(), $(self.ui.input_date_to).val(), "date_from");
                        }else {
                            $(self.ui.leave_container).html("");
                            $(self.ui.input_leave_lines).val("");
                            self.lines = {}
                        }
                    }
                },

                gen_leave_detail_table: function(date_from, date_to, type){
                    var self = this;
                    self.lines = {};
                    $(self.ui.leave_container).html("");
                    var max_allow = $(self.ui.val_max_allow).html();
                    max_allow = (max_allow  && max_allow.toString() != '') ? parseFloat(max_allow): '';
                    var type_id = $(self.ui.sl_type_id).val();
                    var diff = 0;
                    if (date_from && date_to){
                        var f_split = date_from.split("/");
                        var t_split = date_to.split("/");
                        var dFrom = new Date(f_split[2], f_split[1]-1, f_split[0]);
                        var dTo = new Date(t_split[2], t_split[1]-1, t_split[0]);
                        diff = (dTo - dFrom)/(24*60*60*1000) + 1;
                        if (diff <= 0){
                            alert('Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu!');
                            $(self.ui.input_date_to).val(null);
                            $('.input-append.date#to_date').datepicker("update", dFrom).datepicker("fill");
                            date_to = null;
                            $(self.ui.val_leave_register).html(0);
                            $(self.ui.val_remaining_leaves).html($(self.ui.val_remaining_leaves).html() != "" && max_allow.toString() != ''? 0 :'');
                            $(self.ui.input_leave_lines).val("");
                            $(self.ui.leave_container).html("");
                        }
                    }
                    openerp.jsonRpc(
                        '/mysite/get_holiday_line', 'call', {
                            'date_from': date_from,
                            'date_to': date_to,
                            'type_id': type_id,
                            'type': type
                        }).then(function (result) {
                        if (result) {
                            if (result.alert){
                                alert(result.alert);
                            }
                            $(self.ui.val_leaves_submitted).html(result['leaves_submitted']);
                            $(self.ui.val_leaves_taken).html(result['leaves_taken']);
                            $(self.ui.val_max_allow).html(result['max_leaves']);
                            if(result['remaining_leaves']){
                                self.remaining = result['remaining_leaves'];
                            }
                            $(self.ui.val_total_leaves).html(result['total_leaves']);

                            if (diff > 0 || result['number_of_days_temp'] > 0) {
                                if (result['check_ins'] != 1) {
                                    $(self.ui.input_number_of_days_temp).val("");
                                    if(($(self.ui.val_remaining_leaves).html() == "")){
                                        $(self.ui.input_number_of_days_temp).val(result['number_of_days_temp']);
                                    }
                                }else{
                                    $(self.ui.input_number_of_days_temp).val(result['number_of_days_temp']);
                                }
                                self.gen_table_from_leave_lines(result.lines);
                                if (result['check_ins'] != 1) {
                                    $(self.ui.input_number_of_days_temp).val("");
                                    $(self.ui.val_leave_register).html(result['number_of_days_temp']);
                                    if (result['remaining_leaves'] && !isNaN(result['remaining_leaves'] - result['number_of_days_temp'])){
                                        var remaining = (self.remaining - (result['number_of_days_temp'] || 0)).toFixed(1);
                                        $(self.ui.val_remaining_leaves).html($(self.ui.val_remaining_leaves).html() != "" && max_allow.toString() != ''? remaining :'');
                                    }else{
                                        remaining = (self.remaining - (result['number_of_days_temp'] || 0)).toFixed(1);
                                        $(self.ui.val_remaining_leaves).html($(self.ui.val_remaining_leaves).html() != "" && max_allow.toString() != ''? remaining :'');
                                    }
                                    if(($(self.ui.val_remaining_leaves).html() == "")){
                                        $(self.ui.input_number_of_days_temp).val(result['number_of_days_temp']);
                                    }
                                } else {
                                    if (date_from && Object.keys(self.lines).length > 0) {
                                        $(self.ui.val_leave_register).html(result['number_of_days_temp']);
                                        $(self.ui.input_number_of_days_temp).val(result['number_of_days_temp']);
                                    }else {
                                        $(self.ui.val_leave_register).html(0);
                                        $(self.ui.input_number_of_days_temp).val("");
                                    }
                                }

                            }

                            var to_date_ins= "";
                            var insurance_date = "";
                            if ('to_date_ins' in result && result["to_date_ins"]){
                                insurance_date = result["to_date_ins"];
                                to_date_ins = 'to_date_ins' in result ? "Ngày nghỉ theo BHXH: " + insurance_date : '';
                                if ('to_date_ins' in result && result["to_date_ins"] && !result.alert){
                                    if((type == 'date_from' && $(self.ui.input_date_to).val() != result["to_date_ins"]) || !$(self.ui.input_date_to).val()){
                                        self.date_to = result['to_date_ins'];
                                        $(self.ui.input_date_to).val(result['to_date_ins']);
                                        var ins_split = result['to_date_ins'].split("/");
                                        $('.input-append.date#to_date').datepicker("update", new Date(ins_split[2], ins_split[1] - 1, ins_split[0])).datepicker("fill");
                                    }
                                    f_split = date_from.split("/");
                                    dFrom = new Date(f_split[2], f_split[1]-1, f_split[0]);
                                    var dateTo = $(self.ui.input_date_to).val();
                                    var r_split = dateTo.split("/");
                                    dTo = new Date(r_split[2], r_split[1]-1, r_split[0]);
                                    diff = (dTo - dFrom)/(24*60*60*1000) + 1;
                                    diff -= (result['number_of_days_duplicate'] || 0);
                                    //$(self.ui.val_leave_register).html(diff);
                                    if ($(self.ui.val_remaining_leaves).html() != ""){
                                        $(self.ui.val_remaining_leaves).html((self.remaining - diff).toFixed(1));
                                    }
                                }
                            }
                            $(self.ui.val_to_date_ins).html(to_date_ins);
                            $(self.ui.input_to_date_ins).html(insurance_date);
                        }
                    });
                },

                gen_leave_lines: function() {
                    $(this.ui.input_leave_lines).val(JSON.stringify(this.lines));
                },

                add_event_click: function(){
                    var self = this;
                    $('.shift_d').click(function () {
                        var leave_register = parseFloat($(self.ui.val_leave_register).html());
                        var i = $(this).parent().parent().find('.line_index').attr("line_id");
                        if(!$(this).prop('checked')) {
                            $(this).parent().parent().find('.all_day').prop('checked', false);
                            self.lines[i]['all_day'] = 0;
                            leave_register -= 0.5;
                        }else{
                            if ($(this).parent().parent().find('.shift_n').prop('checked')){
                                $(this).parent().parent().find('.all_day').prop('checked', true);
                                self.lines[i]['all_day'] = 1;
                            }
                            leave_register += 0.5;
                        }
                        self.lines[i]['shift_d'] = $(this).prop('checked') ? 1:0;
                        self.gen_leave_lines();
                        if ($(self.ui.input_number_of_days_temp).val() > 0){
                            $(self.ui.input_number_of_days_temp).val(leave_register.toFixed(1))
                        }
                        $(self.ui.val_leave_register).html(leave_register);
                        if ($(self.ui.val_remaining_leaves).html()!='' &&!isNaN(self.remaining - leave_register))
                            $(self.ui.val_remaining_leaves).html((self.remaining - leave_register).toFixed(1));
                    });
                    $('.shift_n').click(function () {
                        var leave_register = parseFloat($(self.ui.val_leave_register).html());
                        var i = $(this).parent().parent().find('.line_index').attr("line_id");
                        if(!$(this).prop('checked')) {
                            $(this).parent().parent().find('.all_day').prop('checked', false);
                            self.lines[i]['all_day'] = 0;
                            leave_register -= 0.5;
                        }else{
                            if ($(this).parent().parent().find('.shift_d').prop('checked')){
                                $(this).parent().parent().find('.all_day').prop('checked', true);
                                self.lines[i]['all_day'] = 1;
                            }
                            leave_register += 0.5;
                        }
                        self.lines[i]['shift_n'] = $(this).prop('checked') ? 1:0;
                        self.gen_leave_lines();
                        if ($(self.ui.input_number_of_days_temp).val() > 0){
                            $(self.ui.input_number_of_days_temp).val(leave_register.toFixed(1))
                        }
                        $(self.ui.val_leave_register).html(leave_register);
                        if ($(self.ui.val_remaining_leaves).html()!='' &&!isNaN(self.remaining - leave_register))
                            $(self.ui.val_remaining_leaves).html((self.remaining - leave_register).toFixed(1));
                    });
                    $('.all_day').click(function () {
                        var leave_register = parseFloat($(self.ui.val_leave_register).html());
                        var i = $(this).parent().parent().find('.line_index').attr("line_id");
                        if(!$(this).prop('checked')) {
                            $(this).parent().parent().find('.shift_d').prop('checked', false);
                            $(this).parent().parent().find('.shift_n').prop('checked', false);
                            self.lines[i]['shift_d'] = 0;
                            self.lines[i]['shift_n'] = 0;
                            leave_register -= 1;
                        }else{
                            if (!$(this).parent().parent().find('.shift_d').prop('checked') &&  !$(this).parent().parent().find('.shift_n').prop('checked')){
                                leave_register += 1;
                            }else {
                                leave_register += 0.5;
                            }
                            $(this).parent().parent().find('.shift_d').prop('checked', true);
                            $(this).parent().parent().find('.shift_n').prop('checked', true);
                            self.lines[i]['shift_d'] = 1;
                            self.lines[i]['shift_n'] = 1;
                        }
                        self.lines[i]['all_day'] = $(this).prop('checked') ? 1:0;
                        self.gen_leave_lines();

                        if ($(self.ui.input_number_of_days_temp).val() > 0){
                            $(self.ui.input_number_of_days_temp).val(leave_register.toFixed(1))
                        }
                        $(self.ui.val_leave_register).html(leave_register);
                        if ($(self.ui.val_remaining_leaves).html()!='' && !isNaN(self.remaining - leave_register))
                            $(self.ui.val_remaining_leaves).html((self.remaining - leave_register).toFixed(1));
                    });
                },
                check_min_max_date: function() {
                    var length = Object.keys(this.lines).length;
                    if(this.lines && length > 0){
                        this.min_date = this.lines[Object.keys(this.lines)[0]].date;
                        this.max_date = this.lines[Object.keys(this.lines)[length-1]].date;
                    }
                },

                calc_date_delta: function(date_from, date_to){
                    var f_split = date_from.split("/");
                    var t_split = date_to.split("/");
                    var from = new Date(f_split[2], f_split[1]-1, f_split[0]);
                    var to = new Date(t_split[2], t_split[1]-1, t_split[0]);
                    return (to -from)/(24*60*60*1000);
                }
            });
        }

		return LeaveFormView;
	}
);
