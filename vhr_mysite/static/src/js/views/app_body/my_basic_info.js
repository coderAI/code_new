'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var BasicInfoView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				
				this.parent = options.parent;
				this.my_employee_id = options.my_employee_id;
			},
			
			el: '.basic-info',
			
			template: false,
			
			ui: {
				
				// BUTTON
				
				// INPUT
				input_avatar_file: 'input#my_avatar_file',
				
				img_avatar_display: 'img#my_avatar_display',
				
				btn_save_avatar: 'a#my_avatar_save',
			},
			
			events: {
				
				'change @ui.input_avatar_file': 'onChangeInputAvatar',
				
				'click @ui.btn_save_avatar': 'onSaveAvatar',
			},
			
			onChangeInputAvatar: function(e) {
				
				var self = this;
				// Check for the various File API support.
				if (window.File && window.FileReader && window.FileList && window.Blob) {
					// Great success! All the File APIs are supported.
					var files =  e.target.files;
					
					_.each(files, function(file) {

						var reader = new FileReader();
						var raw_data = '';
						
						reader.onload = function(e) {
							
							// Check image size, max size = 3MB
							if (e.total > 3072 * 1000) {
								return bootbox.alert({ 
								    size: 'small',
								    message: 'Hình ảnh không được vượt quá 3MB',
								});
							}

							raw_data = e.target.result;
							self.parent.global_data_decode64 = raw_data.substring(raw_data.indexOf(',')+1);
							
							self.$el.find(self.ui.img_avatar_display).attr('src', raw_data);
							
							$(self.ui.btn_save_avatar).show();
						}
						
						reader.readAsDataURL(file);
					});
				} else {

				  alert('The File APIs are not fully supported in this browser.');
				}
			},
			
			onSaveAvatar: function(e) {
				
				var self = this;

				if (self.parent.global_data_decode64 !== '') {
					openerp.jsonRpc(
					    '/mysite/set_my_avatar', 'call', {
					    	'image': self.parent.global_data_decode64,
					    }
					).then(function(result) {
						
						$(self.ui.btn_save_avatar).hide();
						if (result) {

							return bootbox.alert({ 
							    size: 'small',
							    message: 'Hình đại diện đã được cập nhật',
							});
						} else {

							return bootbox.alert({ 
							    size: 'small',
							    message: 'Có lỗi trong quá trình cập nhật',
							});
						}
					});
				}
			},
			
		});

		return BasicInfoView;
	}
);
