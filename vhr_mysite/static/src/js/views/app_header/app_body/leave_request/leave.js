var lines = {};
function gen_leave_lines() {
    $('input[name="leave_detail_lines"]').val(JSON.stringify(lines));
}

function add_event_click(){
    $(".shift_d").click(function () {
        var leave_register = parseFloat($("#leave_register").html().trim());
        var i = $(this).parent().parent().find('.line_index').html();
        if(!$(this).prop('checked')) {
            $(this).parent().parent().find('.all_day').prop('checked', false);
            lines[i]['all_day'] = 0;
            leave_register -= 0.5;
        }else{
            if ($(this).parent().parent().find('.shift_n').prop('checked')){
                $(this).parent().parent().find('.all_day').prop('checked', true);
                lines[i]['all_day'] = 1;
            }
            leave_register += 0.5;
        }
        lines[i]['shift_d'] = $(this).prop('checked') ? 1:0;;
        gen_leave_lines();
        $("#leave_register").html(leave_register);
    });
    $(".shift_n").click(function () {
        var leave_register = parseFloat($("#leave_register").html().trim());
        var i = $(this).parent().parent().find('.line_index').html();
        if(!$(this).prop('checked')) {
            $(this).parent().parent().find('.all_day').prop('checked', false);
            lines[i]['all_day'] = 0;
            leave_register -= 0.5;
        }else{
            if ($(this).parent().parent().find('.shift_d').prop('checked')){
                $(this).parent().parent().find('.all_day').prop('checked', true);
                lines[i]['all_day'] = 1;
            }
            leave_register += 0.5;
        }
        lines[i]['shift_n'] = $(this).prop('checked') ? 1:0;;
        gen_leave_lines();
        $("#leave_register").html(leave_register);
    });
    $(".all_day").click(function () {
        var leave_register = parseFloat($("#leave_register").html().trim());
        var i = $(this).parent().parent().find('.line_index').html();
        if(!$(this).prop('checked')) {
            $(this).parent().parent().find('.shift_d').prop('checked', false);
            $(this).parent().parent().find('.shift_n').prop('checked', false);
            lines[i]['shift_d'] = 0;
            lines[i]['shift_n'] = 0;
            leave_register -= 1;
        }else{
            $(this).parent().parent().find('.shift_d').prop('checked', true);
            $(this).parent().parent().find('.shift_n').prop('checked', true);
            lines[i]['shift_d'] = 1;
            lines[i]['shift_n'] = 1;
            leave_register += 1;
        }
        lines[i]['all_day'] = $(this).prop('checked') ? 1:0;
        gen_leave_lines();
        $("#leave_register").html(leave_register);
    });
}

function gen_leave_detail_table(date_from, date_to) {
    var html = "";
    lines = {};
    if (date_from && date_to){
        var f_split = date_from.split("/");
        var t_split = date_to.split("/");
        var dFrom = new Date(f_split[2], f_split[1]-1, f_split[0]);
        var dTo = new Date(t_split[2], t_split[1]-1, t_split[0]);
        var diff = (dTo - dFrom)/(24*60*60*1000) + 1;
        if (diff > 0){
            for (var i = 0; i < diff; i++){
                html += "<tr>" +
                            "<td class='line_index'>" + (i+1) + "</td>" +
                            "<td>" + (parseInt(f_split[0]) + i) + '/' + f_split[1] + '/' + f_split[2] + "</td>" +
                            "<td>" + "<input type='checkbox' class='shift_d' checked='checked'/>" + "</td>" +
                            "<td>" + "<input type='checkbox' class='shift_n' checked='checked'/>" + "</td>" +
                            "<td>" + "<input type='checkbox' class='all_day' checked='checked'/>" + "</td>" +
                        "</tr>";
                lines[i+1] = {'shift_d': 1, 'shift_n': 1, 'all_day': 1, 'date': (f_split[2] + '-' + f_split[1] + '-' + (parseInt(f_split[0]) + i))};
            }

            $("#leave_register").html(diff);
        }else{
            alert('Ngày kết thúc phải lớn hơn ngày bắt đầu!');
            $("#date_to").val(null);
        }
    }
    $("#tb-leave-container").html(html);
    gen_leave_lines();
    add_event_click();
}

function gen_table_from_leave_lines(leave_lines) {
    var html = "";
    lines = JSON.parse(leave_lines);

    for (var key in lines){
        html += "<tr>" +
                    "<td class='line_index'>" + key + "</td>" +
                    "<td>" + lines[key].date + "</td>" +
                    "<td>" + "<input type='checkbox' class='shift_d' " + (lines[key].shift_d ? "checked='checked' ": "") + (lines[key].readonly ? "disabled='disabled' ": "") + "/>" + "</td>" +
                    "<td>" + "<input type='checkbox' class='shift_n' " + (lines[key].shift_n ? "checked='checked' ": "") + (lines[key].readonly ? "disabled='disabled' ": "") + "/>" + "</td>" +
                    "<td>" + "<input type='checkbox' class='all_day' " + (lines[key].all_day ? "checked='checked' ": "") + (lines[key].readonly ? "disabled='disabled' ": "") + "/>" + "</td>" +
                "</tr>";
    }
    $("#tb-leave-container").html(html);
    gen_leave_lines();
    add_event_click();
}

$(document).ready(function () {
    var date_from = $("#date_from");
    var date_to = $("#date_to");
    var max_allow = parseFloat($("#max_allow").html().trim());
    var leave_lines = $('input[name="leave_detail_lines"]').val();
    if (date_from && date_to && !leave_lines && max_allow >= 0){
         gen_leave_detail_table(date_from.val(), date_to.val());
    }
    else if (leave_lines){
        leave_lines = leave_lines.replace(/'/g, '"');
        gen_table_from_leave_lines(leave_lines);
    }
});
