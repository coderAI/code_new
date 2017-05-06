# -*-coding:utf-8-*-


mail_process = {
                     'draft': [
                               #approve
                                   ['approve',   {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'vhr_ts_overtime_draft_to_lm_1',
                                                   }
                                    ],
                                    ['approve',   {    'to'            : ['lm'],
                                                        'cc'            : [],
                                                        'mail_template' : 'vhr_ts_overtime_draft_to_lm_2',
                                                        'action_from_email': True
                                                   }
                                    ],
                                    ['approve_late', { 'to'           :['requester'],
                                                       'cc'            : [],
                                                       'mail_template' : 'vhr_ts_overtime_submit_ot_pay_money_late'
                                                                   }
                                     ]
                              ],
                
                    'approve': [
                               #approve
                                   ['finish',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'vhr_ts_overtime_lm_to_fin',
                                                   }
                                    ],
                                   ['draft',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'vhr_ts_overtime_lm_to_draft',
                                                   }
                                    ],
                                    ['cancel',     {    'to'            : ['requester'],
                                                        'cc'            : [],
                                                        'mail_template' : 'vhr_ts_overtime_lm_to_cancel',
                                                   }
                                    ],
                                
                                    ['approve_late', { 'to'           :['requester'],
                                                       'cc'            : ['lm'],
                                                       'mail_template' : 'vhr_ts_overtime_approve_ot_pay_money_late'
                                                                   }
                                     ],
                              ],
                }