{
    'name': 'Craydoo Account Product',
    'version': '20.0.0.0.0',
    'summary': 'Resolves invoice line accounts from product/category configuration',
    'category': 'Accounting',
    'author': 'Craydoo',
    'license': 'LGPL-3',
    'depends': ['craydoo_account', 'craydoo_product'],
    'auto_install': True,
    'data': [
        'views/product_views.xml',
        'views/account_invoice_views.xml',
    ],
}
