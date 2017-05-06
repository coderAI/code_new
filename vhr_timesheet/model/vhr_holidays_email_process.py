# -*-coding:utf-8-*-


mail_process = {
                     'draft': [
                               #approve
                                   ['confirm',   {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Submit',
                                                   }
                                    ],
                                    ['confirm',   {    'to'            : ['lm'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Waiting_LM',
                                                        'action_from_email': True,
                                                   }
                                    ],
                                    
                              ],
                
                    'confirm': [
                               #approve
                                   ['validate1',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Notify_LM',
                                                        #Mail có check is_by_pass_with_admin và người action là admin thi ko gửi mail nữa
                                                        'is_by_pass_with_admin': True,
                                                   }
                                    ],
                                   ['validate1',     {    'to'            : ['dept_head'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Waiting_DH',
                                                        'action_from_email': True,
                                                   }
                                    ],
                                   ['validate2',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Notify_LM',
                                                         #Mail có check is_by_pass_with_admin và người action là admin thi ko gửi mail nữa
                                                        'is_by_pass_with_admin': True,
                                                   }
                                    ],
                                    ['validate',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Notify',
                                                   }
                                    ],
                                
                                    ['refuse', { 'to'           :['requester'],
                                                       'cc'            : [],
                                                       'mail_template' : 'LR_Reject_LM'
                                                                   }
                                     ],
                              ],
                    
                    'validate1': [
                               #approve
                                   ['validate2',   {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Notify_DH',
                                                   }
                                    ],
                                   ['validate',   {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'LR_Notify_DH',
                                                   }
                                    ],
                                  ['refuse', { 'to'           :['requester'],
                                                       'cc'            : [],
                                                       'mail_template' : 'LR_Reject_DH'
                                                                   }
                                     ],
                                    
                              ],
                    
#                     'validate2': [
#                                #approve
#                                    ['validate',   {    'to'            : ['requester'],
#                                                         'cc'            : [],
#                                                         'mail_template' : 'LR_Notify_DH',
#                                                    }
#                                     ],
#                                   ['refuse', { 'to'           :['requester'],
#                                                        'cc'            : [],
#                                                        'mail_template' : 'LR_Reject_DH'
#                                                                    }
#                                      ],
#                                     
#                               ],
                
                }