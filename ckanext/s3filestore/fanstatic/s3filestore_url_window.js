'use strict';

ckan.module('s3filestore_url_window', function ($) {
    return {
        _snippetReceived: false,
        initialize: function () {
            $.proxyAll(this, /_on/);
            this.el.on('click', this._onClick);
        },
        _onClick: function (event) {
            this.sandbox.client.call('GET', 'download_window',
                '?package_id=' + this.options.id + '&resource_id=' + this.options.rid,
                this._onReceiveApiSnippet,
                this._onReceiveApiSnippetError
            );
        },
        _onReceiveApiSnippet: function (response) {
            if (response.result) {
                for (const [key, value] of Object.entries(response.result)) {
                    this.options[key] = value;
                }
            }
            if (!this.options["url"]) {
                this._onReceiveApiSnippetError({statusText: 'No url found', status: '404'});
            }
            if (this.options["expiry_in_seconds"]) {
                this.options["expiry_in_minutes"] = this.options["expiry_in_seconds"]/60
            }
            navigator.clipboard.writeText(this.options["url"]);
            this.sandbox.client.getTemplate('s3filestore_url_window.html',
                this.options,
                this._onReceiveHtmlSnippet,
                this._onReceiveHtmlSnippetError
            );
        },
        _onReceiveHtmlSnippet: function (html) {
            this._toggleFeedback(html);
        },
        _onReceiveApiSnippetError: function (error) {
            this._onReceiveSnippetError(error, 'Api');
        },
        _onReceiveHtmlSnippetError: function (error) {
            this._onReceiveSnippetError(error, 'Html');
        },
        _onReceiveSnippetError: function (error, type) {
            let errorMessage = error.statusText;
            if (error && error.responseJSON) {
                errorMessage = error.responseJSON.error.message
            }
            let content = `ERROR (${type}: ${error.status}) ${errorMessage}`;
            this._toggleFeedback(content);
        },
        _toggleFeedback: function (message) {
            let element = $(this.el[0]).closest('div');
            $(element).on('shown.bs.popover', function () {
                $('.popover').one('click', function () {
                    $(this).closest('div').popover('destroy');
                });
                setTimeout(function () {
                    element.popover('destroy');
                }, 6000);
            });
            element.popover('destroy');
            element.popover({
                title: "Copied to clipboard!",
                html: true,
                content: message,
                placement: 'left'
            });
            element.popover('show');

        }
    };
});
