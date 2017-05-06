/**
 * Created by giaosudau on 10/11/2014.
 */

openerp.vhr_monthly_calendar = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt,
        QWeb = instance.web.qweb;

    /* initial view type */

    instance.web.views.add('monthly_calendar', 'instance.vhr_monthly_calendar.CalendarView');

    var B = Backbone;
    /*
     * DateModel
     * */
    var DateModel = B.Model.extend({
        initialize: function (options) {
            if (options.day < 10) {
                this.day = '0' + options.day
            }
            else
                this.day = options.day
            this.month = options.month
            this.year = options.year
            this.name = moment({year: this.year, month: this.month, day: this.day}).format("ddd");
            this.full_name = moment({year: this.year, month: this.month, day: this.day}).format("YYYY-MM-DD");
        }
    })

    var LineView = B.View.extend({
        template: 'MonthlyView.line',

        initialize: function (options) {
            this.data = options.data
            this.display_fields = options.display_fields
            this.dateRange = options.dateRange
        },
        render: function () {
            $(this.el).empty().append(QWeb.render(this.template, {display_fields: this.display_fields, data: this.data, dateRange: this.dateRange}))

        }
    });

    var HeaderView = B.View.extend({
        template: 'MonthlyView.header',

        initialize: function (options) {
            this.display_fields = options.display_fields
            this.dateRange = options.dateRange
        },
        render: function () {
            $(this.el).empty().append(QWeb.render(this.template, {display_fields: this.display_fields, dateRange: this.dateRange}))

        }
    });


    instance.vhr_monthly_calendar.CalendarView = instance.web.View.extend({
        template: "MonthlyView",
        display_name: _lt('Full Calendar'),
        view_type: 'monthly_calendar',
        events: {
            'change #filter_year': 'filter_domain',
            'change #filter_month': 'filter_domain',
            'change .oe_list_record_selector input': 'select_record',
            'click thead .headcol ': 'select_all_record',
            'click input[name=filter_state]': 'filter_state',
            'change #filter_leave': 'filter_state',
            'click .oe_monthly_button_send': 'do_sent',
            'click .oe_monthly_button_approve': 'do_approve',
            'click .oe_monthly_button_reject': 'do_reject',
            'click .link_to_leave_request': 'go_to_leave_request_employee',
        },
        defaults: {
            limit: 40
        },

        
        init: function (parent, dataset, view_id, options) {
            this._super(parent);
            this.ready = $.Deferred();
            this.set_default_options(options);
            this.dataset = dataset;
            this.model = dataset.model;
            this.fields_view = {};
            this.view_id = view_id;
            this.view_type = 'monthly_calendar';
            this.page = 0;
        },
        start: function () {
        	return this.load_view();
        },
        /*
         * TODO later
         * */
        is_action_enabled: function (action) {
            var attrs = this.fields_view.arch.attrs;
            return (action in attrs) ? JSON.parse(attrs[action]) : true;
        },
        do_select: function (ids) {
            // uncheck header hook if at least one row has been deselected
            if (!ids.length) {
                this.dataset.index = 0;
                if (this.sidebar) {
                    this.sidebar.$el.hide();
                }
                this.compute_aggregates();
                return;
            }
            this.dataset.index = _(this.dataset.ids).indexOf(ids[0]);
            if (this.sidebar) {
                this.options.$sidebar.show();
                this.sidebar.$el.show();
            }
        },
        do_delete: function (ids) {
        	
            if (!(ids.length && confirm(_t("Do you really want to remove these records?")))) {
                return;
            }
            this.$el.find("button").hide()
            var self = this;
            return $.when(this.dataset.unlink(ids)).done(function () {
                _(self.records).each(function (line_number) {
                    self.$el.find("[line-number='" + line_number + "']").closest('tr').remove()
                });
                self.total -= self.records.length
                if (self.records.length === 0 && self.total > 0) {
                    //Trigger previous manually to navigate to previous page,
                    //If all records are deleted on current page.
                    self.$pager.find('ul li:first a').trigger('click');
                } else if (self.records.length == self.limit()) {
                    //Reload listview to update current page with next page records
                    //because pager going to be hidden if dataset.size == limit
                    self.reload();
                } else {
                    self.configure_pager();
                }
            });
        },
        do_delete_selected: function () {
            if (this.ids.length) {
                this.do_delete(this.ids);
            } else {
                this.do_warn(_t("Warning"), _t("You must select at least one record."));
            }
        },
        select_all_record: function (e) {
            this.$el.find('.oe_list_record_selector input').prop('checked',
                    this.$el.find('.oe_list_record_selector').prop('checked') || false);

            this.select_record(e)
        },
        select_record: function (e) {
            /*
             * Stupid code goes here
             * */
            var self = this
            self.ids = []
            self.records = []
            _.each(self.$el.find(".oe_list_record_selector input:checked:enabled").closest('tr').find('span'), function (span) {
                self.ids.push(parseInt($(span).attr('id')))
            })
            _.each(self.$el.find(".oe_list_record_selector input:checked:enabled").closest('tr'), function (span) {
                self.records.push(parseInt($(span).attr('line-number')))
            })
            if (self.ids.length) {
                this.sidebar.$el.show()
            }
            else {
                this.sidebar.$el.hide()
                self.$el.find("button").hide()
            }
            
            if (self.state == 'draft') {
                self.sidebar.$el.find("a:contains('Delete')").show()
                self.sidebar.$el.find("a:contains('Xóa')").show()
                if (self.ids.length){
                    self.$el.find("button.oe_monthly_button_send").show()
                    self.$el.find("button.oe_monthly_button_reject").hide()
                    self.$el.find("button.oe_monthly_button_approve").hide()
                }
            }
            else if (self.state == 'reject') {
                self.sidebar.$el.find("a:contains('Delete')").show()
                self.sidebar.$el.find("a:contains('Xóa')").show()
                if (self.ids.length){
                    self.$el.find("button.oe_monthly_button_send").show()
                    self.$el.find("button.oe_monthly_button_reject").hide()
                    self.$el.find("button.oe_monthly_button_approve").hide()
                }
            }
            else if (self.state == 'sent') {
            	this.sidebar.$el.hide()
                self.sidebar.$el.find("a:contains('Delete')").hide()
                self.sidebar.$el.find("a:contains('Xóa')").hide()
                if (self.ids.length){
                    self.$el.find("button.oe_monthly_button_send").hide()
                    self.$el.find("button.oe_monthly_button_reject").show()
                    self.$el.find("button.oe_monthly_button_approve").show()
                }
            }
            else if (self.state == 'approve') {
            	this.sidebar.$el.hide()
                self.sidebar.$el.find("a:contains('Delete')").hide()
                self.sidebar.$el.find("a:contains('Xóa')").hide()
                if (self.ids.length){
                    self.$el.find("button.oe_monthly_button_send").hide()
                    self.$el.find("button.oe_monthly_button_reject").show()
                    self.$el.find("button.oe_monthly_button_approve").hide()
                }
            }
        },
        assign_fields_attr: function () {
            /*
             * cool code
             * */
            var self = this
            this.display_fields = []
            this.color_map = {}
            this.color_field = {}
            this.search_fields = []
            this.from_to_field = {}
            this.from_date = ''
            this.to_date = ''
            this.field_state = ''
            _.each(this.fields_list, function (field_name) {
                var child_attrs = _.filter(self.fields_view.arch.children, function (item) {
                    return item.attrs.name == field_name
                })[0]
                var n_domain = child_attrs.attrs.domain || [];
                n_domain = instance.web.pyeval.eval('domain', n_domain || [], {});

                var search = child_attrs.attrs.search != undefined ? true : false
                var string = child_attrs.attrs.string != undefined ? child_attrs.attrs.string : false
                var mark = child_attrs.attrs.mark != undefined ? true : false
                var display = child_attrs.attrs.display != undefined ? true : false
                var from_to = child_attrs.attrs.from_to != undefined ? true : false
                var color = child_attrs.attrs.color != undefined ? true : false
                var code = child_attrs.attrs.code != undefined ? true : false
                var state = child_attrs.attrs.state != undefined ? true : false
                var field = self.fields[field_name];
                field['domain'] = n_domain || field['domain']
                field['name'] = field_name
                if (search) {
                    self.search_fields.push(field)
                }
                if (color) {
                    self.color_field = field
                }
                if (mark) {
                    self.mark_field = field
                }
                if (display) {
                    self.display_fields.push(field)
                }
                if (from_to) {
                    self.from_to_field = field
                }
                if (code) {
                    self.field_code = field
                }
                if (string) {
                    field['string'] = string
                }
                if (state) {
                    self.field_state = field
                }
            })
        },
        reload: function () {
        	this.$el.find("button").hide()
            if (this.last_domain !== undefined)
                return this.do_search(this.last_domain, this.last_context, this.last_group_by);
        },
        initial_pager: function () {
            var self = this
            if (!this.$pager) {
                this.$pager = $(QWeb.render("ListView.pager", {'widget': self}));
                if (this.options.$buttons) {
                    this.$pager.appendTo(this.options.$pager);
                } else {
                    this.$el.find('.oe_list_pager').replaceWith(this.$pager);
                }

                this.$pager
                    .on('click', 'a[data-pager-action]', function () {
                        var $this = $(this);
                        var max_page = Math.floor(self.total / self.limit());
                        switch ($this.data('pager-action')) {
                            case 'first':
                                self.page = 0;
                                break;
                            case 'last':
                                self.page = max_page - 1;
                                break;
                            case 'next':
                                self.page += 1;
                                break;
                            case 'previous':
                                self.page -= 1;
                                break;
                        }
                        var mod_size = self.total % self._limit
                        if (mod_size == 0) {
                            if (self.page < 0) {
                                self.page = max_page - 1;
                            } else if (self.page >= max_page) {
                                self.page = 0;
                            }
                        }
                        else {
                            if (self.page < 0) {
                                self.page = max_page;
                            } else if (self.page > max_page) {
                                self.page = 0;
                            }
                        }

                        self.do_search(self.last_domain, self.last_context, self.last_group_by, self.page);
                    }).find('.oe_list_pager_state')
                    .click(function (e) {
                        e.stopPropagation();
                        var $this = $(this);

                        var $select = $('<select>')
                            .appendTo($this.empty())
                            .click(function (e) {
                                e.stopPropagation();
                            })
                            .append('<option value="40">40</option>' +
                                '<option value="80">80</option>' +
                                '<option value="200">200</option>' +
                                '<option value="500">500</option>' +
                                '<option value="1000">1000</option>' +
                                '<option value="2000">2000</option>' +
                                '<option value="3000">3000</option>' +
                                '<option value="NaN">' + _t("Unlimited") + '</option>')
                            .change(function () {
                                var val = parseInt($select.val(), 10);
                                self._limit = (isNaN(val) ? null : val);
                                self.page = 0;
                                self.do_search(self.last_domain, self.last_context, self.last_group_by, self.page);
                            }).blur(function () {
                                $(this).trigger('change');
                            })
                            .val(self._limit || 'NaN');
                    });


            }
        },

        /**
         * re-renders the content of the list view
         *
         * @returns {$.Deferred} promise to content reloading
         */
        init_sidebar: function () {
            var self = this
            if (!this.sidebar && this.options.$sidebar) {
                this.sidebar = new instance.web.Sidebar(this);
                this.sidebar.appendTo(this.options.$sidebar);
                this.sidebar.add_items('other',
                    _.compact([self.is_action_enabled('delete') && { label: _t('Delete'), callback: this.do_delete_selected },
                     //   { label: _t('Send'), callback: this.do_sent },
//                        { label: _t('Approve'), callback: this.do_approve },
//                        { label: _t('Reject'), callback: this.do_reject },
                    ]));
                
                this.sidebar.add_toolbar(this.fields_view.toolbar);
                this.sidebar.$el.hide();

//                TODO: make add attachment works
                self.sidebar.$el.find("button:contains('Attachment(s)')").closest('div').remove()
                self.sidebar.$el.find("li.oe_share").remove()
            }
        },
        load_hrs_calendar: function (fv) {
        	var self = this;
            this.fields_view = fv;
            this.is_display_sat = fv.arch.attrs.is_display_sat === 'false' ? false : true
            this.is_display_sun = fv.arch.attrs.is_display_sun === 'false' ? false : true
            this.field_date = fv.arch.attrs.field_date || 'date'
            this.reference = fv.arch.attrs.reference
            this.reference_field = fv.arch.attrs.reference_field
            this.fields = fv.fields;
            this.fields_list = _(this.fields_view.arch.children).map(function (field) {
                return field.attrs.name
            })
            this.assign_fields_attr()
            // Pager
            this.initial_pager();
            // Sidebar
            this.init_sidebar();
            this.$el.find('div.toolbar').empty().append(QWeb.render('MonthlyView.toolbar', {filter_state: this.field_state}))
            _.each(self.dataset.domain, function (item) {
    			if (item[0] == 'month') {
        			self.$el.find('#filter_month').val(item[2])
                } else if (item[0] == 'year') {
            		self.$el.find('#filter_year').val(item[2])
                } 
    		});
            this.$el.find("button").hide()
            
            this.reload_freeHeader();
        },
        do_sent: function (e){
        	this.do_set_state('sent')
        },
        do_reject: function (e){
        	this.do_set_state('reject')
        },
        do_approve: function (e){
        	this.do_set_state('approve')
        },
        
        go_to_leave_request_employee: function(e){
        	//Open List of Leave Request of Employee in dateRange
            var employee_code = e.currentTarget.innerHTML;
            dateRange = []
            for (i=0; this.dateRange.length > i; i++) 
            {
            	dateRange.push(this.dateRange[i].full_name);
            }
            
            self_this = this;
            this.dataset.call('get_leave_request_in_dateRange', [employee_code, dateRange]).done(function (list_leave_request) {
            	
            	self_this.dataset.call('get_form_tree_list_of_leave', []).done(function (res) {
            		
            		self_this.do_action({
                    	type: 'ir.actions.act_window',
                        name: 'List of Leave',
                        res_model: 'hr.holidays',
                        views: [[res && res[0], 'list'], [res && res[1], 'form']],
                        target: 'current',
                        context: {'get_all': 1, 'rule_for_tree_form': 1, 'move': 0, 'create': 0, 'edit': 1,'validate_read_holiday': 0},
                        domain: [["id", "in", list_leave_request]],
                    });
            	});
				
            })
            
        },
        do_set_state: function (state) {
            if (this.ids === undefined) {
                return;
            }
            if (!(this.ids.length && confirm(_t("Do you really want to " + (state == 'sent' ? 'send' : state) + " these records?")))) {
                return;
            }
            var self = this
            return $.when(this.dataset.call('set_state', [self.ids, state])).done(function () {
                self.reload()
            })
        },
        filter_state: function (e) {
            e.stopPropagation();
            var state = this.$el.find('input[name=filter_state]:checked').val();
            this.$el.find("button").hide()
            if (state) {
            	//remove old domain
            	var index_holiday = false
                for (var i = this.last_domain.length - 1; i >= 0; i--) {
	                if (this.last_domain[i][0] === 'state' || 
	                		this.last_domain[i][0] === 'holiday_line_id_state' && state !== 'draft') {
	                    this.last_domain.splice(i, 1);
	                }
                }
                this.last_domain.push(['state', '=', state])
                if (state !== 'draft' && state !== 'reject') {
                    this.$el.find('span[name="filter_leave"]').hide()
                }
                else {
                    this.$el.find('span[name="filter_leave"]').show()
                    var val = this.$el.find('#filter_leave').val()
                    var holiday_line_state = 'holiday_line_id_state';
                    for (var i = this.last_domain.length - 1; i >= 0; i--) {
                        if (this.last_domain[i][0] === holiday_line_state) {
                            this.last_domain.splice(i, 1);
                        }
                    }
                    if (val == 'waiting_approve') {
                        this.last_domain.push([holiday_line_state, '=', 'waiting_approve'])
                    }
                    else if (val == 'approved') {
                        this.last_domain.push([holiday_line_state, '=', 'approved'])
                    }
                }
            }
            this.filter_domain()
        },
        filter_domain: function (e) {
            var month = this.$el.find('#filter_month').val();
            this.current_year = this.$el.find('#filter_year').val();
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
            this.do_search(this.last_domain, this.last_context, this.last_group_by)
        },

        view_loading: function (fv) {
            return this.load_hrs_calendar(fv);
        },
        limit: function () {
            if (this._limit === undefined) {
                this._limit = (this.options.limit
                    || this.defaults.limit
                    || (this.getParent().action || {}).limit
                    || 80);
            }
            return this._limit;
        },
        configure_pager: function () {
            var total = this.total;
            var limit = this.limit() || total;
            if (total === 0)
                this.$pager.hide();
            else
                this.$pager.css("display", "");
            this.$pager.toggleClass('oe_list_pager_single_page', (total <= limit));
            var spager = '-';
            if (total) {
                var range_start = this.page * limit + 1;
                var range_stop = range_start - 1 + limit;
                if (range_stop > total) {
                    range_stop = total;
                }
                spager = _.str.sprintf(_t("%d-%d of %d"), range_start, range_stop, total);
            }

            this.$pager.find('.oe_list_pager_state').text(spager);
        },
        generate_date_range: function (year, month) {
            var def = $.Deferred();
            var self = this

            var domain = [
                ['year', '=', year],
                ['month', '=', month]
            ];
            if (!_.isEmpty(this.timesheet_ids)) {
                domain.push(['timesheet_id', 'in', this.timesheet_ids])
            }
            var model_obj = new instance.web.DataSetSearch(this, this.from_to_field.relation, {}, domain);
            model_obj.read_slice(['from_date', 'to_date'], {}).done(function (res) {
                if (res.length > 0) {

                    var list_from_date = []
                    var list_to_date = []
                    _.each(res, function (range) {
                        list_from_date.push(range['from_date'])
                        list_to_date.push(range['to_date'])
                    })
                    var from_date = list_from_date.sort()[list_from_date.length - 1]
                    var to_date = list_to_date.sort()[list_to_date.length - 1]
                    if (from_date && to_date) {
                        var start = moment(from_date);
                        var end = moment(to_date);
                        if (start.isBefore(end)) {
                            start = start.clone();
                            self.dateRange = [];
                            while (!start.isSame(end)) {
                                var date_item = new DateModel({day: start.date(), month: start.month(), year: start.year()})
                                self.dateRange.push(date_item);
                                start.add(1, 'days');
                            }
                            self.dateRange.push(new DateModel({day: end.date(), month: end.month(), year: end.year()}));
                        }
                    }
                }
                def.resolve();

            })
            return def.promise();
        },
        
        reload_freeHeader : function() {
			var self = this;

			// NG: ADD new code to make the Header freeze
			if (this.options.action !== null
					&& ! self.$el.find('div[id^="hdScroll"]').length
					&& this.options.action.context['freeze_header'] !== 0) {

				var body_view = $('.oe_view_manager_body').last().outerHeight();
				var search_view = $('.oe_searchview_drawer_container') .is(':visible') ? $( '.oe_searchview_drawer_container') .outerHeight() : 0;
				var toolbar = self.$el.find('.toolbar').is(':visible') ? self.$el.find( '.toolbar').outerHeight() : 0;

				var height_tree = body_view - search_view - toolbar - 22;

				self.$el.find(".table-monthly-calendar") .freezeHeaderMonthlyCalendar({'height' : height_tree.toString() + "px" 	});
			}
			// return reloaded.promise();
		},

        render_view: function (self, domain, context, group_by, month, year) {
        	instance.web.blockUI();
            self.$el.find('thead').empty();
        	self.$el.find('thead').each(function(){
        		self.headerview = new HeaderView({display_fields: self.display_fields, dateRange: self.dateRange, el: $(this)});
        		$(this).append(self.headerview.render());
        	});
            	
            self.$el.find('div[id^="hdScroll"]').scrollTop(0);
            
            /*
             * read from db
             *
             * */

            var options = { offset: self.page * self.limit(), limit: self._limit, context: {'monthly': 1},
                domain: domain};
            self.dataset.read_slice(self.fields_list, options).done(function (res) {
                    var display = []
                    _.each(res, function (item) {
                        var data = {}
                        _.each(self.display_fields, function (field) {
                            data[field.name] = item[field.name]
                        })
                        display.push(data)
                    })

                    var display_temp = []
                    /*
                     * group by display_fields
                     * */
                    _.each(_.uniq(_.collect(display, function (x) {
                        return JSON.stringify(x);
                    })), function (item) {
                        item = JSON.parse(item);
                        list_date_test = [];
                        list_remove_date = [];
                        var list_date = _.filter(res, function (num) {
                            var count = 0;
                            if (num['shift_name']){
                            	//Find record same date
                            	duplicate = _.where(list_date_test, {'date': num['date'], 'employee_code': num['employee_code']});
                            	if (duplicate.length > 0){
                            		if (duplicate[0]['name'] == num['name'] && num['name'] == num['shift_name']){
//                                      name   shift
//                                      X      x
//                                      X      x
//                                      ----> x
                            			//dont need to add to list_remove_date because list_date is filter already, add to list_remove_date will be slow to filter again
                            			return false;
                            		}
                            		else if (duplicate[0]['name'] != num['name'] && 
                            				(num['name'] == num['shift_name'] || duplicate[0]['name'] == num['shift_name']) ){
//                                      name   shift
//                                      x       x
//                                      p/2     x
//                                      ------> p/2
                            			if (num['name'] == num['shift_name'])
                            				return false;
                            			else
                            				list_remove_date.push(duplicate[0]);
                            		}
                            	}
                            	else
                            		list_date_test.push(num);
                            }
                        	else
                        		list_date_test.push(num);
                            		
                            _.each(self.display_fields, function (field) {
                                    if (field.type == 'many2one' && item[field.name][0] == num[field.name][0]) {
                                        count++
                                    }
                                    else if (item[field.name] == num[field.name]) {
                                        count++
                                    }
                                })
                            return count == self.display_fields.length
                        });
                        list_date = _.difference(list_date, list_remove_date);
                        item['date_list'] = list_date

                        display_temp.push(item)
                    });
                    
                    //Sort list to be shown
                    //Sort theo employee code và group by theo timesheet_id
                    
                    var group_display_temp = _.groupBy(display_temp, 'timesheet_id');
                    display_temp = [];
                    _.each(group_display_temp, function (temp){
                    	temp.sort(function(a,b){
                    		return a['employee_code'].replace ( /[^\d.]/g, '' ) - b['employee_code'].replace ( /[^\d.]/g, '' );
                    	}
                    );
                    	display_temp = _.union(display_temp, temp);
                    });
                    
                    
                    
                    self.lineview = new LineView({
                    							  display_fields: self.display_fields,
                    							  data: display_temp,
                    							  dateRange: self.dateRange, 
                    							  el: $(self.$el.find('tbody'))
                    							})

                    self.$el.find('tbody').empty().append(self.lineview.render())
                    self.dataset.read_slice(['id'], {context: {'search_count': 1}}).done(function (res) {
                        self.total = res.length
                        self.configure_pager()
                    })
                    //Color for line
                    self.do_reference(month, year);
                    instance.web.unblockUI();
                })
        },
        do_search: function (domain, context, group_by, pager) {
        	var self = this
        	this.total = 0
        	this.page = pager ? pager : 0
            var year = this.$el.find('#filter_year').val() > 0 ? this.$el.find('#filter_year').val() : moment().year()
            var month = this.$el.find('#filter_month').val() > 0 ? this.$el.find('#filter_month').val(): moment().month() + 1
            var state = 'notset'
            var holiday_line_id_state = this.$el.find('#filter_leave').val() > 0 ? this.$el.find('#filter_leave').val(): 'waiting_approve'
    		self.timesheet_ids = []
            if (!this.$el.find('#filter_year').val()) {
            	this.$el.find('#filter_year').val(year)
            }
            if (!this.$el.find('#filter_month').val() || (domain.length === 0 && !self.last_domain)) {
            	month = moment().month() + 1
            	this.$el.find('#filter_month').val(month)
            }
            _.each(domain, function (item) {
            	if (item[0] == 'state') {
                    state = item[2]
                }else if (item[0] == 'timesheet_id') {
                	if (jQuery.type(item[2]) === 'array'){
                		self.timesheet_ids = item[2]
                	} else {
                		self.timesheet_ids.push(item[2])
                	}
                    
                }
            })
            /*
             * get total record for pager
             * stupid code goes here
             * WHY use to 2 read_slice
             * */

            /*
             * Happy coding!
             *
             * */
            this.dateRange = []
            $.when(this.generate_date_range(year, month)
            ).done(function () {
            	if (state === 'notset') {
            		if (self.last_domain) {
            			_.each(self.last_domain, function (item) {
                            if (item[0] == 'state') {
                                state = item[2]
                                return false
                            }
                        })
                        self.build_domain(self, state, year, month, domain, group_by, context)
            		} else {
            			$.when(self.dataset.call('get_default_state_base_on_uid', [month, year])).done(function (res) {
                			self.build_domain(self, res, year, month, domain, group_by, context)
                		})
            		}
            	} else {
            		self.build_domain(self, state, year, month, domain, group_by, context)
            	}
            	self.sidebar.$el.hide()
            });
        },
        
        build_domain: function (self, state, year, month, domain, group_by, context) {
        	domain.push(['state', '=', state])
            domain.push(['year', '=', year])
            domain.push(['month', '=', month])
            if (state == 'draft' || state == 'reject') {
                domain.push(['holiday_line_id_state', '=', self.$el.find('#filter_leave').val()])
                self.$el.find('span[name="filter_leave"]').show()
            }
            else {
                self.$el.find('span[name="filter_leave"]').hide()
            }
        	//init variable
    		//assign to know current domain, context, group by
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.state = state;
        	$("input[name=filter_state][value=" + state + "]").prop('checked', true);
            self.render_view(self, domain, context, group_by, month, year);
        },
        
        do_reference: function (month, year) {
            var self = this
            if (self.reference) {
                var model_obj = new instance.web.DataSetSearch(self, self.reference, {}, [
                    ['year', '=', year],
                    ['month', '=', month]
                ])
                model_obj.read_slice(['date', 'color_name'], {}).done(function (res) {
                    _.each(res, function (item) {
                        var cell = self.$el.find('td#' + item.date).find('div')
                        $(cell).css({'background-color': item.color_name})
                    })
                })
            }
            self.$el.find('span.leave_color').closest("td").addClass('Leave');
            
//            _.each(self.$el.find('div.editable').not(':has(span)'), function (item) {
//                $(item).closest("td").not(':has(.Sun)').addClass('grey-cell')
//            });
            
            //Loop for each row (employee)
            _.each(self.$el.find('tr[line-number]'), function(item){
            	var employee_code = $(item).find('a')[0].innerHTML;
            	list_none_data_of_line = $(item).find('div.editable').not(':has(span)');
            	var list_td_date_none_not_sun = [];
            	var list_date_none_data = [];
            	
            	//Get list date is not Sun and dont have any data from monthly
            	_.each($(list_none_data_of_line).closest("td").not('.Sun'),function(item){
            		list_td_date_none_not_sun.push(item);
            		list_date_none_data.push(item.id);
            	});
            	
            	//Call python function to knonw which date should be grey
            	$.when(self.dataset.call('get_list_grey_date', [employee_code, month, year, list_date_none_data])).done(function (list_grey_date) {
        			list_grey_td_date = $(list_td_date_none_not_sun).filter(function(index){
	        				return list_grey_date.indexOf( list_td_date_none_not_sun[index].id) > -1; 
	        			});
        			$(list_grey_td_date).addClass('grey-cell');
        			
//        			list_white_td_date = $(list_td_date_none_not_sun).filter(function(index){
//        				return list_grey_date.indexOf( list_td_date_none_not_sun[index].id) == -1; 
//        			});
//        			$(list_white_td_date).find('div').append("<span></span>");
        		})
            	
            	
            });
        },
        /*
         * Don't know when it call :D
         * */
        do_show: function () {
            this._super();
            if (this.$buttons) {
                this.$buttons.show();
            }
            if (this.$pager) {
                this.$pager.show();
            }
        },
        do_hide: function () {
            if (this.sidebar) {
                this.sidebar.$el.hide();
            }
            if (this.$buttons) {
                this.$buttons.hide();
            }
            if (this.$pager) {
                this.$pager.hide();
            }
            this._super();
        },

        destroy: function () {
            this._super.apply(this, arguments);
        }
    })
}
