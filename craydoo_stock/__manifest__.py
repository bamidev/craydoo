{
    'name': 'Craydoo Stock',
    'version': '20.0.0.0.0',
    'summary': 'Inventory and warehouse operations for the Craydoo suite',
    'category': 'Inventory',
    'author': 'Craydoo',
    'license': 'LGPL-3',
    'depends': ['base', 'craydoo_product'],
    'data': [
        'security/ir.access.csv',
        'data/stock_transfer_sequence.xml',
        'data/stock_picking_order_sequence.xml',
        'views/stock_location_views.xml',
        'views/stock_quantity_views.xml',
        'views/stock_transfer_views.xml',
        'views/stock_picking_order_views.xml',
    ],
}
