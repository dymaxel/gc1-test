# -*- coding: utf-8 -*-
from odoo import _, api, exceptions, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.depends("create_date")
    def _compute_channel_names(self):
        for record in self:
            res_id = record.id
            record.notify_info_channel_name = "notify_info_%s" % res_id
            record.notify_default_channel_name = "notify_default_%s" % res_id

    notify_info_channel_name = fields.Char(compute="_compute_channel_names")
    notify_default_channel_name = fields.Char(compute="_compute_channel_names")

    def notify_info(self, message="Default message", title=None, sticky=True):
        title = title or _("Required fields not set")
        self._notify_channel('info', message, title, sticky)

    def _notify_channel(self, type_message='default', message='Default message', title=None, sticky=True):
        channel_name_field = "notify_{}_channel_name".format(type_message)
        bus_message = {
            "type": type_message,
            "message": message,
            "title": title,
            "sticky": sticky,
        }
        notifications = [
            (record[channel_name_field], bus_message) for record in self
        ]
        self.env["bus.bus"].sendmany(notifications)
