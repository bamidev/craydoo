{
    'name': 'Craydoo Account',
    'version': '20.0.1.0.0',
    'summary': 'Tigerbeetle-backed accounting for the Craydoo suite',
    'category': 'Accounting',
    'author': 'Craydoo',
    'license': 'LGPL-3',
    'depends': ['base', 'craydoo_contact'],
    'data': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'data/account_invoice_sequence.xml',
        'views/account_invoice_views.xml',
        'views/account_tax_views.xml',
        'views/account_tax_tag_views.xml',
    ],
}
