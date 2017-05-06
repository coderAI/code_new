# -*-coding:utf-8-*-


mail_process_of_staff_movement = {
#                      'draft': [
#                                     ['new_hrbp',   {    'to'            : ['new_hrbp'],
#                                                         'cc'            : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                            'old_depthead','new_depthead'],
#                                                         'mail_template' : 'vhr_sm_draft_to_new_hrbp',
# #                                                         'action_from_email': True
#                                                    }
#                                     ],
                               
#                                     ['dept_hr',   {    'to'            : ['dept_hr'],
#                                                         'cc'            : ['old_hrbp','old_assist_hrbp', 'new_depthead'],
#                                                         'mail_template' : 'vhr_sm_draft_to_dept_hr',
# #                                                         'action_from_email': True
#                                                    }
#                                     ],
                               
                               
#                               ],
                
                
#              'new_hrbp': [
#                                    ['dept_hr',   {    'to'            : ['dept_hr'],
# #                                                         'cc'            : ['requester','old_hrbp','old_assist_hrbp','new_assist_hrbp',
# #                                                                            'new_hrbp','old_depthead','new_depthead'],
#                                                         'mail_template' : 'vhr_sm_new_hrbp_to_dept_hr_1',
# #                                                         'action_from_email': True
#                                                    }
#                                     ],
                          
#                                     ['dept_hr',   {    'to'            : ['requester'],
#                                                         'cc'            : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                            'new_hrbp'],
#                                                         'mail_template' : 'vhr_sm_new_hrbp_to_dept_hr_2',
#                                                    }
#                                     ],
                          
#                                     #Return
#                                     ['draft',   {    'to'            : ['requester'],
#                                                         'cc'            : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                            'new_hrbp','old_depthead','new_depthead'],
#                                                         'mail_template' : 'vhr_sm_new_hrbp_to_draft',
#                                                    }
#                                     ],
                          
#                                     #Reject
#                                     ['cancel',   {    'to'            : ['requester'],
#                                                         'cc'            : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                            'new_hrbp','old_depthead','new_depthead'],
#                                                         'mail_template' : 'vhr_sm_new_hrbp_to_cancel',
#                                                    }
#                                     ],
                          
#                             ],
                                    
                    
#              'dept_hr': [
#                          #approve
#                                   ['cb',            {   'to'              : ['requester'],
#                                                         'cc'              : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                              'new_hrbp','old_depthead','new_depthead', 'SM_C&B'],
#                                                         'mail_template'   : 'vhr_sm_hrd_to_cb'}
#                                   ],
#                          #return
#                                   ['new_hrbp',      {   'to'              : ['new_hrbp'],
#                                                          'cc'             : ['new_assist_hrbp', 'new_depthead'],
#                                                          'mail_template'  : 'vhr_sm_hrd_to_new_hrbp'}
#                                    ],
#                          #return
#                                   ['draft',      {   'to'              : ['requester'],
#                                                          'cc'             : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                              'new_hrbp','old_depthead','new_depthead'],
#                                                          'mail_template'  : 'vhr_sm_hrd_to_new_hrbp'}
#                                    ],
                         
#                          #reject
#                                   ['cancel',      {     'to'              : ['requester'],
#                                                          'cc'             : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                              'new_hrbp','old_depthead','new_depthead','dept_hr'],
#                                                          'mail_template'  : 'vhr_sm_hrd_to_cancel'}
#                                    ]
                        
#                         ],
                
                
#                 'cb': [
#                           #reject
#                               ['cancel',          {  'to'           : ['requester'],
#                                                    'cc'             : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                         'new_hrbp','old_depthead','new_depthead','dept_hr'],
#                                                    'mail_template'  : 'vhr_sm_cb_to_cancel'}
#                               ],
#                          ],
                
#                 #From a whatever step to finish, to send email announce change of allowance
#                 'step_to_finish_to_af': [
#                               ['finish',          {  'to'           : ['af_executor'],
#                                                    'cc'             : [],
#                                                    'mail_template'  : 'vhr_sm_announce_allowance_to_af'}
#                               ],
                             
#                          ],
#                 'step_to_finish_to_emp': [
                    
#                                ['finish',          {  'to'           : ['employee'],
#                                                    'cc'             : [],
#                                                    'mail_template'  : 'vhr_sm_announce_allowance_to_employee'}
#                               ],
#                          ],
                                  
#                 'finish': [
#                           #reject
#                               ['cancel',          {  'to'             : ['requester'],
#                                                    'cc'             : ['old_hrbp','old_assist_hrbp','new_assist_hrbp',
#                                                                         'new_hrbp','old_depthead','new_depthead','dept_hr'],
#                                                    'mail_template'  : 'vhr_sm_cb_to_cancel'}
#                               ],
#                          ],
                                    
                                    
               }


            

