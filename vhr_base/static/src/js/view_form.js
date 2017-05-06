openerp_vhr_base_view_form = function (instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    jQuery.fn.highlight = function (pat) {
        function innerHighlight(node, pat) {
            var skip = 0;
            if (node.nodeType == 3) {
                var pos = node.data.toUpperCase().indexOf(pat);
                if (pos >= 0) {
                    var spannode = document.createElement('span');
                    spannode.className = 'highlight';
                    var middlebit = node.splitText(pos);
                    var endbit = middlebit.splitText(pat.length);
                    var middleclone = middlebit.cloneNode(true);
                    spannode.appendChild(middleclone);
                    middlebit.parentNode.replaceChild(spannode, middlebit);
                    skip = 1;
                }
            }
            else if (node.nodeType == 1 && node.childNodes && !/(script|style)/i.test(node.tagName)) {
                for (var i = 0; i < node.childNodes.length; ++i) {
                    i += innerHighlight(node.childNodes[i], pat);
                }
            }
            return skip;
        }

        return this.each(function () {
            innerHighlight(this, pat.toUpperCase());
        });
    };

    jQuery.fn.removeHighlight = function () {
        function newNormalize(node) {
            for (var i = 0, children = node.childNodes, nodeCount = children.length; i < nodeCount; i++) {
                var child = children[i];
                if (child.nodeType == 1) {
                    newNormalize(child);
                    continue;
                }
                if (child.nodeType != 3) {
                    continue;
                }
                var next = child.nextSibling;
                if (next == null || next.nodeType != 3) {
                    continue;
                }
                var combined_text = child.nodeValue + next.nodeValue;
                new_node = node.ownerDocument.createTextNode(combined_text);
                node.insertBefore(new_node, child);
                node.removeChild(child);
                node.removeChild(next);
                i--;
                nodeCount--;
            }
        }

        return this.find("span.highlight").each(function () {
            var thisParent = this.parentNode;
            thisParent.replaceChild(this.firstChild, this);
            newNormalize(thisParent);
        }).end();
    };

    instance.web.FormView.include({
        _process_save: function (save_obj) {
            var self = this;
            var prepend_on_create = save_obj.prepend_on_create;
            try {
                var form_invalid = false,
                    values = {},
                    first_invalid_field = null,
                    readonly_values = {},
                    save_no_required = false;
                if (self.options !== undefined && self.options.save_no_required === true) {
                    save_no_required = true;
                }
                for (var f in self.fields) {
                    if (!self.fields.hasOwnProperty(f)) {
                        continue;
                    }
                    f = self.fields[f];
                    if (f.get('required') && f.options['save_no_required'] === true && save_no_required === true) {
                        f.set({required: false});
                    }
                    if (!f.is_valid()) {
                        form_invalid = true;
                        if (!first_invalid_field) {
                            first_invalid_field = f;
                        }
                    } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                        // Special case 'id' field, do not save this field
                        // on 'create' : save all non readonly fields
                        // on 'edit' : save non readonly modified fields
                        //tuannh3 check type de trim khoang trang dau` duoi cua value
                        var check_type = function (value) {
                            if (typeof value === 'string') {
                                return true;
                            }
                            return false;
                        };
                        var value_field = f.get_value();
                        if (check_type(f.get_value())) {
                            value_field = f.get_value().trim();
                        }
                        ///////////////////////////////////////
                        if (!f.get("readonly") || f.options['save_readonly']) {
                            values[f.name] = value_field;
                        } else {
                            readonly_values[f.name] = value_field;
                        }
                        if (f.options['save_no_required'] && save_no_required === true) {
                            f.set({required: true});
                        }
                    }
                }
                if (form_invalid) {
                    self.set({'display_invalid_fields': true});
                    first_invalid_field.focus();
                    self.on_invalid();
                    return $.Deferred().reject();
                } else {
                    self.set({'display_invalid_fields': false});
                    var save_deferral;
                    if (!self.datarecord.id) {
                        // Creation save
                        save_deferral = self.dataset.create(values, {readonly_fields: readonly_values}).then(function (r) {
                            return self.record_created(r, prepend_on_create);
                        }, null);
                    } else if (_.isEmpty(values)) {
                        // Not dirty, noop save
                        save_deferral = $.Deferred().resolve({}).promise();
                    } else {
                        // Write save
                        save_deferral = self.dataset.write(self.datarecord.id, values, {readonly_fields: readonly_values}).then(function (r) {
                            return self.record_saved(r);
                        }, null);
                    }
                    return save_deferral;
                }
            } catch (e) {
                console.error(e);
                return $.Deferred().reject();
            }
        },

        is_syntax_valid: function () {
            if (!this.get("effective_readonly") && this.$("input").size() > 0) {
                //tuannh3 khong cho phep chi nhap khoang trang voi field required
                if ((this.$('input').val().trim()).length <= 0 && this.get('required')) {
                    return false
                }
                try {
                    this.parse_value(this.$('input').val(), '');
                    return true;
                } catch (e) {
                    return false;
                }
            }
            return true;
        },
        
        load_form: function (data) {
            var self = this;
            if (!data) {
                throw new Error(_t("No data provided."));
            }
            if (this.arch) {
                throw "Form view does not support multiple calls to load_form";
            }
            this.fields_order = [];
            this.fields_view = data;

            this.rendering_engine.set_fields_registry(this.fields_registry);
            this.rendering_engine.set_tags_registry(this.tags_registry);
            this.rendering_engine.set_widgets_registry(this.widgets_registry);
            this.rendering_engine.set_fields_view(data);
            var $dest = this.$el.hasClass("oe_form_container") ? this.$el : this.$el.find('.oe_form_container');
            this.rendering_engine.render_to($dest);

            this.$el.on('mousedown.formBlur', function () {
                self.__clicked_inside = true;
            });

            this.$buttons = $(QWeb.render("FormView.buttons", {'widget': self}));

            if (this.options.$buttons) {
                //NG: add option hide_form_view_button to hide button Save/ Create/ Edit/ Discard in form view
                context = this.options.action && this.options.action.context
                hide_form_view_button = context && context['hide_form_view_button']
                if (!hide_form_view_button) {
                    this.$buttons.appendTo(this.options.$buttons);
                }

            } else {
                this.$el.find('.oe_form_buttons').replaceWith(this.$buttons);
            }

            this.$buttons.on('click', '.oe_form_button_create',
                this.guard_active(this.on_button_create));
            this.$buttons.on('click', '.oe_form_button_edit',
                this.guard_active(this.on_button_edit));
            this.$buttons.on('click', '.oe_form_button_save',
                this.guard_active(this.on_button_save));
            this.$buttons.on('click', '.oe_form_button_cancel',
                this.guard_active(this.on_button_cancel));
            if (this.options.footer_to_buttons) {
                this.$el.find('footer').appendTo(this.$buttons);
            }

            this.$sidebar = this.options.$sidebar || this.$el.find('.oe_form_sidebar');
            if (!this.sidebar && this.options.$sidebar) {
                this.sidebar = new instance.web.Sidebar(this);
                self.remove_toolbar_section('attachment','Attachment(s)');
                this.sidebar.appendTo(this.$sidebar);
                if (this.fields_view.toolbar) {
                    this.sidebar.add_toolbar(this.fields_view.toolbar);
                }
                this.sidebar.add_items('other', _.compact([
                        self.is_action_enabled('delete') && { label: _t('Delete'), callback: self.on_button_delete },
                    //NG: Delete default duplicate button from <More> section if set duplicate=False in form view
                        self.is_action_enabled('create') && self.is_action_enabled('duplicate') && { label: _t('Duplicate'), callback: self.on_button_duplicate },

                ]));
            }

            this.has_been_loaded.resolve();

            // Add bounce effect on button 'Edit' when click on readonly page view.
            this.$el.find(".oe_form_group_row,.oe_form_field,label,h1,.oe_title,.oe_notebook_page, .oe_list_content").on('click', function (e) {
                if (self.get("actual_mode") == "view") {
                    var $button = self.options.$buttons.find(".oe_form_button_edit");
                    $button.openerpBounce();
                    e.stopPropagation();
                    instance.web.bus.trigger('click', e);
                }
            });
            //bounce effect on red button when click on statusbar.
            this.$el.find(".oe_form_field_status:not(.oe_form_status_clickable)").on('click', function (e) {
                if ((self.get("actual_mode") == "view")) {
                    var $button = self.$el.find(".oe_highlight:not(.oe_form_invisible)").css({'float': 'left', 'clear': 'none'});
                    $button.openerpBounce();
                    e.stopPropagation();
                }
            });
            
            this.trigger('form_view_loaded', data);
            return $.when();
        },
      //NG: Remove item in Sidebar if set it in context
        remove_toolbar_section: function(option, name){
        	context = this.options.action && this.options.action.context;
        	
        	if (context && option in context && !context[option]){
        		sidebar_sections = this.sidebar && this.sidebar.sections;
            	if (sidebar_sections){
            		remove_index = -1;
            		for (var i = 0; i < sidebar_sections.length; i+=1){
            			if (sidebar_sections[i]['label'] == name){
            				remove_index = i;
            				break;
            			}
            		}
            		if (remove_index >= 0){
            			sidebar_sections.splice(remove_index, 1);
            		}
            	}
        	}
        	
        },
        load_record: function(record) {
            var self = this, set_values = [];
            if (!record) {
                this.set({ 'title' : undefined });
                this.do_warn(_t("Form"), _t("The record could not be found in the database."), true);
                return $.Deferred().reject();
            }
            this.datarecord = record;
            this._actualize_mode();
            this.set({ 'title' : record.id ? record.display_name : _t("New") });
            
           
            _(this.fields).each(function (field, f) {
                field._dirty_flag = false;
                field._inhibit_on_change_flag = true;
                var result = field.set_value(self.datarecord[f] || false);
                //Call function to render color of field value
                field.render_color_field();
                field._inhibit_on_change_flag = false;
                set_values.push(result);
            });
           
            return $.when.apply(null, set_values).then(function() {
                if (!record.id) {
                    // New record: Second pass in order to trigger the onchanges
                    // respecting the fields order defined in the view
                    _.each(self.fields_order, function(field_name) {
                        if (record[field_name] !== undefined) {
                            var field = self.fields[field_name];
                            field._dirty_flag = true;
                            self.do_onchange(field);
                        }
                    });
                }
                self.on_form_changed();
                self.rendering_engine.init_fields();
                self.is_initialized.resolve();
                self.do_update_pager(record.id === null || record.id === undefined);
                if (self.sidebar) {
                   self.sidebar.do_attachement_update(self.dataset, self.datarecord.id);
                }
                if (record.id) {
                    self.do_push_state({id:record.id});
                } else {
                    self.do_push_state({});
                }
                self.$el.add(self.$buttons).removeClass('oe_form_dirty');
                self.autofocus();
            });
        },

    });
    

    
    instance.web.form.FormRenderingEngine.include({
        process_notebook: function ($notebook) {
            var self = this;
            var pages = [];
            $notebook.find('> page').each(function () {
                var $page = $(this);
                var page_attrs = $page.getAttributes();
                page_attrs.id = _.uniqueId('notebook_page_');
                var $new_page = self.render_element('FormRenderingNotebookPage', page_attrs);
                $page.contents().appendTo($new_page);
                $page.before($new_page).remove();
                var ic = self.handle_common_properties($new_page, $page).invisibility_changer;
                page_attrs.__page = $new_page;
                page_attrs.__ic = ic;
                pages.push(page_attrs);

                $new_page.children().each(function () {
                    self.process($(this));
                });
            });
            var $new_notebook = this.render_element('FormRenderingNotebook', { pages: pages });
            $notebook.contents().appendTo($new_notebook);
            $notebook.before($new_notebook).remove();
            self.process($($new_notebook.children()[0]));
            //tabs and invisibility handling
            $new_notebook.tabs();
            //tuannh3: Fix focus notebook if first page invisible
            var check_index_page = false
            _.each(pages, function (page, i) {
                if (!page.__ic)
                    if (check_index_page === false) {
                        $new_notebook.tabs('select', i);
                        check_index_page = true;
                    }
                ;
                return;
                page.__ic.on("change:effective_invisible", null, function () {
                    if (!page.__ic.get('effective_invisible') && page.autofocus) {
                        //tuannh3: Fix focus notebook if have onchange invisible
                        var hrs_visible = _.find(_.range(pages.length), function (i2) {
                            return (!pages[i2].__ic) || (!pages[i2].__ic.get("effective_invisible"));
                        });
                        $new_notebook.tabs('select', hrs_visible);
                        return;
                    }
                    var current = $new_notebook.tabs("option", "selected");
                    if (!pages[current].__ic || !pages[current].__ic.get("effective_invisible"))
                        return;
                    var first_visible = _.find(_.range(pages.length), function (i2) {
                        return (!pages[i2].__ic) || (!pages[i2].__ic.get("effective_invisible"));
                    });
                    if (first_visible !== undefined) {
                        $new_notebook.tabs('select', first_visible);
                    }
                });
            });

            this.handle_common_properties($new_notebook, $notebook);
            return $new_notebook;
        },
    });
//instance.web.form.CompletionFieldMixin.include({
    instance.web.form.FieldMany2One.include({
    	events: _.extend({}, instance.web.form.FieldMany2One.prototype.events, {
            'click input': 'on_click_input',
        }),
        on_click_input: function(){
        	this.$el.find('input').select();
        },
        get_search_result: function (search_val) {
            var self = this;

            var dataset = new instance.web.DataSet(this, this.field.relation, self.build_context());
            var blacklist = this.get_search_blacklist();
            this.last_query = search_val;

            return this.orderer.add(dataset.name_search(
                search_val, new instance.web.CompoundDomain(self.build_domain(), [
                    ["id", "not in", blacklist]
                ]),
                'ilike', this.limit + 1, self.build_context())).then(function (data) {
                self.last_search = data;
                // possible selections for the m2o
                var values = _.map(data, function (x) {
                    x[1] = x[1].split("\n")[0];
                    return {
                        label: _.str.escapeHTML(x[1]),
                        value: x[1],
                        name: x[1],
                        id: x[0],
                    };
                });

                // search more... if more results that max
                //tuannh3: get limit many2one in options
                var vhr_limit = self.limit
                if (self.options && self.options['limit'] !== undefined) {
                    vhr_limit = self.options['limit']
                }
                if (values.length > vhr_limit) {
                    values = values.slice(0, vhr_limit);
                    values.push({
                        label: _t("Search More..."),
                        action: function () {
                            dataset.name_search(search_val, self.build_domain(), 'ilike', 160).done(function (data) {
                                //tuannh3 truyen them sefl.options de lay no_create
                                self._search_create_popup("search", data, self.options);
                            });
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                // quick create
                var raw_result = _(data.result).map(function (x) {
                    return x[1];
                });
                //tuannh3 Fix luon luon dong quick create, khi nao can thi bo sung them 'quick_create': True
                if (search_val.length > 0 && !_.include(raw_result, search_val) &&
                    (self.options && self.options.quick_create)) {
                    //! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                    values.push({
                        label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                            $('<span />').text(search_val).html()),
                        action: function () {
                            self._quick_create(search_val);
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                // create...
                if (!(self.options && self.options.no_create)) {
                    values.push({
                        label: _t("Create and Edit..."),
                        action: function () {
                            self._search_create_popup("form", undefined, self._create_context(search_val));
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                else if (values.length == 0)
                    values.push({
                        label: _t("No results to show..."),
                        action: function () {
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });

                return values;
            });
        },
        
        // all search/create popup handling
        _search_create_popup: function (view, ids, context) {
            var self = this;
            var pop = new instance.web.form.SelectCreatePopup(this);
            //tuannh3 xu ly options duoc truyen vao, hide button create tren form search more cua many2one
            var options = {
                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
                initial_ids: ids ? _.map(ids, function (x) {
                    return x[0];
                }) : undefined,
                initial_view: view,
                disable_multiple_selection: true
            };
            if (context && context.no_create) {
                _.extend(options, {no_create: context.no_create})
            }
            ;
            pop.select_element(
                self.field.relation,
                options,
                self.build_domain(),
                new instance.web.CompoundContext(self.build_context(), context || {})
            );
            pop.on("elements_selected", self, function (element_ids) {
                self.add_id(element_ids[0]);
                self.focus();
            });
        },

        //Add no_quick_create into if condition to prevent open show_error_displayer()
        render_editable: function () {
            var self = this;
            this.$input = this.$el.find("input");

            this.init_error_displayer();

            self.$input.on('focus', function () {
                self.hide_error_displayer();
            });

            this.$drop_down = this.$el.find(".oe_m2o_drop_down_button");
            this.$follow_button = $(".oe_m2o_cm_button", this.$el);

            this.$follow_button.click(function (ev) {
                ev.preventDefault();
                if (!self.get('value')) {
                    self.focus();
                    return;
                }
                var pop = new instance.web.form.FormOpenPopup(self);
                var context = self.build_context().eval();
                var model_obj = new instance.web.Model(self.field.relation);
                model_obj.call('get_formview_id', [self.get("value"), context]).then(function (view_id) {
                    pop.show_element(
                        self.field.relation,
                        self.get("value"),
                        self.build_context(),
                        {
                            title: _t("Open: ") + self.string,
                            view_id: view_id
                        }
                    );
                    pop.on('write_completed', self, function () {
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                    });
                });
            });

            // some behavior for input
            var input_changed = function () {
                if (self.current_display !== self.$input.val()) {
                    self.current_display = self.$input.val();
                    if (self.$input.val() === "") {
                        self.internal_set_value(false);
                        self.floating = false;
                    } else {
                        self.floating = true;
                    }
                }
            };
            this.$input.keydown(input_changed);
            this.$input.change(input_changed);
            this.$drop_down.click(function () {
                self.$input.focus();
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete("close");
                } else {
                    if (self.get("value") && !self.floating) {
                        self.$input.autocomplete("search", "");
                    } else {
                        self.$input.autocomplete("search");
                    }
                }
            });

            // Autocomplete close on dialog content scroll
            var close_autocomplete = _.debounce(function () {
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete("close");
                }
            }, 50);
            this.$input.closest(".modal .modal-content").on('scroll', this, close_autocomplete);

            self.ed_def = $.Deferred();
            self.uned_def = $.Deferred();
            var ed_delay = 200;
            var ed_duration = 15000;
            var anyoneLoosesFocus = function (e) {
                var used = false;
                if (self.floating) {
                    if (self.last_search.length > 0) {
                        if (self.last_search[0][0] != self.get("value")) {
                            self.display_value = {};
                            self.display_value_backup = {};
                            self.display_value["" + self.last_search[0][0]] = self.last_search[0][1];
                            self.reinit_value(self.last_search[0][0]);
                        } else {
                            used = true;
                            self.render_value();
                        }
                    } else {
                        used = true;
                        self.reinit_value(false);
                    }
                    self.floating = false;
                }
                //tuannh3 Fix luon luon dong quick create, khi nao can thi bo sung them 'quick_create': True
                if (used && self.get("value") === false && !self.no_ed && self.options.quick_create === true) {
                    self.ed_def.reject();
                    self.uned_def.reject();
                    self.ed_def = $.Deferred();
                    self.ed_def.done(function () {
                        self.show_error_displayer();
                        ignore_blur = false;
                        self.trigger('focused');
                    });
                    ignore_blur = true;
                    setTimeout(function () {
                        self.ed_def.resolve();
                        self.uned_def.reject();
                        self.uned_def = $.Deferred();
                        self.uned_def.done(function () {
                            self.hide_error_displayer();
                        });
                        setTimeout(function () {
                            self.uned_def.resolve();
                        }, ed_duration);
                    }, ed_delay);
                } else {
                    self.no_ed = false;
                    self.ed_def.reject();
                }
            };
            var ignore_blur = false;
            this.$input.on({
                focusout: anyoneLoosesFocus,
                focus: function () {
                    self.trigger('focused');
                },
                autocompleteopen: function () {
                    ignore_blur = true;
                },
                autocompleteclose: function () {
                    ignore_blur = false;
                },
                blur: function () {
                    // autocomplete open
                    if (ignore_blur) {
                        return;
                    }
                    if (_(self.getChildren()).any(function (child) {
                        return child instanceof instance.web.form.AbstractFormPopup;
                    })) {
                        return;
                    }
                    self.trigger('blurred');
                }
            });

            var isSelecting = false;
            // autocomplete
            this.$input.autocomplete({
                source: function (req, resp) {
                    self.get_search_result(req.term).done(function (result) {
                        resp(result);
                    });
                },
                select: function (event, ui) {
                    isSelecting = true;
                    var item = ui.item;
                    if (item.id) {
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.display_value["" + item.id] = item.name;
                        self.reinit_value(item.id);
                    } else if (item.action) {
                        item.action();
                        // Cancel widget blurring, to avoid form blur event
                        self.trigger('focused');
                        return false;
                    }
                },
                focus: function (e, ui) {
                    e.preventDefault();
                },
                html: true,
                // disabled to solve a bug, but may cause others
                //close: anyoneLoosesFocus,
                minLength: 0,
                delay: 250
            });
            // set position for list of suggestions box
            this.$input.autocomplete("option", "position", { my: "left top", at: "left bottom" });
            this.$input.autocomplete("widget").openerpClass();
            // used to correct a bug when selecting an element by pushing 'enter' in an editable list
            this.$input.keyup(function (e) {
                if (e.which === 13) { // ENTER
                    if (isSelecting)
                        e.stopPropagation();
                }
                isSelecting = false;
            });
            this.setupFocus(this.$follow_button);
            
          //NG: Fix autocomplete does not run when paste value into Many2One Field
            this.$input.bind('paste', function(e) {
                setTimeout(function() { 
                	self.$input.autocomplete('search', self.$input.val());},0);
            });
        },
    });

    instance.web.form.FieldOne2Many.include({
        //NG: Add function to check require when set required=True to field one2many
        is_false: function () {
            return this.dataset.ids == false;
        },
    });

    instance.web.form.One2ManyListView.include({
        limit: function () {
            //tuannh3: them limit so record tren 1 page
            if (this.ViewManager !== undefined && this.ViewManager.o2m
                && this.ViewManager.o2m.options !== undefined
                && this.ViewManager.o2m.options.limit !== undefined) {
                this._limit = this.ViewManager.o2m.options.limit;
            } else if (this._limit === undefined) {
                this._limit = (this.options.limit
                    || this.defaults.limit
                    || (this.getParent().action || {}).limit
                    || 80);
            }
            return this._limit;
        },
    });

    instance.web.form.SelectCreatePopup.include({
        do_search: function () {
            //tuannh3: Special Gift for Recruitment
            this.$el.find('.oe_cv_context_search_highlight').text('');
            this._super.apply(this, arguments);
        },
    });
    instance.web.form.SelectCreateListView.include({
        select_record: function (index) {
            //tuannh3: Special Gift for Recruitment
            this.popup.read_record = true;
            this.popup.select_elements([this.dataset.ids[index]]);
            if (this.popup.vhr_search_cv === undefined) {
                this.popup.destroy();
            }
        },
    });

    instance.web.form.WidgetButton.include({
        //Tuannh3: Enable button when close act window
        on_click: function () {
            var self = this;
            this.force_disabled = true;
            this.check_disable();
            this.execute_action();
            if (self.field_manager.options['history_back'] === true) {
                self.do_action('history_back');
            }
            if (self.field_manager.options['one_click_button'] === true) {
                this.force_disabled = true;
                this.check_disable();
            } else {
                this.force_disabled = false;
                this.check_disable();
            }

        },
        //tuannh3: Special Gift for Recruitment
        //TODO: Change pop_up_select come to {domain: '', context: '', function: '', model: '', label: ''}

        vhr_do_add_record: function () {
            var pop = new instance.web.form.SelectCreatePopup(this);
            var id_parent = this.view.datarecord.id
            var context = {};
            _.extend(context, {'form_view_ref': 'vhr_recruitment.view_vhr_applicant_form',
                'tree_view_ref': 'vhr_recruitment.view_vhr_applicant_tree',
                'search_view_ref': 'vhr_recruitment.view_vhr_applicant_search',
                'show_appli': true, 'active_ids': [id_parent], 'active_id': id_parent});
            pop.select_element(
                'hr.applicant',
                {
                    title: _t("Add New CV"),
                    no_create: true,
                    limit: 10
                },
                new instance.web.CompoundDomain([
                    '|', ['state', 'in', ['opening']], ['is_staff_movement', '=', true]
                ]),
                context
            );
            var self = pop;
            var self_this = this
            pop.vhr_search_cv = true;
            pop.on("elements_selected", self, function (element_ids) {
                if (self.read_record) {
                    var model_obj = new instance.web.Model('hr.applicant');
                    model_obj.call('read', [element_ids, ['description'], context]).done(function (record) {
                        var value = (record[0].description || '')
                        value = value.replace(/\n\n/g, '<br/>').replace(/\n/g, '<br/>').replace(/\r\n/g, '<br/>').replace(/\n\r/g, '<br/>');                        
                        
                        var dialog = new instance.web.Dialog(this, {
                            size: 'large',
                            title: 'View CV',
                        }, QWeb.render("Popup.ViewCV", value)).open();
                        dialog.$el.find('.oe_cv_context_search_highlight').html(value);
                        dialog.$el.find('.oe_cv_context_search_highlight').removeHighlight();
                        
                        var values = self.$el.find('.oe_facet_value');
                        values.each(function (result) {
                            var searchTerm = values[result].outerText;
                            if (searchTerm === undefined) {
                                searchTerm = values[result].textContent || '';
                                searchTerm = searchTerm.trim()
                            }
                            dialog.$el.find('.oe_cv_context_search_highlight').highlight(searchTerm);
                        });
                    });
                    self.read_record = false;
                } else {
                    var model_obj = new instance.web.Model(self_this.field_manager.model);
                    model_obj.call('create_interview', [
                        [self_this.field_manager.datarecord.id],
                        element_ids,
                        context
                    ]).done(function () {
                        self_this.field_manager.recursive_reload();
                    });
                }
            });
        },

        on_confirmed: function () {
            var self = this;

            var context = this.build_context();
            //tuannh3: Special Gift for Recruitment
            if (self.view.options.pop_up_select !== undefined && self.view.options.pop_up_select === true) {
                return self.vhr_do_add_record();
            }
            return this.view.do_execute_action(
                _.extend({}, this.node.attrs, {context: context}),
                this.view.dataset, this.view.datarecord.id, function (reason) {
                    if (!_.isObject(reason)) {
                        self.view.recursive_reload();
                    }
                });
        },
        //////////////////////////////////////////////////////////////////////////
        execute_action: function () {
            var self = this;
            var exec_action = function () {
                if (self.node.attrs.confirm) {
                    var def = $.Deferred();
                    var dialog = new instance.web.Dialog(this, {
                        title: _t('Confirm'),
                        buttons: [
                            {text: _t("Ok"), click: function () {
                                var self2 = this;
                                self.on_confirmed().always(function () {
                                    self2.parents('.modal').modal('hide');
                                });
                            }
                            },
                            {text: _t("Cancel"), click: function () {
                                this.parents('.modal').modal('hide');
                            }
                            }

                        ],
                    }, $('<div/>').text(self.node.attrs.confirm)).open();
                    dialog.on("closing", null, function () {
                        def.resolve();
                    });
                    return def.promise();
                } else {
                    return self.on_confirmed();
                }
            };
            if (!this.node.attrs.special) {
                //tuannh3 cho phep save bo qua required
                if (this.node.attrs.save_no_required) {
                    this.view.options['save_no_required'] = true;
                } else {
                    if (this.view.options['save_no_required']) {
                        this.view.options['save_no_required'] = false;
                    }
                }
                ;
                if (this.node.attrs.history_back) {
                    this.view.options['history_back'] = true;
                } else {
                    if (this.view.options['history_back']) {
                        this.view.options['history_back'] = false;
                    }
                }
                ;
                if (this.node.attrs.one_click_button) {
                    this.view.options['one_click_button'] = true;
                } else {
                    if (this.view.options['one_click_button']) {
                        this.view.options['one_click_button'] = false;
                    }
                }
                ;
                if (this.node.attrs.pop_up_select) {
                    this.view.options['pop_up_select'] = true;
                } else {
                    if (this.view.options['pop_up_select']) {
                        this.view.options['pop_up_select'] = false;
                    }
                }
                ;
                return this.view.recursive_save().then(exec_action);
            } else {
                return exec_action();
            }
        },
    });

    instance.web.form.FieldFloat.include({
        //luannk: default float field is none
        set_value: function (value_) {
            if ((value_ === false || value_ === undefined) && (!this.options['default_show_zero'])) {
                // As in GTK client, floats default to 0
                value_ = '';
            }
            this._super.apply(this, [value_]);
        },
        render_value: function () {

            // chanhlt2: Show float field when value is zero.
            var value_if_empty = '';
            if (this.options['show_zero']) {
                value_if_empty = 0;
                var l10n = _t.database.parameters;
                var digits = this.digits;
                digits = typeof digits === "string" ? py.eval(digits) : digits;
                if (digits) {
                    var precision = digits[1];
                    var formatted = _.str.sprintf('%.' + precision + 'f', 0).split('.');
                    formatted[0] = instance.web.insert_thousand_seps(formatted[0]);
                    value_if_empty = formatted.join(l10n.decimal_point);
                }
                else {

                }
            }

            var show_value = this.format_value(this.get('value'), value_if_empty);

            // positive number:
            if (this.options['positive_number'] && this.get('value') && parseInt(this.get('value')) < 0) {
                show_value = this.format_value(Math.abs(this.get('value')), value_if_empty);
            }

            if (this.options['remove_thousand_seps']) {
                show_value = show_value.replace(',', '')
            }

            if (this.options['show_zero_blank']) {
            	if (show_value === false || show_value === undefined || show_value === "") {
            		show_value = '';
            	}else{
            		if(parseInt(show_value)==0)
            			show_value = 0;
            	}
            }
            if (!this.get("effective_readonly")) {
                this.$el.find('input').val(show_value);
            } else {
                if (this.password) {
                    show_value = new Array(show_value.length + 1).join('*');
                }
                this.$(".oe_form_char_content").text(show_value);
            }
        },
        validate_number: function (raise_error) {
            try {
                var data = this.$('input').val()
                if (this.options['integer_number'] && data && data.length) {
                    var pattern = /^[0-9]+$/;
                    var result = pattern.exec(data)
                    if (!result) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: 1)"));
                        return false
                    }
                }
                else if (this.options['validate_date_number'] && data && data.length) {
                    data = parseInt(data)
                    if (data < 1 || data > 31) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(Must be in range[1 - 31])"));
                        return false
                    }
                }
                
                /*NG: validate with widget limit_float_time
                 * Allow to input 1,2,4 number, then function will auto convert to type hh:mm.
                 * 	1 number: ex 1 = 01:00
                 *  2 number: ex 12 = 12:00
                 *  4 number: ex 1221 = 12:21
                 * Allow to input with type hh:mm
                 * Input number must be in range 00:00 - 23:59
                */
                if ( ( (this.widget || this.type || (this.field && this.field.type)).localeCompare('limit_float_time') == 0 ) && data && data.length){
                	var value = data.toString();
            		var float_time_pair = value.split(":");
            		
            		if (float_time_pair.length == 1){
    	        		length_value = value.length;
    	        		//Only allow to input 1,2,4 number
    	        		if ([1,2,4].indexOf(length_value) == -1 || isNaN(value)){
    	        			if (raise_error)
    	        				this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: hh:mm)"));
    	        			return false;
    	        		}
    	        		value = this.set_special_value(false);
            		}//Dont accept aa:bb:cc
            		else if (float_time_pair.length > 2){
            			if (raise_error)
            				this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: hh:mm)"));
            			return false;
            		}
            		
            		else{
            			for (i=0;i<float_time_pair.length; i++){
            				if (isNaN(float_time_pair[i]) || float_time_pair[i].length != 2){
            					if (raise_error)
            						this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: hh:mm)"));
                    			return false;
            				}
            			}
            			value = instance.web.parse_value(value, { type:"float_time" });
            		}
            		if (value < 0 || value >= 24){
            			if (raise_error)
            				this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  value !\n(e.g: 00:00 - 23:59)"));
            			return false;
            		}
                }

            } catch (e) {
                return false;
            }
            return true
        },

    });

    instance.web.form.FieldChar.include({
        //NG: Update events['change input'] = 'store_dom_char_value'
        events: _.extend({}, instance.web.form.FieldChar.prototype.events, {
            'change input': 'store_dom_char_value',
        }),
        store_dom_char_value: function () {
            //Call openerp method when change input
        	
        	//NG: Convert value to value in widget limit_float_time
        	this.set_special_value(true);
            this.store_dom_value()
            //NG: check validate field
            var is_number = this.validate_number(true)

            //Anhnh4: Format Number
            if (is_number){
            	if (this.field.type === 'integer' || this.field.type === 'float' || this.widget == 'number_separator'){
                    this.render_value();
                }
            }
        },
        is_syntax_valid: function () {
            if (!this.get("effective_readonly") && this.$("input").size() > 0) {
                try {
                    this.parse_value(this.$('input').val(), '');

//              //NG: check validate field
                    return this.validate_number(false)

                } catch (e) {
                    return false;
                }
            }
            return true;
        },
        
      //NG: With widget limit_float_time, when input 0930, change to 09:30
        set_special_value: function (set){
        	/*
        	 * Only allow to input 1,2,4 number or type hh:mm
        	 */
        	var value = this.$('input').val();
        	if ( (this.widget || this.type || (this.field && this.field.type)).localeCompare('limit_float_time') == 0 ){
        		value = value.toString();
        		var float_time_pair = value.split(":");
        		length_value = value.length;
        		
        		if (float_time_pair.length == 1 && [1,2,4].indexOf(length_value) > -1){
        			if (length_value == 4 && !isNaN(value) ){
        				value = value.substr(0,2) *1 + value.substr(2,2)/60;
        			}
        			if (set && !isNaN(value))
        				this.set_value(parseFloat(value));
        		}
        	}
        	return value;
        },
        
        //NG: Add function to validate this.$('input').val() must be match with pattern /^[\s0-9\.,;\-+\(\)]+$/
        //Only accept data have 0 1 2 3 4 5 6 7 8 9 , ; - + ()
        validate_number: function (raise_error) {
            try {
                var data = this.$('input').val()
                if (this.options['validate_number'] && data && data.length) {
                    var pattern = /^[\s0-9\.,;\-+\(\)]+$/;
                    var result = pattern.exec(data)
                    if (!result) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: 090-123-456)"));
                        return false
                    }
                }
                //   chanhlt2 check email validate http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
                else if (this.options['validate_email'] && data && data.length) {
                    var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                    var result = re.exec(data)
                    if (!result) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: me@example.com)"));
                        return false
                    }
                }
                else if (this.options['validate_phone'] && data && data.length) {
                    var re = /0\d{9,10}/;
                    var result = re.exec(data)
                    if (!result) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: 01667599546)"));
                        return false
                    }
                }
                //NG: Validate string mm/yyyy
                else if (this.options['validate_mm_yyyy'] && data && data.length) {
                    var re = /^(0?[1-9]|1[012])[\/]\d{4}$/;
                    var result = re.exec(data)
                    if (!result) {
                        if (raise_error)
                            this.do_warn(_t("Error"), _t("Incorrect " + this.field['string'] + "  format !\n(e.g: 12/2014)"));
                        return false
                    }
                }

            } catch (e) {
                return false;
            }
            return true

        }
    });
    
    instance.web.DateTimeWidget.include({
    	change_datetime: function() {
            if (this.is_valid_()) {
            	//Add method to convert 31122014 --> 31/12/2014
            	this.validate_date();
                this.set_value_from_ui_();
                this.trigger("datetime_changed");
            }
        },
        //If length value is 8 and only consist number, try to convert it to correct date format
        //Default correct date format is dd/MM/YYYY
    	//ex: 30122015 --> 30/12/2015
        validate_date: function(){
        	if (this.$input){
        		var value = this.$input.val();
            	re = /^\d{8}$/;
            	if (value.length == 8 && re.exec(value)){
            		new_value = value.substr(0,2) +'/' + value.substr(2,2) + '/' + value.substr(4,4);
            		this.set({'value': new_value});
                    this.$input.val(new_value);
            	}
        	}
        },
    });
    
    instance.web.form.FieldTextHtml.include({
        initialize_content: function () {
            var self = this;
            if (!this.get("effective_readonly")) {
                self._updating_editor = false;
                this.$textarea = this.$el.find('textarea');
                var width = ((this.node.attrs || {}).editor_width || '100%');
                var height = ((this.node.attrs || {}).editor_height || 250);
                //Tuannh3: Fix tools edit document for widget html
                this.$textarea.cleditor({
                    width: width, // width not including margins, borders or padding
                    height: height, // height not including margins, borders or padding
                    controls: // controls to add to the toolbar
                        "bold italic underline strikethrough | font size " +
                        "style | color highlight | bullets numbering | outdent " +
                        "indent | cut copy paste pastetext | alignleft center alignright justify | source",
                    colors: // colors in the color popup
                        "FFF FCC FC9 FF9 FFC 9F9 9FF CFF CCF FCF " +
                        "CCC F66 F96 FF6 FF3 6F9 3FF 6FF 99F F9F " +
                        "BBB F00 F90 FC6 FF0 3F3 6CC 3CF 66C C6C " +
                        "999 C00 F60 FC3 FC0 3C0 0CC 36F 63F C3C " +
                        "666 900 C60 C93 990 090 399 33F 60C 939 " +
                        "333 600 930 963 660 060 366 009 339 636 " +
                        "000 300 630 633 330 030 033 006 309 303",
                    fonts: // font names in the font popup
                        "Arial,Arial Black,Comic Sans MS,Courier New,Narrow,Garamond," +
                        "Georgia,Impact,Sans Serif,Serif,Tahoma,Trebuchet MS,Verdana",
                    sizes: // sizes in the font size popup
                        "1,2,3,4,5,6,7",
                    bodyStyle:  // style to assign to document body contained within the editor
                        "margin:4px; color:#4c4c4c; font-size:13px; font-family:'Lucida Grande',Helvetica,Verdana,Arial,sans-serif; cursor:text"
                });
                this.$cleditor = this.$textarea.cleditor()[0];
                this.$cleditor.change(function () {
                    if (!self._updating_editor) {
                        self.$cleditor.updateTextArea();
                        self.internal_set_value(self.$textarea.val());
                    }
                });
                if (this.field.translate) {
                    var $img = $('<img class="oe_field_translate oe_input_icon" src="/web/static/src/img/icons/terp-translate.png" width="16" height="16" border="0"/>')
                        .click(this.on_translate);
                    this.$cleditor.$toolbar.append($img);
                }
            }
        },
    });
    instance.web.form.FieldBoolean.include({
    	 on_click: function() {
	        var self = this;
	        this.popup =  new instance.web.form.FormOpenPopup(this);
	        if (self.options.show_popup !== undefined && self.options.show_popup) {
	        	self.popup.show_element(
	                    self.field_manager.model,
	                    false,
	                    self.build_context(),
	                    {
	                    	title: self.options.show_popup, 
	                    });
	        }
	    },
    });
    instance.web.DateTimeWidget.include({
        start: function () {
            var self = this;
            this.$input = this.$el.find('input.oe_datepicker_master');
            this.$input_picker = this.$el.find('input.oe_datepicker_container');

            $.datepicker.setDefaults({
                clearText: _t('Clear'),
                clearStatus: _t('Erase the current date'),
                closeText: _t('Done'),
                closeStatus: _t('Close without change'),
                prevText: _t('<Prev'),
                prevStatus: _t('Show the previous month'),
                nextText: _t('Next>'),
                nextStatus: _t('Show the next month'),
                currentText: _t('Today'),
                currentStatus: _t('Show the current month'),
                monthNames: Date.CultureInfo.monthNames,
                monthNamesShort: Date.CultureInfo.abbreviatedMonthNames,
                monthStatus: _t('Show a different month'),
                yearStatus: _t('Show a different year'),
                weekHeader: _t('Wk'),
                weekStatus: _t('Week of the year'),
                dayNames: Date.CultureInfo.dayNames,
                dayNamesShort: Date.CultureInfo.abbreviatedDayNames,
                dayNamesMin: Date.CultureInfo.shortestDayNames,
                dayStatus: _t('Set DD as first week day'),
                dateStatus: _t('Select D, M d'),
                firstDay: Date.CultureInfo.firstDayOfWeek,
                initStatus: _t('Select a date'),
                isRTL: false
            });
            $.timepicker.setDefaults({
                timeOnlyTitle: _t('Choose Time'),
                timeText: _t('Time'),
                hourText: _t('Hour'),
                minuteText: _t('Minute'),
                secondText: _t('Second'),
                currentText: _t('Now'),
                closeText: _t('Done')
            });
            //Tuannh3: Fix limit year -50 and +10
            this.picker({
                onClose: this.on_picker_select,
                onSelect: this.on_picker_select,
                changeMonth: true,
                changeYear: true,
                showWeek: true,
                showButtonPanel: true,
                firstDay: Date.CultureInfo.firstDayOfWeek,
                yearRange: "c-50:c+10"
            });
            // Some clicks in the datepicker dialog are not stopped by the
            // datepicker and "bubble through", unexpectedly triggering the bus's
            // click event. Prevent that.
            this.picker('widget').click(function (e) {
                e.stopPropagation();
            });

            this.$el.find('img.oe_datepicker_trigger').click(function () {
                if (self.get("effective_readonly") || self.picker('widget').is(':visible')) {
                    self.$input.focus();
                    return;
                }
                self.picker('setDate', self.get('value') ? instance.web.auto_str_to_date(self.get('value')) : new Date());
                self.$input_picker.show();
                self.picker('show');
                self.$input_picker.hide();
            });
            this.set_readonly(false);
            this.set({'value': false});
        },
    });
    //Tuannh3: Fix multi select many2manytag
	instance.web.form.FieldMany2ManyTags.prototype._search_create_popup = function(view, ids) {
    	var self = this;
    	//remove value have chosen
    	_.each(ids, function (id, key) {
    		if (jQuery.inArray(id[0], self.get("value")) !== -1){
    			ids = jQuery.grep(ids, function(value) {
    				  		return value != id;
					  });
    		}
    	});
    	
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.select_element(
            self.field.relation,
            {
                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
                initial_ids: ids ? _.map(ids, function(x) {return x[0];}) : undefined,
                initial_view: view,
                disable_multiple_selection: false
            },
            self.build_domain(),
            new instance.web.CompoundContext(self.build_context(), context || {})
        );
        pop.on("elements_selected", self, function(element_ids) {
            self.add_id(element_ids);
            self.focus();
        });
    };
    //Tuannh3: Fix multi select many2manytag
    instance.web.form.FieldMany2ManyTags.include({
        add_id: function(ids) {
        	var self = this;
        	if (jQuery.type(ids) === 'array') {
            	_.each(ids, function (id, field) {
            		self.set({'value': _.uniq(self.get('value').concat([id]))});
            	});
        	} else {
        		self.set({'value': _.uniq(self.get('value').concat([ids]))});
        	}
        },
        
        get_search_result: function(search_val) {
            var self = this;

            var dataset = new instance.web.DataSet(this, this.field.relation, self.build_context());
            var blacklist = this.get_search_blacklist();
            this.last_query = search_val;
            var create_rights = new instance.web.Model(this.field.relation).call(
                    "check_access_rights", ["create", false]);
            var write_rights = new instance.web.Model(this.field.relation).call(
                    "check_access_rights", ["write", false]);

            return this.orderer.add(dataset.name_search(
                    search_val, new instance.web.CompoundDomain(self.build_domain(), [["id", "not in", blacklist]]),
                    'ilike', this.limit + 1, self.build_context())).then(function(data) {
                self.last_search = data;
                var search_val = search_val;
                // possible selections for the m2o
                var values = _.map(data, function(x) {
                    x[1] = x[1].split("\n")[0];
                    return {
                        label: _.str.escapeHTML(x[1]),
                        value: x[1],
                        name: x[1],
                        id: x[0],
                    };
                });

                // search more... if more results that max
                if (values.length > self.limit) {
                    values = values.slice(0, self.limit);
                    values.push({
                        label: _t("Search More..."),
                        action: function() {
                            dataset.name_search(search_val, self.build_domain(), 'ilike', 160).done(function(data) {
                                self._search_create_popup("search", data);
                            });
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                // quick create
                var raw_result = _(data.result).map(function(x) {return x[1];});
                
                $.when(create_rights, write_rights).then(function (can_create, can_write) {
                	
                	self.can_create = can_create;
                	self.can_write = can_write;
                	
                	if (can_create && !can_write && search_val.length > 0 && !_.include(raw_result, search_val) &&
                        ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                        values.push({
                            label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                                $('<span />').text(search_val).html()),
                            action: function() {
                                self._quick_create(search_val);
                            },
                            classname: 'oe_m2o_dropdown_option'
                        });
                    }
                    // create...
                    if (can_create && can_write && !(self.options && self.options.no_create)){
                        values.push({
                            label: _t("Create and Edit..."),
                            action: function() {
                                self._search_create_popup("form", undefined, self._create_context(search_val));
                            },
                            classname: 'oe_m2o_dropdown_option'
                        });
                    }
                    else if (values.length == 0)
                    	values.push({
                    		label: _t("No results to show..."),
                    		action: function() {},
                    		classname: 'oe_m2o_dropdown_option'
                    	});
                });
                return values;
            });
        },
    });
    
    var toString = Object.prototype.toString;

	_.isString = function (obj) {
	  return toString.call(obj) == '[object String]';
	}

    instance.web.form.compute_domain = function(expr, fields) {
        if (! (expr instanceof Array))
            return !! expr;
        var stack = [];
        for (var i = expr.length - 1; i >= 0; i--) {
            var ex = expr[i];
            if (ex.length == 1) {
                var top = stack.pop();
                switch (ex) {
                    case '|':
                        stack.push(stack.pop() || top);
                        continue;
                    case '&':
                        stack.push(stack.pop() && top);
                        continue;
                    case '!':
                        stack.push(!top);
                        continue;
                    default:
                        throw new Error(_.str.sprintf(
                            _t("Unknown operator %s in domain %s"),
                            ex, JSON.stringify(expr)));
                }
            }

            var field = fields[ex[0]];
            if (!field) {
                throw new Error(_.str.sprintf(
                    _t("Unknown field %s in domain %s"),
                    ex[0], JSON.stringify(expr)));
            }
            var field_value = field.get_value ? field.get_value() : field.value;
            var op = ex[1];
            var val = ex[2];

            switch (op.toLowerCase()) {
                case '=':
                case '==':
                    stack.push(_.isEqual(field_value, val));
                    break;
                case '!=':
                case '<>':
                    stack.push(!_.isEqual(field_value, val));
                    break;
                case '<':
                    stack.push(field_value < val);
                    break;
                case '>':
                    stack.push(field_value > val);
                    break;
                case '<=':
                    stack.push(field_value <= val);
                    break;
                case '>=':
                    stack.push(field_value >= val);
                    break;
                case 'in':
                    if (!_.isArray(val)) val = [val];
                    stack.push(_(val).contains(field_value));
                    break;
                case 'not in':
                    if (!_.isArray(val)) val = [val];
                    stack.push(!_(val).contains(field_value));
                    break;
                //NG: Add new attribute for domain in xml: indexOf (like javascript) for string.indexOf(string1)
                case 'indexof':
            		if (_.isString(val) && _.isString(field_value) && field_value.indexOf(val) != -1)
            			{
            			stack.push(true);
            			}
            		else
            			{
            			stack.push(false);
            			}
                    
                    break;
                
                case 'not indexof':
            		if (_.isString(val) && _.isString(field_value) && field_value.indexOf(val) != -1)
            			{
            			stack.push(false);
            			}
            		else
            			{
            			stack.push(true);
            			}
                    
                    break;
                default:
                    console.warn(
                        _t("Unsupported operator %s in domain %s"),
                        op, JSON.stringify(expr));
            }
        }
        return _.all(stack, _.identity);
    };


    //anhnh4: Render Value Integer/Float Fields With Separator (Button Widget StatInfo)
    instance.web.form.StatInfo = instance.web.form.AbstractField.extend({
        is_field_number: true,
        init: function() {
            this._super.apply(this, arguments);
            this.internal_set_value(0);
        },
        set_value: function(value_) {
            if (value_ === false || value_ === undefined) {
                value_ = 0;
            }
            this._super.apply(this, [value_]);
        },
        format_value: function(val, def) {
            return instance.web.format_value(val, this.field, def);
        },
        render_value: function() {
            var value = 0
            if (this.field.type === 'integer' || this.field.type === 'float'){
                value = this.format_value(this.get('value'), '')
            }
            var options = {
                value: value || 0,
            };
            if (! this.node.attrs.nolabel) {
                options.text = this.string
            }
            this.$el.html(QWeb.render("StatInfo", options));
        },

    });
    
    instance.web.form.AbstractField.include({
    	init: function(field_manager, node) {
            this._super(field_manager, node);
            // Save colors attribute into this.colors
            if (this.node.attrs.colors) {
	            this.colors = _(this.node.attrs.colors.split(';')).chain()
	            .compact()
	            .map(function(color_pair) {
	                var pair = color_pair.split(':'),
	                    color = pair[0],
	                    expr = pair[1];
	                return [color, py.parse(py.tokenize(expr)), expr];
	            }).value();
            }
    	},
    	render_color_field: function(){
    		if (this.colors){
        		if (this.$el.attr('id') == 'color_field'){
        			record = this.field_manager && this.field_manager.datarecord;
        			style = this.style_for(record);
        			this.$el.attr('style',style);
        		}
        		else if (this.$el.find('span#color_field').length){
        			record = this.field_manager && this.field_manager.datarecord;
        			style = this.style_for(record);
        			this.$el.find('span#color_field').attr('style',style);
        		}
        	}
    	}
    
    });
    
    instance.web.form.FieldRadio.include({
    	render_value: function () {
            var self = this;
            this.$el.toggleClass("oe_readonly", this.get('effective_readonly'));
            this.$("input:checked").prop("checked", false);
            if (this.get_value()) {
                this.$("input").filter(function () {return this.value == self.get_value();}).prop("checked", true);
                this.$(".oe_radio_readonly").text(this.get('value') ? this.get('value')[1] : "");
            }
            else{
            	//Add condition to set value of element = null when field value is null
            	this.$(".oe_radio_readonly").text("");
            }
        }
            	
    });
    
    instance.web.form.FieldBinary.include({
    	on_file_uploaded: function(size, name, content_type, file_base64) {
    		this._super(size, name, content_type, file_base64);
    		
    		//NG: Case field one2many A link to ir.attachment:
    		//when user choose file in list view of field one2many A, try to call function changed_value of field A
    		//Only check if field have attrs: trigger_on_change
    		//TODO: Handle for other case 
    		if (this.node && this.node.attrs && this.node.attrs['trigger_on_change']){
    			
    			if (this.view && this.view.getParent() && this.view.getParent().getParent()
    			 && this.view.getParent().getParent().getParent()){
    				
    				PPParentView = this.view.getParent().getParent().getParent();
        			//Because tried to call so many getParent(), so i need to check if latest Parent is view of field one2many
        			if (PPParentView.active_view == 'list' && PPParentView.getParent() && PPParentView.getParent().field){
        				PPParentView.getParent().trigger('changed_value');
        			}
    			}
    			
    			
    		};
            
        },
    });
    
    instance.web.form.FormWidget.include({
    	//NG: Function to get color of field based on condition
    	style_for: function (record) {
            var style= '';
            
            var context = _.extend({}, record, {
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

            if (!this.colors) { return style; }
            for(i=0, len=this.colors.length; i<len; ++i) {
                pair = this.colors[i];
                var color = pair[0];
                expression = pair[1];
                var is_have_data = true;
                
                expression.expressions.forEach(function(item,index){
                	//If item consist name of field check if that field have data in context
                	if (item.id == "(name)" && context[item.value]==undefined){
                		is_have_data=false; 
                	} 
                });
                
                if (is_have_data && py.evaluate(expression, context).toJSON()) {
                    return style += 'color: ' + color + ';';
                }
                // TODO: handle evaluation errors
            }
            return style;
        },
    });
}
;
