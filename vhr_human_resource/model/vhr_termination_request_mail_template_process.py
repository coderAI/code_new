# -*-coding:utf-8-*-
mail_process_of_ter_online = {
#                      'draft': [
#                                #approve
#                                    ['supervisor', {    'to'            : ['lm'],
#                                                         'cc'            : ['hrbp','assist_hrbp','dept_head','RR','RAM','TER_C&B','lm_loop'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr','lm_loop'],
#                                                         'mail_template' : 'vhr_termination_draft_to_lm_termination_online',
                                                        
#                                                    }
#                                     ],
                                
                               
#                                #case bypass to next state
#                                     ['hrbp',        {    'to'            : ['hrbp'],
#                                                         'cc'            : ['assist_hrbp','dept_head','RR','RAM','TER_C&B','lm_loop'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr','lm_loop'],
#                                                         'mail_template' : 'vhr_termination_lm_to_hrbp_2_termination_online',
# #                                                         'action_from_email': True
#                                                    }
#                                     ],
#                                     ['dept_head',  {    'to'            : ['requester'],
#                                                         'cc'            : ['hrbp','assist_hrbp','dept_head','RR','RAM','TER_C&B','lm_loop'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr','lm_loop'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_termination_online'
#                                                    }
#                                     ],
#                                 #Huong dan tro cap that nghiep
#                                 #We need to send this template if by pass to/over dept head
#                                     ['dept_head',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
#                                  #Wating for DH approval
#                                     ['dept_head',  {    'to'            : ['dept_head'],
#                                                         'cc'            : ['hrbp','assist_hrbp','RR','RAM','TER_C&B','lm_loop'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr','lm_loop'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_3_termination_online',
#                                                         'action_from_email': True
#                                                    }
#                                     ],
#                                #Huong dan tro cap that nghiep
#                                #We need to send this template if by pass to/over dept head
#                                     ['finish',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
#                                 # Termination Announcement 
#                                     ['finish',      {    'to'            : ['IT','AF_Helpdesk','TER_C&B','FA','LG'],
#                                                         'cc'            : ['requester','hrbp','assist_hrbp','lm','dept_hr','RR','RAM','dept_head'],
#                                                         'mail_template' : 'vhr_termination_hrd_to_fin_2_termination_online',
#                                                         'not_split_email': True
#                                                    }
#                                     ],
                                    
#                               ],
                    
#                  'supervisor': [
#                                 #approve
#                                    ['hrbp',        {    'to'            : ['requester'],
#                                                         'cc'            : [],
#                                                         'mail_template' : 'vhr_termination_lm_to_hrbp_termination_online'
#                                                    }
#                                     ],
                                
#                                    ['hrbp',        {    'to'            : ['hrbp'],
#                                                         'cc_level_fr_3' : [],
#                                                         'cc'            : ['assist_hrbp'],
#                                                         'mail_template' : 'vhr_termination_lm_to_hrbp_2_termination_online',
# #                                                         'action_from_email': True
#                                                    }
#                                     ],
                                    
#                                     #In mail have link to exit survey
#                                     ['dept_head',        {    'to'            : ['requester'],
#                                                         'cc'            : [],
#                                                         'mail_template' : 'vhr_termination_lm_to_hrbp_termination_online'
#                                                    }
#                                     ],
                                    
#                                     ['dept_head',  {    'to'            : ['requester'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_termination_online'
#                                                    }
#                                     ],
#                               #Huong dan tro cap that nghiep
#                                #We need to send this template if by pass to/over dept head
                                    
#                                     ['dept_head',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
                                 
#                                     ['dept_head',  {    'to'            : ['dept_head'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_3_termination_online',
#                                                         'action_from_email': True
#                                                    }
#                                     ],
                                    
#                                     #In mail have link to exit survey
#                                     ['finish',        {    'to'            : ['requester'],
#                                                         'cc'            : [],
#                                                         'mail_template' : 'vhr_termination_lm_to_hrbp_termination_online'
#                                                    }
#                                     ],
#                                 #Huong dan tro cap that nghiep
#                                #We need to send this template if by pass to/over dept head
#                                     ['finish',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
#                                 #Termination Announcement -
#                                     ['finish',      {    'to'            : ['IT','AF_Helpdesk','TER_C&B','FA','LG'],
#                                                         'cc'            : ['requester','hrbp','assist_hrbp','lm','dept_hr','RR','RAM','dept_head'],
#                                                         'mail_template' : 'vhr_termination_hrd_to_fin_2_termination_online',
#                                                         'not_split_email': True
#                                                    }
#                                     ],
                                



#                                 #reject
#                                     ['cancel',     {    'to'            : ['requester'],
#                                                         'cc'            : ['hrbp','assist_hrbp','dept_head','RR','RAM','TER_C&B'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr'],
#                                                         'mail_template' : 'vhr_termination_lm_to_cancel_termination_online'
#                                                    }
#                                     ]
#                               ],
                              
#                     'hrbp':  [
#                               #approve
#                                    ['dept_head',  {    'to'            : ['requester'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_termination_online'
#                                                    }
#                                     ],
#                                #Huong dan tro cap that nghiep
#                                #We need to send this template if by pass to/over dept head
#                                     ['dept_head',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
                                 
#                                     ['dept_head',  {    'to'            : ['dept_head'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'cc_level_fr_3' : ['hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_3_termination_online',
#                                                         'action_from_email': True
#                                                    }
#                                     ],
                                    
                                    
#                                      #Huong dan tro cap that nghiep
#                                #We need to send this template if by pass to/over dept head
#                                     ['finish',  {    'to'            : ['employee'],
#                                                         'cc'            : ['hrbp','assist_hrbp'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_dh_2_termination_online',
#                                                         'only_sent_once': True,
#                                                    }
#                                     ],
#                                 #Termination Announcement
#                                     ['finish',      {    'to'            : ['IT','AF_Helpdesk','TER_C&B','FA','LG'],
#                                                         'cc'            : ['requester','hrbp','assist_hrbp','lm','dept_hr','RR','RAM','dept_head'],
#                                                         'mail_template' : 'vhr_termination_hrd_to_fin_2_termination_online',
#                                                         'not_split_email': True
#                                                    }
#                                     ],
                              
                              
#                               #reject
#                                     ['cancel',     {    'to'            : ['requester'],
#                                                         'cc'            : ['lm','hrbp','assist_hrbp','dept_head','RR','RAM','TER_C&B'],
#                                                         'cc_level_fr_3' : ['hrbp','dept_head','PR_TEAM_LEADER','cb_manager','dept_hr','lm'],
#                                                         'mail_template' : 'vhr_termination_hrbp_to_cancel_termination_online'
#                                                    }
#                                     ]
                              
#                               ],
                              
#                      'dept_head': [
                                   
#                                 #Termination Announcement
#                                     ['finish',      {    'to'            : ['IT','AF_Helpdesk','TER_C&B','FA','LG'],
#                                                         'cc'            : ['requester','hrbp','assist_hrbp','lm','dept_hr','RR','RAM'],
#                                                         'mail_template' : 'vhr_termination_hrd_to_fin_2_termination_online',
#                                                         'not_split_email': True
#                                                    }
#                                     ],
                                   
#                                    ['cancel',      {    'to'            : ['requester'],
#                                                         'cc'            : ['hrbp','assist_hrbp','lm','RR','RAM','TER_C&B'],
#                                                         'cc_level_fr_3' : ['hrbp','PR_TEAM_LEADER','cb_manager','dept_hr','lm'],
#                                                         'mail_template' : 'vhr_termination_dh_to_cancel_termination_online'
#                                                    }
#                                     ]
#                               ],
                              
#                      'finish': [
#                                    ['change',      {    'to'            : ['IT','AF_Helpdesk','TER_C&B','FA','LG'],
#                                                         'cc'            : ['requester','hrbp','assist_hrbp','dept_head','lm','RR','RAM'],
#                                                         'mail_template' : 'vhr_termination_fin_adjust_LWD_termination_online',
#                                                         'not_split_email': True
#                                                    }
#                                     ]
#                               ],
                
                
}

mail_process_of_ter_offline_official = {
                    #  'draft': [
                                
                    #                 ['finish',     {    'to'            : ['IT','FA','AF','TER_C&B'],
                    #                                     'cc'            : ['dept_hr','hrbp','assist_hrbp','dept_head','RR','RAM'],
                    #                                     'mail_template' : 'vhr_termination_hrd_to_fin_2_termination_offline_official',
                    #                                     'not_split_email': True
                    #                                }
                    #                 ],
                               
                    #           ],
                    
                    
                    # 'finish': [
                    #                ['change',      {    'to'            : ['IT','FA','AF','TER_C&B_CTV'],
                    #                                     'cc'            : ['hrbp','assist_hrbp','dept_hr','dept_head','RR','RAM'],
                    #                                     'mail_template' : 'vhr_termination_fin_adjust_LWD_termination_online',
                    #                                     'not_split_email': True
                    #                                }
                    #                 ]
                    #           ],
 }

mail_process_of_ter_offline_not_official = {
                    #  'draft': [
                                
                    #                 ['finish',     {    'to'            : ['IT','FA','AF','TER_C&B_CTV'],
                    #                                     'cc'            : ['hrbp','assist_hrbp'],
                    #                                     'mail_template' : 'vhr_termination_cb_to_fin_termination_offline_not_official',
                    #                                     'not_split_email': True
                    #                                }
                    #                 ],
                               
                    #           ],
                    
                    
                    # 'finish': [
                    #                ['change',      {    'to'            : ['IT','FA','AF','TER_C&B_CTV'],
                    #                                     'cc'            : ['hrbp','assist_hrbp','dept_hr','dept_head','RR','RAM'],
                    #                                     'mail_template' : 'vhr_termination_fin_adjust_LWD_termination_online',
                    #                                     'not_split_email': True
                    #                                }
                    #                 ]
                    #           ],
}

