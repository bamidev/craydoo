{
    'name': 'Craydoo Contact',
    'version': '20.0.1.0.0',
    'summary': 'Contact information for the Craydoo suite',
    'category': 'Contacts',
    'author': 'Craydoo',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'phone_validation'],
    'data': [
        'security/contact_security.xml',
        'security/ir.access.csv',
        'views/contact_info_views.xml',
        'views/contact_mixin_views.xml',
        'views/contact_person_views.xml',
        'views/contact_company_views.xml',
    ],
}
