# -*-coding:utf-8-*-#
######################
###File này hiện chỉ có hiệu lực đối với 1 số field được khai báo.
###Khi xem xét attribute của các field trong view, nên xem trong hàm fields_view_get và view để biết rõ ràng hơn.
###Vì phân quyền readonly, required, invisible của các field trong Termination phức tạp hơn rất nhiều so với trong Working Record,
###nên mô tả trong file này chỉ có tác dụng thấp đối với 1 số field: employee_id, company_id, date_end_working_approve, 
######################

draft_permission = {

    'employee_id': {
        'write': ['vhr_requestor'],
    },
    'company_id': {
        'write': ['vhr_requestor'],
    },
    'date_end_working_expect': {
        'write': ['vhr_requestor'],
    },
    'ending_probation': {
        'write': [],
    },
    # 'resignation_type': {
    # 'write': [],
    # },
    # 'change_form_id': {
    #     'write': [],
    # },
    'resignation_reason': {
        'write': [],
    },
    # 'resign_reason_detail_ids': {
    # 'write': [],
    # },
    # 'suggest_for_holding_employee': {
    #     'write': [],
    # },
    # 'hrbp_note': {
    #     'write': [],
    # },
    # 'continue_recruiting_id': {
    #     'write': [],
    # },
    'date_end_working_approve': {
        'write': [],
    },
    'update_date': {
        'write': [],
    },
    'date_response_to_af_fa_it': {
        'write': [],
    },
    'severance_allowance': {
        'write': [],
    },
    'decision_no': {
        'write': [],
    },
    'sign_date': {
        'write': [],
    },
    'signer_id': {
        'write': [],
    },
    'signer_job_title_id': {
        'write': [],
    },
    # 'attached_file': {
    # 'write': [],
    # },
    'note': {
        'write': [],
    },


}

hrbp_permission = {

    'employee_id': {
        'write': [],
    },
    'company_id': {
        'write': [],
    },
    'date_end_working_expect': {
        'write': [],
    },
    # 'ending_probation': {
    # 'write': ['vhr_hrbp'],
    # },
    # 'resignation_type': {
    # 'write': ['vhr_hrbp'],
    # },
    # 'change_form_id': {
    #     'write': ['vhr_hrbp'],
    # },
    #                 'resignation_reason': {
    #                                      'write': ['vhr_hrbp'],
    #                                      },
    # 'resign_reason_detail_ids': {
    # 'write': ['vhr_hrbp'],
    # },
    # 'suggest_for_holding_employee': {
    #     'write': ['vhr_hrbp'],
    # },
    # 'hrbp_note': {
    #     'write': ['vhr_hrbp'],
    # },
    # 'continue_recruiting_id': {
    #     'write': ['vhr_hrbp'],
    # },
    'date_end_working_approve': {
        'write': [],
    },
    'update_date': {
        'write': [],
    },
    'date_response_to_af_fa_it': {
        'write': [],
    },
    'severance_allowance': {
        'write': [],
    },
    'decision_no': {
        'write': [],
    },
    'sign_date': {
        'write': [],
    },
    'signer_id': {
        'write': [],
    },
    'signer_job_title_id': {
        'write': [],
    },
    #                 'attached_file': {
    #                                           'write': [],
    #                                           },
    'note': {
        'write': [],
    },
}

cb_permission = {

    'employee_id': {
        'write': [],
    },
    'company_id': {
        'write': [],
    },
    'date_end_working_expect': {
        'write': [],
    },
    'ending_probation': {
        'write': [],
    },
    # 'resignation_type': {
    # 'write': [],
    # },
    'resignation_reason': {
        'write': [],
    },
                 
                  
                  
    # 'change_form_id': {
    # 'write': [],
    # },
    # 'resign_reason_detail_ids': {
    #     'write': [],
    # },
    # 'suggest_for_holding_employee': {
    #     'write': [],
    # },
    # 'hrbp_note': {
    #     'write': [],
    # },
    # 'continue_recruiting_id': {
    #     'write': [],
    # },
    'date_end_working_approve': {
        'write': ['vhr_cb_termination'],
    },
    'update_date': {
        'write': ['vhr_cb_termination'],
    },
    'date_response_to_af_fa_it': {
        'write': ['vhr_cb_termination'],
    },
    'severance_allowance': {
        'write': ['vhr_cb_termination'],
    },
    'decision_no': {
        'write': ['vhr_cb_termination'],
    },
    'sign_date': {
        'write': ['vhr_cb_termination'],
    },
    'signer_id': {
        'write': ['vhr_cb_termination'],
    },
    'signer_job_title_id': {
        'write': ['vhr_cb_termination'],
    },
    # 'attached_file': {
    # 'write': ['vhr_cb_termination'],
    # },
    'note': {
        'write': ['vhr_cb_termination'],
    },


}
