openerp_vhr_base_search = function (instance) {
    var _t = instance.web._t;
    instance.web.search.CharField.include({
    	complete: function (value) {
        	value = value.replace(/\s+/g, " ");
        	value = value.replace(/^\s+|\s+$/g, "");
            if (_.isEmpty(value)) { return $.when(null); }
            var label = _.str.sprintf(_.str.escapeHTML(
                _t("Search %(field)s for: %(value)s")), {
                    field: '<em>' + _.escape(this.attrs.string) + '</em>',
                    value: '<strong>' + _.escape(value) + '</strong>'});
            return $.when([{
                label: label,
                facet: {
                    category: this.attrs.string,
                    field: this,
                    values: [{label: value, value: value}]
                }
            }]);
        }
    });
    
    instance.web.search.Field.include({
        get_domain: function (facet) {
            if (!facet.values.length) { return; }

            var value_to_domain;
            var self = this;
            var domain = this.attrs['filter_domain'];
            if (domain) {
                value_to_domain = function (facetValue) {
                    return new instance.web.CompoundDomain(domain)
                        .set_eval_context({self: self.value_from(facetValue)});
                };
            } else {
                value_to_domain = function (facetValue) {
                    return self.make_domain(
                        self.attrs.name,
                        self.attrs.operator || self.default_operator,
                        facetValue);
                };
            }
            var domains = facet.values.map(value_to_domain);

            if (domains.length === 1) { return domains[0]; }
            for (var i = domains.length; --i;) {
            	//tuannh3 default search &
                //domains.unshift(['|']);
            	domains.unshift(['&']);
            }

            return _.extend(new instance.web.CompoundDomain(), {
                __domains: domains
            });
        }
    });
    
    instance.web.SearchView.include({
    	// NX: Trigger the table header scroll event everytime click on search toolbar
    	// Re-caculate the list view header.
        events: _.extend({}, instance.web.SearchView.prototype.events, {
        	'click .oe_searchview_unfold_drawer': function (e) {
                e.stopImmediatePropagation();
                if (this.drawer) 
                    this.drawer.toggle();
                $('div[id^="hdScroll"]').trigger("scroll");
            },
        }),
    });
    
    instance.web.SearchViewDrawer.include({
    	// NX: Trigger the table header scroll event everytime click on search toolbar
    	// Re-caculate the list view header.
        events: _.extend({}, instance.web.SearchViewDrawer.prototype.events, {
        	'click .oe_searchview_savefilter': function (e) {
                $('div[id^="hdScroll"]').trigger("scroll");
            },
            'click .oe_searchview_advanced': function (e) {
                $('div[id^="hdScroll"]').trigger("scroll");
            },
            'click .oe_searchview_dashboard': function (e) {
                $('div[id^="hdScroll"]').trigger("scroll");
            },
            'click .searchview_extended_delete_prop': function (e) {
                $('div[id^="hdScroll"]').trigger("scroll");
            },
        }),
    });
    
    instance.web.search.ExtendedSearchProposition.include({
    	events: _.extend({}, instance.web.search.ExtendedSearchProposition.prototype.events, {
    		'click .searchview_extended_delete_prop': function (e) {
                e.stopPropagation();
                this.getParent().remove_proposition(this);
                $('div[id^="hdScroll"]').trigger("scroll");
            }
        }),
    });
};
