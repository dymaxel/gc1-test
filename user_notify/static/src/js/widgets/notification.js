odoo.define('web_notify.Notification', function (require) {
    "use strict";

    var Notification = require('web.Notification');

    Notification.include({
        events: {
            'click a': '_clickRedirect',
        },
        icon_mapping: {
            'info': 'fa-info',
            'default': 'fa-lightbulb-o',
        },
        _autoCloseDelay: 50000,
        init: function () {
            this._super.apply(this, arguments);
            this.className = this.className.replace(' o_error', '');
            this.icon = (this.type in this.icon_mapping) ?
                this.icon_mapping[this.type] :
                this.icon_mapping['default'];
            this.className += ' o_' + this.type;
        },
        _clickRedirect: function (ev) {
            var id = $(ev.currentTarget).data('oe-id');
            if (id) {
                ev.preventDefault();
                var model = $(ev.currentTarget).data('oe-model');
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: model,
                    res_id: id,
                    views: [[false, 'form']],
                    target: 'current'
                });
            }
         },
    });

});
