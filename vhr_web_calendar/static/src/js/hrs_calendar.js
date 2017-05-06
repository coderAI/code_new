/**
 * Created by giaosudau on 15/09/2014.
 */

openerp.vhr_web_calendar = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt,
        QWeb = instance.web.qweb;

    /* initial view type */

    instance.web.views.add('hrs_calendar', 'instance.vhr_web_calendar.CalendarView');

    var B = Backbone;
    /*
     * DateModel
     * */
    var DateModel = B.Model.extend({
        initialize: function (options) {
            this.day = options.day
            this.month = options.month
            this.year = options.year
            this.name = moment({year: this.year, month: this.month, day: this.day}).format("ddd");
            this.full_name = moment({year: this.year, month: this.month, day: this.day}).format("YYYY-MM-DD");
        }
    })


    var MonthModel = B.Model.extend({
        initialize: function (options) {
            this.month = options.month
            this.year = options.year
            this.name = moment({year: this.year, month: this.month}).format("MMM");
            var days = new Date(this.year, this.month + 1, 0).getDate();
            this.days = []
            var self = this
            if (days)
                _.each(_.range(1, days + 1), function (e) {
                    var date = new DateModel({day: e, month: self.month, year: self.year})
                    self.days.push(date)
                })
        }
    });
    var CalendarCollection = B.Collection.extend({
        model: MonthModel
    });

    var Toolbar = B.View.extend({
            template: 'CalendarExtraView.toolbar',
            initialize: function (options) {
                this.message = options.message
                this.data = options.data
            },
            render: function () {
                var self = this
                this.$el.html(QWeb.render(this.template, {data: this.data, message: this.message}))
                this.$el.find('#filter_year').val(moment().year())

                _.each(this.data, function (field_data) {
                    var data = []
                    _.each(field_data.data, function (item) {
                        item['text'] = item['code'] + ' - ' + item['name']
                        if (!item.hasOwnProperty('color_name')) {
                            item['color_name'] = 'yellow'
                        }
                        data.push(item)
                    })
                    function format(val) {
                        if (!val.id) return val.text; // optgroup
                        if (val.hasOwnProperty('color_name')) {
                            return "<i class='fa fa-square fa-" + val.color_name + "'></i>  " + val.text;
                        }
                    }

                    self.$el.find('div[name*="' + field_data.name + '"]').select2({
                        allowClear: true,
                        placeholder: 'Select',
                        formatResult: format,
                        formatSelection: format,
                        escapeMarkup: function (m) {
                            return m;
                        },
                        initSelection: function (element, callback) {
                            var data = _.filter(field_data.data, function (item) {
                                return item.id == element.val()
                            })
                            callback(data && data[0] || {});
                        },
                        width: "250px",
                        data: data
                    });

                })
            }
        }
    )

    var MonthView = B.View.extend({
        template: 'CalendarExtraView.month',

        initialize: function (options) {
            this.collection = options.collection
            this.listenTo(this.collection, "change", this.render, this);
        },
        render: function () {
            $(this.el).empty().append(QWeb.render(this.template, {models: this.collection.models}))

        }
    });
//    hide searchview when load type hrs_calendar

    instance.web.ViewManagerAction.include({
        switch_mode: function (view_type, no_store, options) {
            var self = this;
            return this.alive($.when(this._super.apply(this, arguments))).done(function () {
                var controller = self.views[self.active_view].controller;
                self.$el.find('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                    view: controller,
                    view_manager: self
                }));
                self.set_title();
                if (view_type == 'hrs_calendar') {
                    self.$el.find('div.oe_searchview').toggle()
                }
            });
        },
    })

    instance.vhr_web_calendar.CalendarView = instance.web.View.extend({
        template: "CalendarExtraView",
        display_name: _lt('Full Calendar'),
        view_type: 'hrs_calendar',
        events: {
            'dblclick td.date div.editable': 'generate_record_values',
            'click #btn-save': 'save_calendar',
            'click #btn-clear': 'clear_calendar',
            'blur td.date div.editable': 'manual_input_value',
            'change #filter_year, #filter_month': 'filter_check',
            'change #filter_year': 'filter_domain',
            'change #filter_month': 'filter_domain',
            'change #search_field': 'filter_domain'
        },
        init: function (parent, dataset, view_id, options) {
            this._super(parent);
            this.ready = $.Deferred();
            this.set_default_options(options);
            this.dataset = dataset;
            this.model = dataset.model;
            this.fields_view = {};
            this.view_id = view_id;
            this.view_type = 'hrs_calendar';
        },
        start: function () {
            return this.load_view();
        },
        read_data: function () {
            var promises = [];
            def = $.Deferred();
            var fields = _.keys(this.fields);
            var self = this
            var index = 0
            _.each(fields, function (field_name) {

                var def = new $.Deferred();
                var child_attrs = _.filter(self.fields_view.arch.children, function (item) {
                    return item.attrs.name == field_name
                })[0]
                var modifiers = JSON.parse(child_attrs.attrs.modifiers)
                var n_domain = child_attrs.attrs.domain || [];
                n_domain = instance.web.pyeval.eval('domain', n_domain || [], {});

                var search = child_attrs.attrs.search != undefined ? true : false
                var code = child_attrs.attrs.code != undefined ? true : false
                var color = child_attrs.attrs.color != undefined ? true : false
                var field = self.fields[field_name];
                field['domain'] = n_domain || field['domain']
                
              //Get context of field from hrs_calendar view
                var context_attrs =  instance.web.pyeval.eval('context', child_attrs.attrs.context);
                if (context_attrs)
                	{
                	field.context = context_attrs || field.context
                	}
                
                var model_obj = new instance.web.DataSetSearch(this, field.relation, field.context, field.domain);
                model_obj.read_slice(['name', 'code', 'id', 'color_name'], {}).done(function (res) {
                    if (search == 1) {
                        self.list_fields_search_data.push({name: field_name, label: field.string, data: res, modifiers: modifiers, search: search})
                        self.search_field.push(field_name)
                    }
                    else if (code) {
                        self.code_data.push({name: field_name, label: field.string, data: res, modifiers: modifiers, search: search})
                        self.fields_code.push(field_name)
                        _.each(this.code_data, function (data) {
                            _.each(data.data, function (item) {
                                    self.color_map[item.code] = item.color_name
                                }
                            )
                        })
                    }
                    if (color) {
                        self.color_field['name'] = field_name
                        _.each(res, function (item) {
                            self.color_map[item.id] = item.color_name
                        })
                    }
                    if (modifiers.invisible != true)
                        self.data.push({name: field_name, label: field.string, data: res, modifiers: modifiers, search: search})
                    def.resolve(res);
                })
                promises.push(def);
                index++
            })
            return $.when.apply(undefined, promises).promise();
        },
        load_hrs_calendar: function (fv) {
            this.fields_view = fv;
            this.is_display_sat = fv.arch.attrs.is_display_sat === 'false' ? false : true
            this.is_display_sun = fv.arch.attrs.is_display_sun === 'false' ? false : true
            this.color = fv.arch.attrs.color === 'false' ? false : true
            this.reference = fv.arch.attrs.reference
            this.reference_field = fv.arch.attrs.reference_field
            this.message = fv.arch.attrs.message
            this.field_date = fv.arch.attrs.field_date || 'date'
            this.default_get_fields = fv.arch.attrs.default_get_fields || []
//            get attrs
            this.fields = fv.fields;
            var self = this
            this.fields_list = _.keys(this.fields)
            this.data = []
            this.list_fields_search_data = []
            this.search_field = []
            this.fields_code = []
            this.code_data = []
            this.color_map = {}
            this.color_field = {}
//
            this.ViewManager.on('switch_mode', this, function (e) {
                if (e === 'hrs_calendar' && !self.toolbar) {
                    $.when(self.read_data()).done(function () {
                        self.toolbar = new Toolbar({ el: 'div.toolbar', data: self.data, message: self.message})
                        self.$el.find('div.toolbar').empty().append(self.toolbar.render())
                    })
                }
            });
        },

        view_loading: function (fv) {
            return this.load_hrs_calendar(fv);
        },

        manual_input_value: function (e) {
            var allCode = []
            _.each(this.code_data, function (data) {
                _.each(data.data, function (item) {
                    allCode.push(item.code)
                })
            })
            var value = e.target.textContent.replace(/\s/g, "").toUpperCase()
            $(e.target).text(value)
            if (value !== "" && _.indexOf(allCode, value) == -1) {
                $(e.target).css({'border-color': 'red'})
                this.$el.find('div#divValid').show()
            }
            else {
                this.generate_record_values(e, true)
                this.$el.find('div#divValid').hide()
                $(e.target).css({'border-color': '#7f9db9'})
            }
        },
        clear_calendar: function () {
            _.each(this.$el.find("td.date"), function (item) {
                var div_item = $(item).find('div');
                var record_id = parseInt(div_item.attr('id'));
                if (record_id) {
                    div_item.attr('delete', "1")
                }
                else {
                    div_item.removeAttr('data')
                }
            })
        },
        save_calendar_callback: function(result){
        	var self = this
            var fields_value = {}
            var missing_field = '';
        	var d = $.Deferred();
        	d.resolve('');
            _.each(this.list_fields_search_data, function (field) {
                var field_search_data = self.$el.find('div[name*="' + field.name + '"]').select2('data');
                if (field_search_data) {
                    fields_value[field.name] = field_search_data.id
                }
                else {
                    missing_field += field.label
                }
            })
            if (_.isEmpty(fields_value) && this.search_field.length > 0) {
            	//Call d.reject to caller know that save_calendar_callback not success
            	d = $.Deferred();
            	d.reject;
                new instance.web.Dialog(this, {
                    title: _t('Information'),
                    size: 'medium',
                    buttons: [
                        {text: _t("Ok"), click: function () {
                            this.parents('.modal').modal('hide');
                        }
                        },
                    ],
                }, $("<div />").text(_t("You must choose " + missing_field + " to set!"))).open();

                return d.promise();
            }
            var delete_record_ids = []
            _.each(this.$el.find("td.date"), function (item) {
                var div_item = $(item).find('div');
                var div_data = div_item.attr('data');
                var reference_data = div_item.attr('reference_data');
                var record_id = parseInt(div_item.attr('id'));

                if (record_id && div_item.attr('delete') != undefined) {
                    delete_record_ids.push(record_id)
                }
                else {
                    if (div_data != undefined) {
                        div_data = JSON.parse(div_data)
                    }
                    else {
                        div_data = {}
                    }
                    if (reference_data != undefined) {
                        reference_data = JSON.parse(reference_data)
                        div_data = $.extend({}, reference_data, div_data, fields_value);
                    }
                    if (_.isEmpty(div_data)) {
                    	//Call d.reject to caller know that save_calendar_callback not success
                    	d.reject;
                    	return d.promise();
                    }
                    else if (record_id) {
                        div_data['name'] = div_item.text().trim()
                        self.dataset.write(record_id, div_data, {}).done(function (id) {
                        })
                    }
                    else {
                    	d = $.Deferred();
                    	div_data = $.extend({}, result, div_data);
                    	self.dataset.create(div_data).done(function (id) {
                    		d.resolve(id);
                    		$(div_item).attr({'id': id});
                            
                        }).fail(d.reject); //Call d.reject to caller know that have error during create new record

                    }
                }

            })
            if (delete_record_ids) {
                this.dataset.unlink(delete_record_ids);
            }
            
            return d.promise();
        },
        save_calendar: function () {
        	var self = this;
        	//Get default_get data for create record
        	self.dataset.default_get([]).then(function(result){
        		//Call function save_calendar_callback with input is default_get data
        		$.when(self.save_calendar_callback(result)).done(function(p){
        			//Only alert message 'Save Calendar successfully if save_calendar_callback success'
        			new instance.web.Dialog(this, {
                        title: _t('Information'),
                        size: 'medium',
                        buttons: [
                            {text: _t("Ok"), click: function () {
                                this.parents('.modal').modal('hide');
                            }
                            },
                        ],
                    }, $("<div />").text(_t("Save Calendar successfully!"))).open();
        		});
        	});
        },
        generate_record_values: function (e, user_input) {
            var self = this
            var set_code = ''
            var fields_value = {}
            if (!user_input) {
                _.each(this.fields_list, function (field) {
                    var field_search_data = self.$el.find('div[name*="' + field + '"]').select2('data');
                    if (field_search_data) {
                        fields_value[field] = field_search_data.id
                        if (self.fields_code.indexOf(field) != -1) {
                            set_code = field_search_data.code;
                        }
                    }
                })
                $(e.target).text(set_code)
            }
            else {
                var values = {}

                _.each(this.search_field, function (field) {
                    var field_search_data = self.$el.find('div[name*="' + field + '"]').select2('data');
                    if (field_search_data) {
                        fields_value[field] = field_search_data.id
                    }
                })
                _.each(this.code_data, function (data) {
                    _.each(data.data, function (item) {
                            if (item.code === e.target.textContent) {
                                set_code = item.code
                                values[data.name] = item.id
                            }
                        }
                    )
                })
                fields_value = $.extend({}, fields_value, values)
            }
            var record_id = parseInt(e.target.id)
            var date = e.target.parentNode.id

            if (record_id && set_code) {
                $(e.target).attr({'data': JSON.stringify(fields_value)})
            }
            else if (set_code && fields_value && date) {
                var values = {}
                values[this.field_date] = date
                values['name'] = set_code
                values = $.extend({}, fields_value, values)
                $(e.target).attr({'data': JSON.stringify(values)})
            }
            else if (record_id || $(e.target).attr('data')) {
            	$(e.target).attr({'data': JSON.stringify({})});
                $(e.target).attr({delete: "1"})
            }

        },
        filter_domain: function (e) {
            var month = $('#filter_month').val();
            this.current_year = $('#filter_year').val();
            var self = this
            this.last_domain = _.filter(this.last_domain, function (domain) {
                return self.search_field.indexOf(domain[0]) == -1;
            });
            var null_search_field = 0
            _.each(this.search_field, function (field) {
                var field_value = ''
                var field_search_data = self.$el.find('div[name*="' + field + '"]').select2('data');
                if (field_search_data) {
                    field_value = field_search_data.code
                    self.last_domain.push([field, '=', field_value])
                }
                else {
                    null_search_field++
                }
            })
            /*
             * Clean calendar when not enough condition to search
             * */
            if (this.search_field.length > 0 && null_search_field == this.search_field.length) {
                this.$el.find('td.date').find('div').text('')
                this.$el.find('td.date').find('div').text('')
                return;
            }
            if (this.current_year === '' || parseInt(this.current_year) < 1900) {
                return;
            }

            if (parseInt(month) < 1 || parseInt(month) > 12) {
                return;
            }
//                remove previous domain
            for (var i = this.last_domain.length - 1; i >= 0; i--) {
                if (this.last_domain[i][0] === 'year') {
                    this.last_domain.splice(i, 1);
                }
                else if (this.last_domain[i][0] === 'month') {
                    this.last_domain.splice(i, 1);
                }
            }
            if (month) {
                this.last_domain.push(['month', '=', parseInt(month)])
            }

            this.last_domain.push(['year', '=', this.current_year])
            this.action_search(this.last_domain, this.last_context, this.last_group_by, true)
        },
        filter_check: function () {
            var year = $('#filter_year').val();
            var month = $('#filter_month').val();
            var $error_message = this.$el.find('#error_message');
            if (year === '' || parseInt(year) < 1900) {
                $error_message.text('Please enter valid year > 1900').css({visibility: 'visible'})
                return;
            }

            if (parseInt(month) < 1 || parseInt(month) > 12) {
                $error_message.text('Please enter valid month').css({visibility: 'visible'})
                return;
            }
            $error_message.css({visibility: 'hidden'})
        },
        do_search: function (domain, context, group_by) {
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.action_search(this.last_domain, this.last_context, this.last_group_by);

        },
        mark_color: function (domain, context, load_record) {
            var self = this
            /*
             * TODO: Refactor here
             * Mark color of object reference
             * */
            if (this.reference && this.reference_field) {
                var model_obj = new instance.web.DataSet(this, this.reference)
                model_obj.read_slice(['date', this.reference_field, 'color_name'], {domain: [
                    ['year', '=', self.current_year]
                ]}).done(function (res) {
                    _.each(res, function (item) {
                        var cell = self.$el.find('td#' + item.date).find('div')
                        var field_name = self.reference_field
                        var reference_data = {}
                        reference_data[field_name] = item[field_name][0]
                        reference_data['date'] = item.date
                        if (self.color_field) {
                            var color_name = self.color_map[item[field_name][0]]
                            $(cell).css({'background-color': color_name})
                        }
                        $(cell).attr('reference_data', JSON.stringify(reference_data))
                    })
                })
            }
            /*
             * ONLY LOAD REFERENCE
             * */
            if (!load_record) {
                return true
            }

            /*
             * MARK COLOR FOR RECORD
             * */
            this.dataset.read_slice(['name', 'date', 'color_name'], {
                domain: domain,
                context: context
            }).done(function (res) {
                _.each(res, function (item) {
                    var cell = self.$el.find('td#' + item.date).find('div')
                    $(cell).css({'background-color': item.color_name})
                    if (item.name)
                        $(cell).text(item.name)
                    $(cell).attr({'id': item.id})
                })
            });
        },
        action_search: function (domain, context, group_by, filter_by_action) {
            var self = this
            var months = new CalendarCollection
            var count = 0
            var year = moment().year()
            var month = -1

            _.each(domain, function (item) {
                if (item[0] == 'year') {
                    year = item[2]
                }
                else if (item[0] == 'month') {
                    month = item[2]
                }
                else if (year != moment().year()) {
                    domain.push(['year', '=', year])
                }
            })

            if (month >= 0) {
                var instance = new MonthModel({year: year, month: month - 1})
                months.add(instance)
            }
            if (months.length == 0)
                while (count < 12) {
                    var instance = new MonthModel({year: year, month: count++})
                    months.add(instance)
                }
            if (!this.month_view)
                this.month_view = new MonthView({collection: months, el: $(this.$el.find('tbody'))})
            else {
                this.month_view.collection = months;
            }


            $.when(self.$el.find('tbody').empty().append(self.month_view.render())).then(function () {
                if (!self.reference && !filter_by_action) {
                    filter_by_action = true
                }
                if (filter_by_action === true) {
                    self.mark_color(domain, context, true);
                }
                else {
                    self.mark_color(domain, context, false);
                    _.each(self.search_field, function (field) {
                        self.$el.find('div[name*="' + field + '"]').select2('val', "");
                    })
                }
            })
//            adjust view

            this.$el.find('#filter_year').val(year)
            this.$el.find('#filter_month').val(month > 0 ? month : '')
//            display sun / sat or not
            if (!this.is_display_sun)
                this.$el.find('td.Sun div').css("background-color", "transparent");
            if (!this.is_display_sat)
                this.$el.find('td.Sat div').css("background-color", "transparent");
        },

        destroy: function () {
            this._super.apply(this, arguments);
        }
    })


}