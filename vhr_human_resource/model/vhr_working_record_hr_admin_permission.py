# -*-coding:utf-8-*-
#Why i dont separate this file to multi modules based on fields of every inherit model :|
#vhr_dept_head là 1 group ảo, thực tế không có group này
fields_permission = {
                     
                'employee_id':  {
                                 "all_group": {'read':['record','request'],     'write':['record','request']}
                             }, 
                     
                'company_id':  {
                                "all_group": {'read':['record','request'],      'write':['record','request']}
                             }, 
                     
                'effect_from':  {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
                                 'vhr_dept_admin': {'read':['record'],                  'write':['record']}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':['record']}, 
                                 "all_group": {'read':['record','request'],     'write':[]},
                             }, 
                     
                'change_form_ids' : {
                                'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
                                 'vhr_dept_admin': {'read':['record'],                  'write':['record']}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':['record']}, 
                                 "all_group": {'read':['record','request'],     'write':[]},
                             },
                     
                'decision_no':  {
                                 "all_group": {'read':[],     'write':[]}
                             }, 
                     
                'sign_date':  {
                               "all_group": {'read':[],     'write':[]}
                             }, 
                
                'signer_id':  {
                              "all_group": {'read':[],     'write':[]}
                             }, 
                
                'signer_job_title_id':  {
                                 "all_group": {'read':[],     'write':[]}
                             },
               
               'country_signer':  {
                                 "all_group": {'read':[],     'write':[]}
                             },
               'work_for_company_id_old': {
                                "all_group": {'read':[],     'write':[]},
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
#                                  'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'work_for_company_id_new': {
                                "all_group": {'read':[],     'write':[]},
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
#                                  'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                
               'office_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
               'division_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               'department_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[ ]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[ ]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               'department_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[ ]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[ ]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'team_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
                'job_title_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                
                'career_track_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
               'pro_job_family_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_job_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_sub_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_ranking_level_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_grade_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
               'office_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
               'division_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'department_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               'department_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'team_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
                'job_title_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'career_track_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
               'pro_job_family_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_job_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_sub_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_ranking_level_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'pro_grade_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                'vhr_dept_admin': {'read':[],                          'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                          'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                
                'mn_job_family_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_job_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_sub_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_ranking_level_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_grade_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'mn_job_family_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_job_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_sub_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_ranking_level_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'mn_grade_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['request'],             'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'job_level_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                     
                'job_level_person_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],               'write':[]}, 
                                 'vhr_af_admin':   {'read':[],               'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                     
                'job_level_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                'job_level_person_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                  'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                                },
                
#                 'position_class_id_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':[],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
               
               'report_to_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                   'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'manager_id_old': {
                               "all_group": {'read':['record','request'],       'write':[]}
                               },
               
#                'approver_id_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],               'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
               
#                'mentor_id_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],               'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
                     
               
#                 'position_class_id_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
#                                  'vhr_dept_admin': {'read':[],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
               
               'report_to_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':['record']}, 
                                 'vhr_af_admin':   {'read':['record'],                  'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'manager_id_new': {
                               "all_group": {'read':['record','request'],       'write':[]}
                               },
               
#                'approver_id_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_dept_admin': {'read':['record'],               'write':['record']}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
#                
#                'mentor_id_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],               'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
               
#                'ts_working_schedule_id_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':[],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':[],                 'write':[]}, 
#                                },
                'ts_working_group_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
               'timesheet_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':[],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':[],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
               'salary_setting_id_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':[],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':[],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
#                'ts_working_schedule_id_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':[],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]}, 
#                                  'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':[],                 'write':[]}, 
#                                },
                'ts_working_group_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]}, 
                                 'vhr_hr_dept_head':{'read':['record',],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
               'timesheet_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':[],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':[],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
               'salary_setting_id_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':[],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':[],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
               
               'seat_old': {   
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]},
                                 'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
                     
               'ext_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':[]},
                                 'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
#                      
#                'work_phone_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],                  'write':[]}, 
#                                  'vhr_af_admin':   {'read':['record'],                  'write':[]},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
#                      
#                'work_email_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
#                                  'vhr_hrbp':       {'read':['record','request'],             'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
#                      
#                'mobile_phone_old': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
#                                  'vhr_dept_admin': {'read':[],                  'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },     
                
               
               'seat_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':['record']},
                                 'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
                     
               'ext_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':['record'],               'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':['record']},
                                 'vhr_hr_dept_head':{'read':['record'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':[],                 'write':[]}, 
                               },
                     
#                'work_phone_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],             'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],             'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],                       'write':[]}, 
#                                  'vhr_af_admin':   {'read':['record'],                       'write':['record']},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
#                      
#                'work_email_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],             'write':[]},
#                                  'vhr_dept_admin': {'read':['record'],                      'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
#                      
#                'mobile_phone_new': {
#                                  'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_hrbp':       {'read':['record','request'],        'write':['record','request']},
#                                  'vhr_dept_admin': {'read':[],                  'write':[]}, 
#                                  'vhr_af_admin':   {'read':[],                      'write':[]},
#                                  'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
#                                  'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
#                                },
               
               'keep_authority_fcnt': {
                                 'vhr_cb_working_record':         {'read':['record','request'],             'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],             'write':[]},
                                 'vhr_dept_admin': {'read':['record'],                       'write':[]}, 
                                 'vhr_af_admin':   {'read':['record'],                       'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'salary_percentage_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
               'gross_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'basic_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'kpi_amount_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'general_allowance_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
               'v_bonus_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'collaborator_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'type_of_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'probation_salary_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'is_salary_by_hours_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_1_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_2_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_3_old': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]}, 
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]}, 
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
               
               'gross_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               }, 
                     
               'salary_percentage_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'basic_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'kpi_amount_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'general_allowance_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                
                'v_bonus_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
               'type_of_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
                'probation_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'collaborator_salary_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'is_salary_by_hours_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_1_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_2_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                'salary_by_hours_timeline_3_new': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':['request']},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
                'note': {
                                "all_group": {'read':['record','request'],      'write':['record','request']}
                               },
                
                'state': {
                                "all_group": {'read':['request'],                   'write':['request']}
                               },
                
                'requester_id': {
                               "all_group": {'read':['request']}
                               },
                'is_public': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':['record','request']},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':['record'],               'write':['record']}, 
                                 'vhr_af_admin':   {'read':['record'],               'write':['record']},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               },
                     
                     
                'old_allowance_ids': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               }, 
                'new_allowance_ids': {
                                 'vhr_cb_working_record':         {'read':['record','request'],        'write':[]},
                                 'vhr_cb_working_record_readonly':         {'read':['record','request'],        'write':[]},
                                 'vhr_hrbp':       {'read':['record','request'],        'write':[]},
                                 'vhr_dept_admin': {'read':[],                      'write':[]}, 
                                 'vhr_af_admin':   {'read':[],                      'write':[]},
                                 'vhr_hr_dept_head':{'read':['record','request'],       'write':[]}, 
                                 'vhr_dept_head':  {'read':['request'],                 'write':[]}, 
                               }, 
               
               }
