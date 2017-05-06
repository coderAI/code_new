openerp_vhr_base_view_list = function (instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.web.ListView.include({
        limit: function () {
            //tuannh3: them option limit record of page cho tree
            if (this.ViewManager !== undefined
                && this.ViewManager.options !== undefined
                && this.ViewManager.options.limit !== undefined) {
                this._limit = this.ViewManager.options.limit;
            } else if (this._limit === undefined) {
                this._limit = (this.options.limit
                    || this.defaults.limit
                    || (this.getParent().action || {}).limit
                    || 80);
            }
            return this._limit;
        },

        init: function () {
            this._super.apply(this, arguments);
            if (this.ViewManager !== undefined
                && this.ViewManager.action !== undefined
                && this.ViewManager.action.context !== undefined
                && this.ViewManager.action.context.pop_up_select === true) {
                this.options.pop_up_select = true;
            }
        },

        load_list: function () {
            this._super.apply(this, arguments);
            var self = this;
            if (this.options.pop_up_select) {
                //tuannh3: resize tree
                $('table.oe_list_content > tfoot').on('mousedown', function (e) {
                    self.resizing(e);
                })
            }
        },

        //tuannh3: resize list
        resizing: function (e) {
            e.preventDefault()
            var start = this.$el.find('.oe_list_content')
            var pressed = true;
            var startY = e.pageY;
            var startHeight = start.height();
            $(start).addClass("resizing");

            $(document).mousemove(function (e) {
                if (pressed) {
                    $(start).height(startHeight + (e.pageY - startY));
                }
            });

            $(document).mouseup(function () {
                if (pressed) {
                    $(start).removeClass("resizing");
                    pressed = false;
                }
            });


        },
        
        setup_events: function () {
            var self = this;
            _.each(this.editor.form.fields, function(field, field_name) {
                var set_invisible = function() {
                    field.set({'force_invisible': field.get('effective_readonly')});
                };
                //NG: Fix error not update list row when change value of field selection
                if (field.template == 'FieldSelection')
                	{
	                	field.on("change select", self, function () {
	                    	this.save_edition();
	                    });
                	}
                
                field.on("change:effective_readonly", self, set_invisible);
                set_invisible();
                field.on('change:effective_invisible', self, function () {
                    if (field.get('effective_invisible')) { return; }
                    var item = _(self.fields_for_resize).find(function (item) {
                        return item.field === field;
                    });
                    if (item) {
                        setTimeout(function() {
                            self.resize_field(item.field, item.cell);
                        }, 0);
                    }
                     
                });
            });

            this.editor.$el.on('keyup keypress keydown', function (e) {
                if (!self.editor.is_editing()) { return true; }
                var key = _($.ui.keyCode).chain()
                    .map(function (v, k) { return {name: k, code: v}; })
                    .find(function (o) { return o.code === e.which; })
                    .value();
                if (!key) { return true; }
                var method = e.type + '_' + key.name;
                if (!(method in self)) { return true; }
                return self[method](e);
            });
        },
        
        save_edition: function () {
            var self = this;
            return self.saving_mutex.exec(function() {
                if (!self.editor.is_editing()) {
                    return $.when();
                }
                return self.with_event('save', {
                    editor: self.editor,
                    form: self.editor.form,
                    cancel: false
                }, function () {
                    return self.editor.save().then(function (attrs) {
                        var created = false;
                        var record = self.records.get(attrs.id);
                        if (!record) {
                            // new record
                            created = true;
                            record = self.records.find(function (r) {
                                return !r.get('id');
                            })
                            /*NG:Check record before set attribute.
                             * Error and error around its, tried to call save_edition when onchange field selection, but still error.
                             * So the best way is check record first before set attribute.
                             * Future coders should check it when have time .
                            */
                            if (record)
                              record = record.set('id', attrs.id);
                            else
                            	return false;
                        }
                        // onwrite callback could be altering & reloading the
                        // record which has *just* been saved, so first perform all
                        // onwrites then do a final reload of the record
                        return self.handle_onwrite(record)
                            .then(function () {
                                return self.reload_record(record); })
                            .then(function () {
                                return { created: created, record: record }; });
                    });
                });
            });
        },
        
        // NX: re-declare reload_content function
        // This function use synchronized decorator and I do not know how to inherit :(
        // Please let me know if there is a way to inherit it. Thanks
        /*
           Check the conditions when reload the tree view:
        	- Action or not: Tree view or Form view
        	- Element with the ID like "hdScroll" exists or not?
        	- Context "freeze_header" true or false
        */
        reload_content: synchronized(function () {
            var self = this;
            self.$el.find('.oe_list_record_selector').prop('checked', false);
            this.records.reset();
            var reloaded = $.Deferred();
            this.$el.find('.oe_list_content').append(
                this.groups.render(function () {
                    if (self.dataset.index == null) {
                        if (self.records.length) {
                            self.dataset.index = 0;
                        }
                    } else if (self.dataset.index >= self.records.length) {
                        self.dataset.index = 0;
                    }

                    self.compute_aggregates();
                    reloaded.resolve();
                }));
            this.do_push_state({
                page: this.page,
                limit: this._limit
            });
            
            // ADD new code to make the Header freeze
            if (this.options.action !== null &&
            		!$('div[id^="hdScroll"]').length &&
            		this.options.action.context['freeze_header'] !== 0) {
                
                var body_view = 0; //$('.oe_view_manager_body').last().outerHeight();
                _.each($('.oe_view_manager_body'), function(manager_body) {

                	body_view = (body_view < $(manager_body).outerHeight() ? $(manager_body).outerHeight() : body_view);
                })
                
                var search_view = 0; 
                if ($('.oe_searchview_drawer_container').is(':visible')) {
                	
                	_.each($('.oe_searchview_drawer_container'), function(searchview_drawer) {

                		search_view = (search_view < $(searchview_drawer).outerHeight() ? $(searchview_drawer).outerHeight() : search_view);
                    })
                }
                
                var quick_add = $('.oe_quickadd.ui-toolbar').is(':visible') ? $('.oe_quickadd.ui-toolbar').outerHeight() : 0;
                
                var height_tree = body_view - search_view - quick_add - 8;
                
                $(".oe_list_content.tree").freezeHeader({ 'height': height_tree.toString() + "px" });
            }
            return reloaded.promise();
        }),
    });

    instance.web.ListView.List.include({
        init: function () {
            this._super.apply(this, arguments);
            var self = this;
            this.$current = $('<tbody>')
                .delegate('input[readonly=readonly]', 'click', function (e) {
                    /*
                     Against all logic and sense, as of right now @readonly
                     apparently does nothing on checkbox and radio inputs, so
                     the trick of using @readonly to have, well, readonly
                     checkboxes (which still let clicks go through) does not
                     work out of the box. We *still* need to preventDefault()
                     on the event, otherwise the checkbox's state *will* toggle
                     on click
                     */
                    e.preventDefault();
                })
                .delegate('th.oe_view_cv', 'click', function (e) {
                    e.stopPropagation();
                    var $row = $(e.target).closest('tr');
                    var model_obj = new instance.web.Model('hr.applicant');
                    model_obj.call('read', [
                        [$($row).data('id')],
                        ['description']
                    ]).done(function (record) {
                        var value = (record[0].description || '')
                        value = value.replace(/\n\n/g, '<br/>').replace(/\n/g, '<br/>').replace(/\r\n/g, '<br/>').replace(/\n\r/g, '<br/>');
                        var dialog = new instance.web.Dialog(this, {
                            size: 'large',
                            title: 'View CV',
                        }, QWeb.render("Popup.ViewCV", value)).open();
                        dialog.$el.find('.oe_cv_context_search_highlight').html(value);
                        dialog.$el.find('.oe_cv_context_search_highlight').removeHighlight();
                        var adv_values = self.view.$el.parents().find('.text-label');
                        var values = self.view.$el.parents().find('.oe_facet_value');
                        values = $.merge(values,adv_values);
                        values.each(function (result) {
                            var searchTerm = values[result].outerText;
                            if (searchTerm === undefined) {
                                searchTerm = values[result].textContent || '';
                                searchTerm = searchTerm.trim()
                            }
                            dialog.$el.find('.oe_cv_context_search_highlight').highlight(searchTerm);
                        });
                    });
                })
                .delegate('th.oe_list_record_selector', 'click', function (e) {
                    e.stopPropagation();
                    var selection = self.get_selection();
                    var checked = $(e.currentTarget).find('input').prop('checked');
                    $(self).trigger(
                        'selected', [selection.ids, selection.records, !checked]);
                })
                .delegate('td.oe_list_record_delete button', 'click', function (e) {
                    e.stopPropagation();
                    var $row = $(e.target).closest('tr');
                    $(self).trigger('deleted', [
                        [self.row_id($row)]
                    ]);
                })
                .delegate('td.oe_list_field_cell button', 'click', function (e) {
                    e.stopPropagation();
                    var $target = $(e.currentTarget),
                        field = $target.closest('td').data('field'),
                        $row = $target.closest('tr'),
                        record_id = self.row_id($row);

                    if ($target.attr('disabled')) {
                        return;
                    }
                    $target.attr('disabled', 'disabled');

                    // note: $.data converts data to number if it's composed only
                    // of digits, nice when storing actual numbers, not nice when
                    // storing strings composed only of digits. Force the action
                    // name to be a string
                    $(self).trigger('action', [field.toString(), record_id, function (id) {
                        $target.removeAttr('disabled');
                        return self.reload_record(self.records.get(id));
                    }]);
                })
                .delegate('a', 'click', function (e) {
                    e.stopPropagation();
                })
                .delegate('tr', 'click', function (e) {
                    var row_id = self.row_id(e.currentTarget);
                    if (row_id) {
                        e.stopPropagation();
                        if (!self.dataset.select_id(row_id)) {
                            throw new Error(_t("Could not find id in dataset"));
                        }
                        self.row_clicked(e);
                    }
                });
        },

        pad_table_to: function (count) {
            if (this.records.length >= count ||
                _(this.columns).any(function (column) {
                    return column.meta;
                })) {
                return;
            }
            var cells = [];
            if (this.options.selectable) {
                cells.push('<th class="oe_list_record_selector"></td>');
            }
            //tuannh3: New button view CV
            if (this.options.pop_up_select) {
                cells.push('<td>');
            }
            _(this.columns).each(function (column) {
                if (column.invisible === '1') {
                    return;
                }
                cells.push('<td title="' + column.string + '">&nbsp;</td>');
            });
            if (this.options.deletable) {
                cells.push('<td class="oe_list_record_delete"><button type="button" style="visibility: hidden"> </button></td>');
            }
            cells.unshift('<tr>');
            cells.push('</tr>');

            var row = cells.join('');
            this.$current
                .children('tr:not([data-id])').remove().end()
                .append(new Array(count - this.records.length + 1).join(row));
        },

        render_cell: function (record, column) {
        	var self = this;
            var value;
            if (column.type === 'reference') {
                value = record.get(column.id);
                var ref_match;
                // Ensure that value is in a reference "shape", otherwise we're
                // going to loop on performing name_get after we've resolved (and
                // set) a human-readable version. m2o does not have this issue
                // because the non-human-readable is just a number, where the
                // human-readable version is a pair
                if (value && (ref_match = /^([\w\.]+),(\d+)$/.exec(value))) {
                    // reference values are in the shape "$model,$id" (as a
                    // string), we need to split and name_get this pair in order
                    // to get a correctly displayable value in the field
                    var model = ref_match[1],
                        id = parseInt(ref_match[2], 10);
                    new instance.web.DataSet(this.view, model).name_get([id]).done(function (names) {
                        if (!names.length) {
                            return;
                        }
                        record.set(column.id + '__display', names[0][1]);
                    });
                }
            } else if (column.type === 'many2one') {
                value = record.get(column.id);
                // m2o values are usually name_get formatted, [Number, String]
                // pairs, but in some cases only the id is provided. In these
                // cases, we need to perform a name_get call to fetch the actual
                // displayable value
                if (typeof value === 'number' || value instanceof Number) {
                    // fetch the name, set it on the record (in the right field)
                    // and let the various registered events handle refreshing the
                    // row
                    new instance.web.DataSet(this.view, column.relation)
                        .name_get([value]).done(function (names) {
                            if (!names.length) {
                                return;
                            }
                            record.set(column.id, names[0]);
                        });
                }
            } else if (column.type === 'many2many') {
                value = record.get(column.id);
                // non-resolved (string) m2m values are arrays
                if (value instanceof Array && !_.isEmpty(value)
                    && !record.get(column.id + '__display')) {
                    var ids;
                    // they come in two shapes:
                    if (value[0] instanceof Array) {
                        var command = value[0];
                        // 1. an array of m2m commands (usually (6, false, ids))
                        if (command[0] !== 6) {
                            throw new Error(_.str.sprintf(_t("Unknown m2m command %s"), command[0]));
                        }
                        ids = command[2];
                    } else {
                        // 2. an array of ids
                        ids = value;
                    }
                    new instance.web.Model(column.relation)
                        .call('name_get', [ids]).done(function (names) {
                            // FIXME: nth horrible hack in this poor listview
                            record.set(column.id + '__display',
                                _(names).pluck(1).join(', '));
                            record.set(column.id, ids);
                        });
                    // temp empty value
                    record.set(column.id, false);
                }
            }

            var res = column.format(record.toForm().data, {
                model: this.dataset.model,
                id: record.get('id')
            });

            //  Remove Separator in Year
            if (column.type === 'integer') {
                if (column.remove_thousand_seps && res && typeof res === 'string') {
                    res = res.replace(',', '');
                }
            }
            
            if (self.style_for(record, column)) {
            	return '<span style="'+ self.style_for(record, column) +'">' + res + '</span>';
            }
            
            return res;

        },
        
        style_for: function (record, column) {
            var style= '';
            
            var attributes = record && record.attributes || {};
            var context = _.extend({}, attributes, {
                uid: this.session.uid,
                current_date: new Date().toString('yyyy-MM-dd')
                // TODO: time, datetime, relativedelta
            });
            
            context = $.each(context, function(index,value){
            	if (value && value.constructor == Array){
            		context[index]= value[0];
            	} 
            	else if (value && value.constructor == String){
            		context[index] = value.trim();
            	}
            
            });
            var i;
            var pair;
            var expression;
            if (this.fonts) {
                for(i=0, len=this.fonts.length; i<len; ++i) {
                    pair = this.fonts[i];
                    var font = pair[0];
                    expression = pair[1];
                    if (py.evaluate(expression, context).toJSON()) {
                        switch(font) {
                        case 'bold':
                            style += 'font-weight: bold;';
                            break;
                        case 'italic':
                            style += 'font-style: italic;';
                            break;
                        case 'underline':
                            style += 'text-decoration: underline;';
                            break;
                        }
                    }
                }
            }

            if (!column.colors) { return style; }
            for(i=0, len=column.colors.length; i<len; ++i) {
                pair = column.colors[i];
                var color = pair[0];
                expression = pair[1];
                var is_have_data = true;
                
                expression.expressions.forEach(function(item,index){
                	if (item.id == "(name)" && context[item.value]==undefined){
                		is_have_data=false; 
                	} 
                });
                
                if (is_have_data && py.evaluate(expression, context).toJSON()) {
                	if (column && column.type == 'boolean'){
                		return style += 'outline-style:solid;outline-width:2px;outline-color:' + color + ';';
                	}
                    return style += 'color: ' + color + ';';
                }
                // TODO: handle evaluation errors
            }
            return style;
        },

    });

    instance.web.ListView.Groups.include({
        render_groups: function (datagroups) {
            var self = this;
            var placeholder = this.make_fragment();
            _(datagroups).each(function (group) {
                if (self.children[group.value]) {
                    self.records.proxy(group.value).reset();
                    delete self.children[group.value];
                }
                var child = self.children[group.value] = new (self.view.options.GroupsType)(self.view, {
                    records: self.records.proxy(group.value),
                    options: self.options,
                    columns: self.columns
                });
                self.bind_child_events(child);
                child.datagroup = group;

                var $row = child.$row = $('<tr class="oe_group_header">');
                if (group.openable && group.length) {
                    $row.click(function (e) {
                        if (!$row.data('open')) {
                            $row.data('open', true)
                                .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-e')
                                .addClass('ui-icon-triangle-1-s');
                            child.open(self.point_insertion(e.currentTarget));
                        } else {
                            $row.removeData('open')
                                .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-s')
                                .addClass('ui-icon-triangle-1-e');
                            child.close();
                            // force recompute the selection as closing group reset properties
                            var selection = self.get_selection();
                            $(self).trigger('selected', [selection.ids, this.records]);
                        }
                    });
                }
                placeholder.appendChild($row[0]);

                var $group_column = $('<th class="oe_list_group_name">').appendTo($row);
                // Don't fill this if group_by_no_leaf but no group_by
                if (group.grouped_on) {
                    var row_data = {};
                    row_data[group.grouped_on] = group;
                    var group_label = _t("Undefined");
                    var group_column = _(self.columns).detect(function (column) {
                        return column.id === group.grouped_on;
                    });
                    if (group_column) {
                        try {
                            group_label = group_column.format(row_data, {
                                value_if_empty: _t("Undefined"),
                                process_modifiers: false
                            });
                        } catch (e) {
                            group_label = _.str.escapeHTML(row_data[group_column.id].value);
                        }
                    } else {
                        group_label = group.value;
                        if (group_label instanceof Array) {
                            group_label = group_label[1];
                        }
                        if (group_label === false) {
                            group_label = _t('Undefined');
                        }
                        group_label = _.str.escapeHTML(group_label);
                    }

                    // group_label is html-clean (through format or explicit
                    // escaping if format failed), can inject straight into HTML
                    //tuannh3: them priority
                    if (group.model.name === 'hr.job') {
                        var model_obj = new instance.web.Model(group.model.name);
                        var list_priority = ['priority_1', 'priority_2', 'priority_3', 'no_of_hired_recruitment'];
                        var priority_1 = 0;
                        var priority_2 = 0;
                        var priority_3 = 0;
                        var hired = 0;
                        model_obj.call('search', [group.domain]).done(function (records) {
                            model_obj.call('read', [records, list_priority]).done(function (obj_records) {
                                var temp_priority_1 = 0;
                                var temp_priority_2 = 0;
                                var temp_priority_3 = 0;

                                _(obj_records).each(function (record) {
                                    hired = record['no_of_hired_recruitment'];
                                    if (hired > record['priority_1']) {
                                        temp_priority_1 = 0;
                                        var pri_excess_1 = hired - record['priority_1']
                                        if (pri_excess_1 > record['priority_2']) {
                                            temp_priority_2 = 0;
                                            temp_priority_3 = record['priority_3'] - (pri_excess_1 - record['priority_2']);
                                        } else {
                                            temp_priority_2 = record['priority_2'] - pri_excess_1;
                                            temp_priority_3 = record['priority_3'];
                                        }
                                    } else {
                                        temp_priority_1 = record['priority_1'] - hired;
                                        temp_priority_2 = record['priority_2'];
                                        temp_priority_3 = record['priority_3'];
                                    }
                                    priority_1 = temp_priority_1 + priority_1;
                                    priority_2 = temp_priority_2 + priority_2;
                                    priority_3 = temp_priority_3 + priority_3;
                                });

                                var innerHTML = $group_column.html();
                                $group_column.html(_.str.sprintf(_t("%s %s (%d / %d / %d)"), innerHTML,
                                															group_label,
                                															(priority_1 < 0) ? 0 : priority_1,
                                															(priority_2 < 0) ? 0 : priority_2,
                                															(priority_3 < 0) ? 0 : priority_3));
                            });
                        });
                    } else {
                        $group_column.html(_.str.sprintf(_t("%s (%d)"),
                            group_label, group.length));
                    }

                    if (group.length && group.openable) {
                        // Make openable if not terminal group & group_by_no_leaf
                        $group_column.prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
                    } else {
                        // Kinda-ugly hack: jquery-ui has no "empty" icon, so set
                        // wonky background position to ensure nothing is displayed
                        // there but the rest of the behavior is ui-icon's
                        $group_column.prepend('<span class="ui-icon" style="float: left; background-position: 150px 150px">');
                    }
                }
                self.indent($group_column, group.level);

                if (self.options.selectable) {
                    $row.append('<td>');
                }
                //tuannh3: New button view CV
                if (self.options.pop_up_select) {
                    $row.append('<td>');
                }
                _(self.columns).chain()
                    .filter(function (column) {
                        return column.invisible !== '1';
                    })
                    .each(function (column) {
                        if (column.meta) {
                            // do not do anything
                        } else if (column.id in group.aggregates) {
                            var r = {};
                            r[column.id] = {value: group.aggregates[column.id]};
                            $('<td class="oe_number">')
                                .html(column.format(r, {process_modifiers: false}))
                                .appendTo($row);
                        } else {
                            $row.append('<td>');
                        }
                    });
                if (self.options.deletable) {
                    $row.append('<td class="oe_list_group_pagination">');
                }
            });
            return placeholder;
        },
        
        setup_resequence_rows: function (list, dataset) {
        	$('div[id^="hdScroll"]').trigger("scroll");
        	this._super.apply(this, arguments);
        },
        
        close: function () {
        	this._super.apply(this, arguments);
            $('div[id^="hdScroll"]').trigger("scroll");
        },
    });
    
    instance.web.list.Char = instance.web.list.Column.extend({
        replacement: '*',
        /**
         * If password field, only display replacement characters (if value is
         * non-empty)
         */
        _format: function (row_data, options) {
            var value = row_data[this.id].value;
            if (value && this.password === 'True') {
                return value.replace(/[\s\S]/g, _.escape(this.replacement));
            }
            if (value && this.options) {
                var new_options = JSON.parse(this.options);
                if((new_options.file_download !== undefined || new_options.file_download !== false)
                    && (new_options.field_data !== undefined || new_options.field_data !== false) && (this.widget == undefined)){
                    
                    var download_url = instance.session.url('/web/binary/saveas', {model: options.model, field: new_options.field_data, id: options.id});
                    download_url += '&filename_field=' + this.id;

                    return _.template('<a href="<%-href%>"><%-text%></a>', {
                        text: value,
                        href: download_url
                    });
                }
            }
            return this._super(row_data, options);
        }
    });

    instance.web.list.Binary.include({
        /**
         * Return a link to the binary data as a file
         *
         * @private
         */
        _format: function (row_data, options) {
            var text = _t("Download");
            var value = row_data[this.id].value;
            var download_url;
            //NG: Add option name_by_file to download with file name
            //This options is for the case save file in tree view, can not download correct file name
            //Example at vhr_master_data/vhr_family/deduct. Employee/Relationship/Family Deduct
            if (value && value.substr(0, 10).indexOf(' ') == -1 && !this.name_by_file) {
                download_url = "data:application/octet-stream;base64," + value;
            } else {
                if (value) {
                    download_url = instance.session.url('/web/binary/saveas', {model: options.model, field: this.id, id: options.id});
                    if (this.filename) {
                        download_url += '&filename_field=' + this.filename;
                    }
                }
                else {
                    return _.template('<a><%-text%></a>', {
                        text: "",
                    });
                }

            }
            if (this.filename && row_data[this.filename]) {
                text = _.str.sprintf(_t("Download \"%s\""), instance.web.format_value(
                    row_data[this.filename].value, {type: 'char'}));
            }
            return _.template('<a href="<%-href%>"><%-text%></a> (<%-size%>)', {
                text: text,
                href: download_url,
                size: instance.web.binary_to_binsize(value),
            });
        },
    });


//    instance.web.Sidebar.include({
//
//        on_item_action_clicked: function (item) {
//            var self = this;
//            self.getParent().sidebar_eval_context().done(function (sidebar_eval_context) {
//                var ids = self.getParent().get_selected_ids();
//                //NG: ADD TO SIDE BAR, CONTEXT FROM MENU
//                old_context = self.getParent().dataset.context;
////                sidebar_eval_context = $.extend(old_context, sidebar_eval_context);
//                sidebar_eval_context = new instance.web.CompoundContext(sidebar_eval_context || {}, old_context)
//                
//                var domain;
//                if (self.getParent().get_active_domain) {
//                    domain = self.getParent().get_active_domain();
//                }
//                else {
//                    domain = $.Deferred().resolve(undefined);
//                }
//                if (ids.length === 0) {
//                    new instance.web.Dialog(this, { title: _t("Warning"), size: 'medium', }, $("<div />").text(_t("You must choose at least one record."))).open();
//                    return false;
//                }
//                var active_ids_context = {
//                    active_id: ids[0],
//                    active_ids: ids,
//                    active_model: self.getParent().dataset.model,
//                };
//
//                $.when(domain).done(function (domain) {
//                    if (domain !== undefined) {
//                        active_ids_context.active_domain = domain;
//                    }
//                    var c = instance.web.pyeval.eval('context',
//                        new instance.web.CompoundContext(
//                            sidebar_eval_context, active_ids_context));
//
//                    self.rpc("/web/action/load", {
//                        action_id: item.action.id,
//                        context: c
//                    }).done(function (result) {
//                        result.context = new instance.web.CompoundContext(
//                                result.context || {}, active_ids_context)
//                            .set_eval_context(c);
//                        result.flags = result.flags || {};
//                        result.flags.new_window = true;
//                        self.do_action(result, {
//                            on_close: function () {
//                                // reload view
//                                self.getParent().reload();
//                            },
//                        });
//                    });
//                });
//            });
//        },
//    });


    instance.web.View.include({

        /**
         * Return whether the user can perform the action ('create', 'edit', 'delete') in this view.
         * An action is disabled by setting the corresponding attribute in the view's main element,
         * like: <form string="" create="false" edit="false" delete="false">
         */
        is_action_enabled: function (action) {
            var attrs = this.fields_view.arch.attrs;

            //Check in context too, if context['rule_for_tree_form'] == True
            var context = (this.dataset && this.dataset.context) || {}
            if (action in context && context['rule_for_tree_form'])
                return JSON.parse(context[action]);

            return (action in attrs) ? JSON.parse(attrs[action]) : true;
        },


        load_view: function (context) {
            var self = this;
            var view_loaded_def;
            if (this.embedded_view) {
                view_loaded_def = $.Deferred();
                $.async_when().done(function () {
                    view_loaded_def.resolve(self.embedded_view);
                });
            } else {
                if (!this.view_type)
                    console.warn("view_type is not defined", this);
                view_loaded_def = instance.web.fields_view_get({
                    "model": this.dataset._model,
                    "view_id": this.view_id,
                    "view_type": this.view_type,
                    "toolbar": !!this.options.$sidebar,
                    "context": this.dataset.get_context(),
                });
            }
            return this.alive(view_loaded_def).then(function (r) {
                self.fields_view = r;

                //NG: Remove Execute/Approve/Return/Reject in menu More if have set it in context
                r = self.remove_toolbar_item(r, 'publish', 'Publish');
                r = self.remove_toolbar_item(r, 'approve', 'Approve');
                r = self.remove_toolbar_item(r, 'return', 'Return');
                r = self.remove_toolbar_item(r, 'reject', 'Reject');
                r = self.remove_toolbar_item(r, 'duplicate', 'Duplicate');
                r = self.remove_toolbar_item(r, 'move', 'Move');

                // add css classes that reflect the (absence of) access rights
                self.$el.addClass('oe_view')
                    .toggleClass('oe_cannot_create', !self.is_action_enabled('create'))
                    .toggleClass('oe_cannot_edit', !self.is_action_enabled('edit'))
                    .toggleClass('oe_cannot_delete', !self.is_action_enabled('delete'));
                return $.when(self.view_loading(r)).then(function () {
                    self.trigger('view_loaded', r);
                });
            });
        },

        context_enabled: function (action) {
            //Check in context, if context['rule_for_tree_form'] == True
            var context = (this.dataset && this.dataset.context) || {}
            if (action in context && context['rule_for_tree_form'])
                return JSON.parse(context[action]);

            return true;
        },

        //NG: Remove item in menu More if set it in context
        remove_toolbar_item: function (data, option, name) {
            if (!this.context_enabled(option) && data && data.toolbar && data.toolbar.action) {
                var no_dup = _.reject(data.toolbar.action, function (item) {
                    return item.name === _t(name);
                });
                data.toolbar.action = no_dup;
            }
            return data;
        },

    });
    
    
    instance.web.list.Column.include({
    	init: function(id, tag, attrs) {
            this._super(id, tag, attrs)
            ;
            // Save colors attribute into this.colors
            if (attrs.colors) {
	            this.colors = _(attrs.colors.split(';')).chain()
	            .compact()
	            .map(function(color_pair) {
	                var pair = color_pair.split(':'),
	                    color = pair[0],
	                    expr = pair[1];
	                return [color, py.parse(py.tokenize(expr)), expr];
	            }).value();
            }
    	},
    });
};

function synchronized(fn) {
    var fn_mutex = new $.Mutex();
    return function () {
        var obj = this;
        var args = _.toArray(arguments);
        return fn_mutex.exec(function () {
            if (obj.isDestroyed()) { return $.when(); }
            return fn.apply(obj, args)
        });
    };
}
