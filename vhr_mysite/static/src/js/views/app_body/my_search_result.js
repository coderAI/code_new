'use strict';

define(
	["marionette"],
	function(Marionette) {
		
		var vhr_mysite = openerp.vhr_mysite,
			ItemView = Marionette.ItemView,
			_super = ItemView.prototype;
		
		var MySearchResultView = ItemView.extend({
			
			initialize: function(options) {

				_super.initialize.apply(this, arguments);
				
				 $('#my_search_table').dataTable();
				 
				 this.domain_div = this.domain_dept = this.domain_team = false;
			},
			
			el: '.my_search_result',
			
			template: false,
			
			ui: {
				
				btn_select_division_breath: '.select_division .oe_breathing',
				btn_select_dept_breath: '.select_dept .oe_breathing',
				btn_select_team_breath: '.select_team .oe_breathing',
				btn_select_breath: '#btn_detail_search .oe_breathing',
				
				select_division_breath: '.select_division select',
				select_dept_breath: '.select_dept select',
				select_team_breath: '.select_team select',
				
				btn_search: '#btn_detail_search',
			},
			
			events: {
				
				'click @ui.btn_select_division_breath': 'onClickDivBreath',
				'click @ui.btn_select_dept_breath': 'onClickDeptBreath',
				'click @ui.btn_select_team_breath': 'onClickTeamBreath',
				
				'change @ui.select_division_breath': 'onChangeSelectDiv',
				'change @ui.select_dept_breath': 'onChangeSelectDept',
				'change @ui.select_team_breath': 'onChangeSelectTeam',
				
				'click @ui.btn_search': 'onClickButtonSearch',
			},
			
			onClickDivBreath: function(e) {
				
				var select = this.$el.find(this.ui.select_division_breath);
				
				var e = document.createEvent('MouseEvents');
			    e.initMouseEvent('mousedown');
			    select[0].dispatchEvent(e);
			    
//			    this.$el.find(this.ui.btn_select_division_breath).addClass('hidden');
//			    this.$el.find(this.ui.btn_select_dept_breath).removeClass('hidden');
			},
			
			onChangeSelectDiv: function(e) {
				
				var self = this;
				// get parent_id
			    var parent_id = parseInt(this.$el.find(this.ui.select_division_breath + ' > option:selected').val());
			    parent_id = parent_id != -1 ? parent_id : false;
			    
			    // Change domain for search
			    if (parent_id) {
			    	this.domain_div = parseInt(parent_id);
			    } else {
			    	this.domain_div = false;
			    }
			    
			    // Call backend for load data
			    openerp.jsonRpc(

				    '/mysite/search/dept', 'call', {'type': 'dept', 'parent_id': parent_id}

				).then(function (result) {
					
					if (result) {
						
						self.$el.find(self.ui.select_dept_breath).html('<option value="-1"></option>');
						self.$el.find(self.ui.select_team_breath).html('<option value="-1"></option>');
						_.each(result, function(item) {
							self.$el.find(self.ui.select_dept_breath).append('<option value="'+ item.id +'">'+ item.code + ' - ' + item.name +'</option>');
						});
						
						// Trigger click event
						self.$el.find(self.ui.btn_select_division_breath).addClass('hidden');
						self.$el.find(self.ui.btn_select_team_breath).addClass('hidden');
						self.$el.find(self.ui.btn_select_dept_breath).removeClass('hidden');
						self.$el.find(self.ui.btn_select_breath).removeClass('hidden');
					}
				});
			},
			
			onClickDeptBreath: function(e) {
				
				var select = this.$el.find(this.ui.select_dept_breath);
				
				var e = document.createEvent('MouseEvents');
			    e.initMouseEvent('mousedown');
			    select[0].dispatchEvent(e);
			    
//			    this.$el.find(this.ui.btn_select_dept_breath).addClass('hidden');
//			    this.$el.find(this.ui.btn_select_team_breath).removeClass('hidden');
			},
			
			onChangeSelectDept: function(e) {
				
				var self = this;
				// get parent_id
			    var parent_id = parseInt(this.$el.find(this.ui.select_dept_breath + ' > option:selected').val());
			    parent_id = parent_id != -1 ? parent_id : false;
			    
			    // Change domain for search
			    if (parent_id) {
			    	this.domain_dept = parseInt(parent_id);
			    } else {
			    	this.domain_dept = false;
			    }
			    
			    // Call backend for load data
			    openerp.jsonRpc(

				    '/mysite/search/dept', 'call', {'type': 'team', 'parent_id': parent_id}

				).then(function (result) {
					
					if (result) {
						
						self.$el.find(self.ui.select_team_breath).html('<option value="-1"></option>');
						_.each(result, function(item) {
							self.$el.find(self.ui.select_team_breath).append('<option value="'+ item.id +'">'+ item.code + ' - ' + item.name +'</option>');
						});
						
						// Trigger click event
						self.$el.find(self.ui.btn_select_dept_breath).addClass('hidden');
						self.$el.find(self.ui.btn_select_team_breath).removeClass('hidden');
						self.$el.find(self.ui.btn_select_breath).removeClass('hidden');
					}
				});
			},
			
			onClickTeamBreath: function(e) {
				
				var select = this.$el.find(this.ui.select_team_breath);
				
				var e = document.createEvent('MouseEvents');
			    e.initMouseEvent('mousedown');
			    select[0].dispatchEvent(e);
			    
//			    this.$el.find(this.ui.btn_select_team_breath).addClass('hidden');
			},
			
			onChangeSelectTeam: function(e) {
				// get parent_id
			    var parent_id = parseInt(this.$el.find(this.ui.select_team_breath + ' > option:selected').val());
			    parent_id = parent_id != -1 ? parent_id : false;
			    
				// Change domain for search
			    if (parent_id) {
			    	this.domain_team = parseInt(parent_id);
			    } else {
			    	this.domain_team = false;
			    }
			    
				// Trigger click event
				this.$el.find(this.ui.btn_select_team_breath).addClass('hidden');
				this.$el.find(this.ui.btn_select_breath).removeClass('hidden');
			},
			
			onClickButtonSearch: function(e) {
				
				e.preventDefault();
				var query = '';
				var sel_div = this.$el.find(this.ui.select_division_breath + ' > option:selected'),
					sel_dept = this.$el.find(this.ui.select_dept_breath + ' > option:selected'),
					sel_team = this.$el.find(this.ui.select_team_breath + ' > option:selected');
				// if not onchange, check selected, if not selected -> false
				this.domain_div = this.domain_div ? this.domain_div : (parseInt(sel_div.val()) != -1 ? parseInt(sel_div.val()) : false) ;
				this.domain_dept = this.domain_dept ? this.domain_dept : (parseInt(sel_dept.val()) != -1 ? parseInt(sel_dept.val()) : false) ;
				this.domain_team = this.domain_team ? this.domain_team : (parseInt(sel_team.val()) != -1 ? parseInt(sel_team.val()) : false) ;
				
				if (this.domain_div) {
					query = (query == '') ? '?div=' + this.domain_div.toString() : query + '&div=' + this.domain_div.toString();
				}
				if (this.domain_dept) {
					query = (query == '') ? '?dept=' + this.domain_dept.toString() : query + '&dept=' + this.domain_dept.toString();
				}
				if (this.domain_team) {
					query = (query == '') ? '?team=' + this.domain_team.toString() : query + '&team=' + this.domain_team.toString();
				}
				
				if (query != '') {
					document.location = '/mysite/search/' + query;
				}
			},
			
		});

		return MySearchResultView;
	}
);
