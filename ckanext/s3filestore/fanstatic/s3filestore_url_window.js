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
                this._onReceiveApiSnippetError("ERROR: No url found.");
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
            let content = `ERROR (${type}): ${error.status} ${error.statusText}`;
            this._toggleFeedback(content);
        },
        _toggleFeedback: function (message) {
            let element = $(this.el[0]).closest('div');
            element.popover('destroy');
            element.popover({
                title: "Clipboard Copy",
                html: true,
                content: message,
                placement: 'left'
            });
            element.popover('show');
            $('.popover').one('click', function(){
                element.popover('destroy');
            });
        }
    };
});
