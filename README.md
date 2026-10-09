# Craydoo

Craydoo aims to be a set of alternative Odoo core modules, whose data model is centered around data consistency, and then performance, useful for large companies.
Accounting history in craydoo is designed to be immutable, unlike Odoo's core modules, which in the default configuration can leave even regular users with the power to delete `account.move`s if you really know how to.

For any type of model that can hold a very large history, like accounting transfers or stock, Postgres' date-partitioning is used to make searching through recent records faster and the archiving of older (fiscal) years possible.

All in all, the aim of this project is to build a set of core modules which can maintain the administration of large companies for many years to come. But it is a work in progress for now...
