# -*- coding: utf-8 -*-
{
	"name" : "User Notification",
	"version" : "13.0.0.1",
	"category" : "Sales",
	'summary': 'User notification on sale order creation',
	"depends" : ['base', 'web', 'mail'],
    'data': ['views/user_notify.xml'],
    # 'demo': ['views/res_users.xml'],
	"Application": True,
	"installable": True,
}
