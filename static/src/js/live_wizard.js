openerp.account_live_report = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.account_live_report = instance.web.account_live_report || {};

    instance.web.views.add('tree_live', 'instance.web.account_live_report.LiveListView');
    instance.web.account_live_report.LiveListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
        },
        load_list: function() {
            var self = this;
            var tmp = this._super.apply(this, arguments);
            this.$el.prepend(QWeb.render("LaunchWizard", {widget: this}));
            console.log('My module has been initialized');
            return tmp;
        },
    });

};
