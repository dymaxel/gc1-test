odoo.define("sprogroup_purchase_request.HideCreateBtnList", function(require) {
    "use strict";

    var ListController = require('web.ListController');
    var session = require('web.session');

    ListController.include({

        willStart: function () {
            var self = this;
            var def_create = session.user_has_group('sprogroup_purchase_request.group_hide_create_btn').then(function (has_create_group) {
                self.has_create_group = has_create_group;
            });

            return Promise.all([this._super.apply(this, arguments), def_create]);
        },

        updateButtons: function (mode) {
            if (this.has_create_group) {
                if (this.modelName == "purchase.order")
                    {
                        this.$buttons.find('.o_list_button_add').hide();
                    }
            }
            this._updateSelectionBox();
        },
    })
});