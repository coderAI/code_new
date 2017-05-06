/**
 * Created by HungPD on 4/7/2015.
 */

function numberFormat(_number, _sep) {
    _number = typeof _number != "undefined" && _number > 0 ? _number : "";
    _number = String(_number);
    _number = _number.replace(new RegExp("^(\\d{" + (_number.length%3? _number.length%3:0) + "})(\\d{3})", "g"), "$1 $2").replace(/(\d{3})+?/gi, "$1 ").trim();
    if(typeof _sep != "undefined" && _sep != " ") {
        _number = _number.replace(/\s/g, _sep);
    }
    return _number;
}

var lines = {};

$(document).ready(function () {
    if ($("#message").val() != undefined && $("#message").val() != '' && $("#message").val() != null ){
        $("#popup").bPopup();
    }
    $('#lti-type').select2()
        .on("change", function(e) {
            if (e.val == 'bonnus'){
                $('#vested').val($('#vesting').val());
                $('input').attr('disabled', 'disabled');
            }
            if (e.val == 'esop'){
                $('#vested, #vesting, #payment_date').removeAttr('disabled');
            }
        });
    $('.input-append.date').datepicker({autoclose: true, todayHighlight: true});

    $("#vested").keydown(function (e) {
        // Allow: backspace, delete, tab, escape, enter and .
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 13, 110, 190]) !== -1 ||
             // Allow: Ctrl+A
            (e.keyCode == 65 && e.ctrlKey === true) ||
             // Allow: home, end, left, right, down, up
            (e.keyCode >= 35 && e.keyCode <= 40)) {
                 // let it happen, don't do anything
                 return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    }).blur(function (e) {
        var vesting_qty = parseInt($("#vesting").val().replace(/,/g, ''));
        var vested_qty = parseInt($("#vested").val().replace(/,/g, ''));
        var price = parseInt($("#price").val().replace(/,/g, ''));
        if(vested_qty && vesting_qty && vested_qty > vesting_qty){
            alert('Số lượng đăng ký phải nhỏ hơn hoặc bằng số lượng quyền mua!');
            $("#vested").val(null);
        }
        else if(vested_qty && vesting_qty && vested_qty <= vesting_qty){
            $("#total_amt").val(numberFormat(vested_qty * price, ','));
            $("#vested").val(numberFormat(vested_qty, ','));
        }

    });


    $("#sellback_qty").keydown(function (e) {
        // Allow: backspace, delete, tab, escape, enter and .
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 13, 110, 190]) !== -1 ||
             // Allow: Ctrl+A
            (e.keyCode == 65 && e.ctrlKey === true) ||
             // Allow: home, end, left, right, down, up
            (e.keyCode >= 35 && e.keyCode <= 40)) {
                 // let it happen, don't do anything
                 return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    }).blur(function (e) {
        var sellback_qty = parseInt($("#sellback_qty").val().replace(/,/g, ''));
        var total_qty = parseInt($("#stock_qty").val().replace(/,/g, ''));
        var sellback_price = parseInt($("#sellback_price").val().replace(/,/g, ''));
        if(sellback_qty && total_qty && sellback_qty > total_qty){
            alert('Số lượng đăng ký bán phải nhỏ hơn hoặc bằng lượng sở hữu');
            $("#sellback_qty").val(null);
        }

        else if(sellback_qty && total_qty && sellback_qty <= total_qty){
            $("#total_amt").val(numberFormat(sellback_qty * sellback_price, ','));
        }
    });

    $("#payment_date").change(function () {
        var confirm_date = $("#confirm_date").val();
        var payment_date = $("#payment_date").val();
        var psplit = payment_date.split("/");
        var csplit = confirm_date.split("/");
        if(payment_date != null && new Date(psplit[2], psplit[1]-1, psplit[0]) < new Date(csplit[2], csplit[1]-1, csplit[0]))
        {
            alert('Ngày dự kiến chuyển tiền phải lớn hơn hoặc bằng ngày ' + confirm_date);
            $("#payment_date").val(null);
        }
    });

    if($('#other_bank').prop('checked')) {
        $('#other_bank_title').show();
        $('#other_bank_info').show();
    } else {
        $('#other_bank_title').hide();
        $('#other_bank_info').hide();
    }

    $('#other_bank').click(function () {
        if($('#other_bank').prop('checked')) {
            $('#other_bank_title').show();
            $('#other_bank_info').show();
        } else {
            $('#other_bank_title').hide();
            $('#other_bank_info').hide();
        }
    });

    $('#reg_vested_qty').keydown(function (e) {
        // Allow: backspace, delete, tab, escape, enter and .
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 13, 110, 190]) !== -1 ||
             // Allow: Ctrl+A
            (e.keyCode == 65 && e.ctrlKey === true) ||
             // Allow: home, end, left, right, down, up
            (e.keyCode >= 35 && e.keyCode <= 40)) {
                 // let it happen, don't do anything
                 return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    }).blur(function (e) {
        var vested_qty = parseInt($("#reg_vested_qty").val().replace(/,/g, ''));
        var total_qty = parseInt($("#total_stock").html().replace(/,/g, ''));
        if(vested_qty && total_qty && vested_qty > total_qty){
            alert('Số lượng đăng ký phải nhỏ hơn hoặc bằng số lượng quyền mua có thể thực thi.');
            $("#reg_vested_qty").val(null);
        }
    });

    $("#form-vesting").submit(function(e) {
        $("#btn_confirm_vesting").prop('disabled', true);
    });
});
