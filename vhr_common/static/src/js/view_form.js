/**
 * Created by chanhlt2 on 6/25/14.
 */
openerp.vhr_common = function (instance) {
    instance.web.FormView = instance.web.FormView.extend({
        _process_save: function (save_obj) {
            var self = this;
            var prepend_on_create = save_obj.prepend_on_create;
            try {
                var form_invalid = false,
                    values = {},
                    first_invalid_field = null,
                    save_no_required = false;
                //tuannh3 check type de trim khoang trang dau` duoi cua value
                var check_type = function (value) {
                    if (typeof value === 'string') {
                        return true;
                    }
                    return false;
                };
                //tuannh3 cho phep save bo qua required
                if (self.options !== undefined && self.options.save_no_required === true) {
                    save_no_required = true;
                }
                for (var f in self.fields) {
                    var change_required = false;
                    if (!self.fields.hasOwnProperty(f)) {
                        continue;
                    }
                    f = self.fields[f];
                    if (f.get('required') && f.options['save_no_required'] === true && save_no_required === true) {
                        f.set({required: false});
                        change_required = true;
                    }
                    if (!f.is_valid()) {
                        form_invalid = true;
                        if (!first_invalid_field) {
                            first_invalid_field = f;
                        }
                    } else if (f.name !== 'id' && !f.get("readonly") && (!self.datarecord.id || f._dirty_flag)) {
                        // Special case 'id' field, do not save this field
                        // on 'create' : save all non readonly fields
                        // on 'edit' : save non readonly modified fields
                        //tuannh3 check type de trim khoang trang dau` duoi cua value
                        if (check_type(f.get_value())) {
                            values[f.name] = f.get_value().trim();
                        } else {
                            values[f.name] = f.get_value();
                        }
                    }
                    // Tuannh3 cho phep save readonly
                    else if (f.options['save_readonly'] === true || f.name == 'name') {
                        //tuannh3 check type de trim khoang trang dau` duoi cua value
                        if (check_type(f.get_value())) {
                            values[f.name] = f.get_value().trim();
                        } else {
                            values[f.name] = f.get_value();
                        }
                    }
                    if (change_required === true) {
                        f.set({required: true});
                    }
                }
                if (form_invalid) {
                    self.set({'display_invalid_fields': true});
                    //tuannh3 thay doi thu tu hien thi loi required file
                    //show log truoc roi moi focus
                    self.on_invalid();
                    first_invalid_field.focus();
                    return $.Deferred().reject();
                } else {
                    self.set({'display_invalid_fields': false});
                    var save_deferral;
                    if (!self.datarecord.id) {
                        // Creation save
                        save_deferral = self.dataset.create(values).then(function (r) {
                            return self.record_created(r, prepend_on_create);
                        }, null);
                    } else if (_.isEmpty(values) && !self.force_dirty) {
                        // Not dirty, noop save
                        save_deferral = $.Deferred().resolve({}).promise();
                    } else {
                        self.force_dirty = false;
                        // Write save
                        save_deferral = self.dataset.write(self.datarecord.id, values, {}).then(function (r) {
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
        _process_save: function (save_obj) {
            var self = this;
            var prepend_on_create = save_obj.prepend_on_create;
            try {
                var form_invalid = false,
                    values = {},
                    first_invalid_field = null,
                    readonly_values = {};
                for (var f in self.fields) {
                    if (!self.fields.hasOwnProperty(f)) {
                        continue;
                    }
                    f = self.fields[f];
                    if (!f.is_valid()) {
                        form_invalid = true;
                        if (!first_invalid_field) {
                            first_invalid_field = f;
                        }
                    } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                        // Special case 'id' field, do not save this field
                        // on 'create' : save all non readonly fields
                        // on 'edit' : save non readonly modified fields
                        if (!f.get("readonly")) {
                            values[f.name] = f.get_value();
                        } else {
                            readonly_values[f.name] = f.get_value();
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
    })
}