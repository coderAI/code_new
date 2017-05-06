openerp_vhr_base_views = function (instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.web.Sidebar.include({

        on_item_action_clicked: function (item) {
            var self = this;
            self.getParent().sidebar_eval_context().done(function (sidebar_eval_context) {
                var ids = self.getParent().get_selected_ids();
                //NG: ADD TO SIDE BAR, CONTEXT FROM MENU
                old_context = self.getParent().dataset.context;
                sidebar_eval_context = new instance.web.CompoundContext(sidebar_eval_context || {}, old_context);
//                sidebar_eval_context = $.extend(old_context, sidebar_eval_context);

                var domain;
                if (self.getParent().get_active_domain) {
                    domain = self.getParent().get_active_domain();
                }
                else {
                    domain = $.Deferred().resolve(undefined);
                }
                if (ids.length === 0) {
                    new instance.web.Dialog(this, { title: _t("Warning"), size: 'medium', }, $("<div />").text(_t("You must choose at least one record."))).open();
                    return false;
                }
                var active_ids_context = {
                    active_id: ids[0],
                    active_ids: ids,
                    active_model: self.getParent().dataset.model,
                };

                $.when(domain).done(function (domain) {
                    if (domain !== undefined) {
                        active_ids_context.active_domain = domain;
                    }
                    var c = instance.web.pyeval.eval('context',
                        new instance.web.CompoundContext(
                            sidebar_eval_context, active_ids_context));

                    self.rpc("/web/action/load", {
                        action_id: item.action.id,
                        context: c
                    }).done(function (result) {
                        result.context = new instance.web.CompoundContext(
                                result.context || {}, active_ids_context)
                            .set_eval_context(c);
                        result.flags = result.flags || {};
                        result.flags.new_window = true;
                        self.do_action(result, {
                            on_close: function () {
                                // reload view
                                self.getParent().reload();
                            },
                        });
                    });
                });
            });
        },
    });

    instance.web.ViewManager.include({
        do_create_view: function(view_type) {
            // Lazy loading of views
            var self = this;
            var view = this.views[view_type];
            var viewclass = this.registry.get_object(view_type);
            var options = _.clone(view.options);
            if (view_type === "form" && this.action && (this.action.target == 'new' || this.action.target == 'inline')) {
                if(this.action.initial_mode!= undefined)
                	options.initial_mode = this.action.initial_mode;
                else
                	options.initial_mode = 'edit';
            }
            var controller = new viewclass(this, this.dataset, view.view_id, options);

            controller.on('history_back', this, function() {
                var am = self.getParent();
                if (am && am.trigger) {
                    return am.trigger('history_back');
                }
            });

            controller.on("change:title", this, function() {
                if (self.active_view === view_type) {
                    self.set_title(controller.get('title'));
                }
            });

            if (view.embedded_view) {
                controller.set_embedded_view(view.embedded_view);
            }
            controller.on('switch_mode', self, this.switch_mode);
            controller.on('previous_view', self, this.prev_view);
            
            var container = this.$el.find("> div > div > .oe_view_manager_body > .oe_view_manager_view_" + view_type);
            var view_promise = controller.appendTo(container);
            this.views[view_type].controller = controller;
            this.views[view_type].deferred.resolve(view_type);
            return $.when(view_promise).done(function() {
                if (self.searchview
                        && self.flags.auto_search
                        && view.controller.searchable !== false) {
                    self.searchview.ready.done(self.searchview.do_search);
                } else {
                    self.view_completely_inited.resolve();
                }
                self.trigger("controller_inited",view_type,controller);
            });
        },
    });

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
                self.remove_default_toolbar_item(r, 'export', 'Export');
                self.remove_default_toolbar_item(r, 'delete', 'Delete');
                
                self.remove_toolbar_section('attachment','Attachment(s)');
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
        remove_default_toolbar_item: function(data, option, name){
        	//Remove default item in Menu More
        	if (!this.context_enabled(option) && this && this.sidebar && this.sidebar.items && this.sidebar.items.other) {
        		menu = this.sidebar.items.other;
        		for (index in menu){
        			if (menu[index] && menu[index].label == name){
        				menu.splice(index, 1);
        				break;
        			}
        		}
        		this.sidebar.redraw();
        	}
        },
      //NG: Remove item in Sidebar if set it in context
        remove_toolbar_section: function(option, name){
        	rthis = this
        	self.$('.oe_form_dropdown_section').each(function() {
            	if (!rthis.context_enabled(option) && $(this).find('button') && $(this).find('button')[0].innerHTML.trim() == name )
            		{
            			$(this).remove();
            		}
                
            });
        }

    });
};