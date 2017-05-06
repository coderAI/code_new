'use strict';

define(
    ["marionette"],
    function(Marionette){
        var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;

        var LiabilityListView = ItemView.extend({

            initialize: function(options) {

				_super.initialize.apply(this, arguments);

                var self = this;

                $(self.ui.tableLiabilities).dataTable();

                $(self.ui.inputDateFrom).datepicker()
                    .on('changeDate', self.onchangeDate.bind(self));
                $(self.ui.inputDateTo).datepicker()
                    .on('changeDate', self.onchangeDate.bind(self));
			},

			el: '.liability_list_view',

			template: false,

            ui: {
                //INPUT
                inputDocumentNo: 'input#document_no',
                inputDateFrom: 'input#date_from',
                inputDateTo: 'input#date_to',
                inputDomain: 'input#domain',
                //SELECT
                //TEXTAREA
                //BUTTON
                buttonSearch: 'button#btn_search',
                //TABLE
                tableLiabilities: 'table#table_liabilities'
            },

            events: {
                //CHANGE
                //CLICK
                'click @ui.buttonSearch': 'getDomainBeforeSubmit'
            },

            _getStrDate: function(strDate){
                if(!strDate){
                    return "";
                }
                var temp = strDate.split("/");
                return temp[2] + "-" + temp[1] + "-" + temp[0];
            },

            _convertToDate: function(strDate){
                if(!strDate){
                    return null;
                }
                var temp = strDate.split("/");
                return new Date(temp[2], temp[1] - 1, temp[0])
            },

            onchangeDate: function(event){
                var self = this;
                var eleDateTo = $(self.ui.inputDateTo);
                var dateFromVal = $(self.ui.inputDateFrom).val();
                var dateToVal = eleDateTo.val();
                var dateFrom = (dateFromVal) ? self._convertToDate(dateFromVal) : '';
                var dateTo = (dateToVal) ? self._convertToDate(dateToVal) : '';
                if (dateFrom && dateTo && dateFrom > dateTo){
                    alert("Ngày Đến phải lớn hơn Ngày Từ");
                    eleDateTo.val("");
                }
            },

            getDomainBeforeSubmit: function(event){
                var self = this;
                var domain = "[";
                var documentNo = $(self.ui.inputDocumentNo).val();
                if(documentNo){
                    domain += "('document_no', 'ilike', '" + documentNo + "')";
                }
                var dateFromVal = $(self.ui.inputDateFrom).val();
                var dateToVal = $(self.ui.inputDateTo).val();
                var dateFrom = (dateFromVal) ? self._getStrDate(dateFromVal) : '';
                var dateTo = (dateToVal) ? self._getStrDate(dateToVal) : '';
                if(dateFrom){
                    if(documentNo){
                        domain += ", ";
                    }
                    domain += "('document_day', '>=', '" + dateFrom + "')";
                }
                if(dateTo){
                    if(documentNo || dateFrom){
                        domain += ", ";
                    }
                    domain += "('document_day', '<=', '" + dateTo + "')";
                }
                domain += "]";
                $(self.ui.inputDomain).val(domain);
            }

        });

        return LiabilityListView;
    }
);
