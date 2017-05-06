'use strict';

Number.prototype.two_digit = function () {
  return isNaN(this) ? this : this > 9 ? "" + this : "0" + this;
};

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;

		$('.input-append.date').datepicker({autoclose: true, todayHighlight: true});
        var OvertimeFormView = ItemView.extend({initialize: function (options) {_super.initialize.apply(this, arguments)}});
        if ($('.overtime_registration').length > 0) {
            OvertimeFormView = ItemView.extend({

                initialize: function (options) {
                    _super.initialize.apply(this, arguments);
                    this.parent = options.parent;
                    this.ot_id = options.ot_id;
                    this.lines = {};
                    this.status = false;
                    this.remaining = 0;
                    this.onShow();
                },

                el: '.overtime-request',

                template: false,

                ui: {
                    //input
                    ot_id: 'input#ot_id',
                    input_ot_lines: 'input[name=overtime_detail_lines]',
                    input_start: 'input[name=start_time]',
                    input_end: 'input[name=end_time]',
                    input_break: 'input[name=break_time]',
                    input_note: 'input[name=notes]',

                    //select
                    sl_date: 'select[name=date_off]',

                    //checkbox
                    cb_is_compensation_leave: '.compensation_leave',

                    //button
                    btn_save: 'button#btn_save',
                    btn_confirm: 'a#btn_confirm',
                    btn_approve_ot: 'button#btn_approve_ot',
                    btn_reject_ot: 'button#btn_reject_ot',
                    btn_add: 'a#btn_add',
                    btn_remove: 'i.fa-trash-o',

                    //tbody
                    ot_container: 'tbody#tb-overtime-container',
                    td_index: 'td.line_index',

                    times: '.times',

                    form: 'form#overtime'
                },

                events: {
                    'click @ui.btn_confirm': 'submitRequest',
                    'click @ui.btn_add': 'add_line'
                },

                onShow: function () {
                    var self = this;
                    var ot_lines = $(self.ui.input_ot_lines).val();
                    if (!ot_lines) {
                        self.add_line();
                    } else {
                        ot_lines = ot_lines.replace(/'/g, '"');
                        self.gen_table_from_ot_lines(ot_lines);
                    }
                    $(self.ui.btn_confirm).click(function () {
                        self.submitRequest();
                    });
                    $(self.ui.times).change(function () {
                        self.calc_total_hours($(this));
                    });
                    $(self.ui.btn_add).click(function () {
                        self.add_line();
                    });

                    $(self.ui.sl_date).change(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.input_note).blur(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.cb_is_compensation_leave).click(function () {
                        self.update_lines($(this));
                    });

                    $(self.ui.btn_approve_ot).click(function (e) {
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("submit");
                        $('form').append($(input)).submit();
                        $(self.ui.btn_approve_ot).prop('disabled', true);
                        $(self.ui.btn_reject_ot).prop('disabled', true);
                    });

                    $(self.ui.btn_reject_ot).click(function (e) {
                        var input = $("<input>").attr({type: "hidden", name: "action"}).val("reject");
                        $('form').append($(input)).submit();
                        $(self.ui.btn_approve_ot).prop('disabled', true);
                        $(self.ui.btn_reject_ot).prop('disabled', true);
                    });

                    $(self.ui.form).submit(function (e) {
                        if (!(self.lines && Object.keys(self.lines).length > 0)) {
                            alert("Vui lòng thêm chi tiết phiếu đăng ký!");
                            e.preventDefault();
                        }
                        $(self.ui.btn_approve_ot).prop('disabled', true);
                        $(self.ui.btn_reject_ot).prop('disabled', true);
                    });
                },

                gen_table_from_ot_lines: function (ot_lines) {
                    var html = "";
                    var self = this;
                    self.lines = JSON.parse(ot_lines);
                    var i = 1;
                    for (var key in self.lines) {
                        var split_date = self.lines[key].date_off.split("-");
                        if (!self.lines[key].readonly) {
                            var date_option = self.gen_schedule(parseInt(split_date[2]), parseInt(split_date[1]));
                        } else {
                            date_option = "<option>" + self.lines[key].date_off + "</option>";
                        }
                        var split_start = self.lines[key].start_time.split(":");
                        var start_option = self.gen_timelines(parseInt(split_start[0]), split_start[1]);
                        var split_end = self.lines[key].end_time.split(":");
                        var end_option = self.gen_timelines(parseInt(split_end[0]), split_end[1]);
                        var disabled = self.lines[key].readonly ? " disabled='disabled' " : "";
                        var lm_edit = !self.lines[key].lm_edit ? " disabled='disabled' " : "";
                        html += "<tr>" +
                            "<input class='line_index' type='hidden' value='" + key + "'/>" +
                            "<td class='hidden-xs'>" + i + "</td>" +
                            "<td><select name='date_off' class='date_off' " + disabled + ">" + date_option + "</select></td>" +
                            "<td><input type='text' required='required' class='notes' onblur='this.setCustomValidity(\"\");' oninvalid=\"if(!this.value) this.setCustomValidity('Vui lòng nhập lý do làm ngoài giờ!');\" value='" + self.lines[key].notes + "' " + disabled + "/></td>" +
                            "<td><select name='start_time' class='start_time times' " + disabled + ">" + start_option + "</select></td>" +
                            "<td><select name='end_time' class='end_time times' " + disabled + ">" + end_option + "</select></td>" +
                            "<td><input name='break_time' type='number' min='0' max='999' onblur='this.setCustomValidity(\"\");' oninvalid=\"if(this.value < 0) this.setCustomValidity('Số phút nghỉ giữa ca phải lớn hơn hoặc bằng 0!');\" class='break_time times' value='" + self.lines[key].break_time + "' " + disabled + "/></td>" +
                            "<td><input type='text' name='total_hours_register' class='total' disabled='disabled' value='" + self.lines[key].total_hours_register + "'/></td>" +
                            "<td><input type='checkbox' class='compensation_leave' " + (self.lines[key].is_compensation_leave ? "checked='checked' " : "") + lm_edit + "/>" + "</td>" +
                            (self.lines[key].readonly ? "" : "<td><i class='fa fa-trash-o fa-lg text-error'></i></td>")
                            + "</tr>";
                        i++;
                    }
                    $(self.ui.ot_container).html(html);
                    self.gen_ot_lines();
                    $(self.ui.btn_remove).click(function () {
                        var index = parseInt($(this).parent().parent().find('.line_index').val());
                        delete self.lines[index];
                        self.gen_ot_lines();
                        self.gen_table_from_ot_lines(JSON.stringify(self.lines));
                    });
                    $(self.ui.times).change(function () {
                        self.calc_total_hours($(this));
                    });
                    $(self.ui.sl_date).change(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.input_note).blur(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.cb_is_compensation_leave).click(function () {
                        self.update_lines($(this));
                    });
                },


                submitRequest: function (e) {
                    var self = this;
                    var input = $("<input>").attr({type: "hidden", name: "state"}).val("confirm");
                    if ($(self.ui.txt_reason).val()) {
                        $('form').append($(input)).submit();
                        $(self.ui.btn_confirm).prop('disabled', true);
                    } else {
                        alert('Vui lòng nhập lý do!');
                        e.preventDefault();
                    }
                },

                gen_timelines: function (hour, minute) {
                    var options = "";
                    var minutes = ['00', '15', '30', '45'];
                    for (var i = 0; i < 24; i++) {
                        for (var j = 0; j < 4; j++) {
                            if (!(i == hour && minutes[j] == minute)) {
                                options += '<option value="' + i.two_digit() + ':' + minutes[j] + '">' + i.two_digit() + ':' + minutes[j] + '</option>';
                            } else {
                                options += '<option value="' + i.two_digit() + ':' + minutes[j] + '" selected="selected">' + i.two_digit() + ':' + minutes[j] + '</option>';
                            }
                        }
                    }
                    if (options != "") {
                        if (hour == 24)
                            options += '<option value="24:00" selected="selected">midnight</option>';
                        else
                            options += '<option value="24:00">midnight</option>';
                    }
                    return options;
                },

                gen_schedule: function (s_date, s_month) {
                    var today = new Date();
                    today.setMonth(today.getMonth() - 1, 26);
                    today.setDate(26);
                    var mm = today.getMonth() + 1;
                    var option = "";
                    var count = 0;
                    while ((today.getMonth() < mm || (today.getMonth() == mm && today.getDate() < 26)) && count < 31) {
                        var d = today.getDate();
                        var m = today.getMonth() + 1;
                        var y = today.getFullYear();
                        today.setDate(d + 1);
                        if (today.getMonth() == 0 && mm == 12) mm = 0;
                        var selected = "";
                        if (d == s_date && m == s_month) {
                            selected = " selected='selected'"
                        }
                        d = d < 10 ? "0" + d : d;
                        m = m < 10 ? "0" + m : m;
                        option += "<option value='" + y + "-" + m + "-" + d + "'" + selected + ">" + d + "/" + m + "/" + y + "</option>";
                        count++;
                    }
                    return option;
                },

                add_line: function () {
                    var self = this;
                    var index = 1;
                    for (var key in self.lines) {
                        key = parseInt(key);
                        if (key >= index) {
                            index = key + 1;
                        }
                    }

                    var today = new Date();
                    var cur_d = today.getDate();
                    var cur_m = today.getMonth() + 1;
                    var cur_y = today.getFullYear();
                    var option = self.gen_schedule(cur_d, cur_m);
                    var html =
                        "<tr>" +
                        "<input class='line_index' type='hidden' value='" + index + "'/>" +
                        "<td class='hidden-xs'>" + (Object.keys(self.lines).length + 1) + "</td>" +
                        "<td>" +
                        "<select name='date_off' class='date_off'>" + option + "</select>" +
                        "</td>" +
                        "<td><input name='notes' type='text' class='notes' onblur='this.setCustomValidity(\"\");' required='required' oninvalid=\"if(!this.value) this.setCustomValidity('Vui lòng nhập lý do làm ngoài giờ!');\"/></td>" +
                        "<td><select name='start_time' class='start_time times'>" + self.gen_timelines(17, "00") + "</select></td>" +
                        "<td><select name='end_time' class='end_time times'>" + self.gen_timelines(18, "00") + "</select></td>" +
                        "<td><input name='break_time' type='number' min='0' max='999' class='break_time times' value='0' onblur='this.setCustomValidity(\"\");' oninvalid=\"if(this.value < 0) this.setCustomValidity('Số phút nghỉ giữa ca phải lớn hơn hoặc bằng 0!');\"/></td>" +
                        "<td><input type='text' name='total_hours_register' class='total' disabled='disabled' value='01:00'/></td>" +
                        "<td><input type='checkbox' checked='checked' class='compensation_leave' disabled='disabled'/></td>" +
                        "<td><i class='fa fa-trash-o fa-lg text-error'></i></td>" +
                        "</tr>";

                    self.lines[index] = {
                        'date_off': cur_y + "-" + cur_m + "-" + cur_d,
                        'notes': "",
                        'start_time': "17:00",
                        'end_time': "18:00",
                        'break_time': 0,
                        'total_hours_register': "01:00",
                        'is_compensation_leave': 1
                    };

                    $(self.ui.ot_container).append(html);
                    self.gen_ot_lines();
                    $(self.ui.btn_remove).click(function () {
                        var index = parseInt($(this).parent().parent().find('.line_index').val());
                        delete self.lines[index];
                        self.gen_ot_lines();
                        self.gen_table_from_ot_lines(JSON.stringify(self.lines));
                    });
                    $(self.ui.times).change(function () {
                        self.calc_total_hours($(this));
                    });

                    $(self.ui.sl_date).change(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.input_note).blur(function () {
                        self.update_lines($(this));
                    });
                    $(self.ui.cb_is_compensation_leave).click(function () {
                        self.update_lines($(this));
                    });
                },

                gen_ot_lines: function () {
                    $(this.ui.input_ot_lines).val(JSON.stringify(this.lines));
                },

                calc_total_hours: function (o) {
                    var self = this;
                    var index = parseInt(o.parent().parent().find('.line_index').val());
                    var start = o.parent().parent().find('.start_time').val();
                    var end = o.parent().parent().find('.end_time').val();
                    var t_break = o.parent().parent().find('.break_time').val();
                    var date_off = o.parent().parent().find('.date_off').val();

                    self.lines[index].start_time = start;
                    self.lines[index].end_time = end;
                    self.lines[index].break_time = t_break;
                    self.lines[index].date_off = date_off;

                    if (start && end && t_break && date_off) {
                        var s_date = date_off.split("-");
                        var s_start = start.split(":");
                        var s_end = end.split(":");
                        var start_date = new Date();
                        start_date.setDate(s_date[2]);
                        start_date.setMonth(parseInt(s_date[1]) - 1);
                        start_date.setFullYear(s_date[0]);
                        if (s_start[0] < 24) {
                            start_date.setHours(s_start[0]);
                        }
                        else {
                            start_date.setHours(0);
                            start_date.setDate(start_date.getDate() + 1);
                        }
                        start_date.setMinutes(s_start[1]);
                        var end_date = new Date();
                        end_date.setDate(s_date[2]);
                        end_date.setMonth(parseInt(s_date[1]) - 1);
                        end_date.setFullYear(s_date[0]);
                        if (s_end[0] < 24) {
                            end_date.setHours(s_end[0]);
                        }
                        else {
                            end_date.setHours(0);
                            end_date.setDate(end_date.getDate() + 1);
                        }
                        end_date.setMinutes(s_end[1]);

                        var diff_m = (end_date - start_date) / (60 * 1000);
                        if (diff_m <= 0) {
                            alert("Giờ ra phải lớn hơn giờ vào");
                            o.parent().parent().find('.end_time').val((parseInt(s_start[0]) + 1).two_digit() + ":" + s_start[1]);
                            self.calc_total_hours(o);
                            return;
                        }
                        var diff = diff_m - parseInt(t_break);
                        var diff_hour = Math.round(diff / 60 * 100) / 100;
                        if (diff_hour <= 0) {
                            alert("Số phút nghỉ giữa giờ phải nhỏ hơn thời gian đăng ký");
                            o.parent().parent().find('.break_time').val(0);
                            self.lines[index].break_time = 0;
                            return;
                        }
                        var total_h = Math.floor(diff / 60);
                        if (total_h >= 4 && parseInt(t_break) == 0 && o.attr('name') != "break_time") {
                            self.lines[index].break_time = 60;
                            o.parent().parent().find('.break_time').val(60);
                            total_h -= 1;
                            diff -= 60;
                        }
                        var total_m = parseInt(diff - total_h * 60);
                        var total_val = total_h.two_digit() + ":" + total_m.two_digit();
                        o.parent().parent().find('.total').val(total_val);
                        self.lines[index].total_hours_register = total_val;
                        self.gen_ot_lines();
                        console.log(self.lines);
                    }
                },

                update_lines: function (o) {
                    var self = this;
                    var index = parseInt(o.parent().parent().find('.line_index').val());
                    var date_off = o.parent().parent().find('.date_off').val();
                    var notes = o.parent().parent().find('.notes').val();
                    var is_compensation_leave = o.parent().parent().find('.compensation_leave').prop('checked') ? 1 : 0;

                    self.lines[index].date_off = date_off;
                    self.lines[index].notes = notes;
                    self.lines[index].is_compensation_leave = is_compensation_leave;
                    self.gen_ot_lines();

                }
            });
        }
		return OvertimeFormView;
	}
);
